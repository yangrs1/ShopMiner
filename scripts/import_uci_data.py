"""
ShopMiner — UCI Online Retail 数据导入脚本
将 UCI 数据集导入现有数据库（Product / Order / OrderItem / User）

映射规则：
  - StockCode + Description → Product（去重，生成唯一ID）
  - CustomerID → User（模拟用户，密码随机生成）
  - InvoiceNo → Order（同一InvoiceNo的多个商品合并为一个Order）
  - (InvoiceNo, StockCode) → OrderItem
  - InvoiceDate → Order.created_at
  - Quantity * UnitPrice → OrderItem.unit_price * quantity（注意：UCI的UnitPrice是单价）
  - Country → User.address（简化存储）
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime
from collections import defaultdict
import hashlib

from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.product import Product
from app.models.order import Order, OrderItem
from app.services.product_translator import translate_product_name

np.random.seed(42)

# UCI 数据路径
UCI_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "raw", "online_retail.csv")

# 商品类别映射（基于Description关键词）
CATEGORY_CN = {
    'BAG': '箱包',
    'CANDLE & HOLDER': '蜡烛与烛台',
    'BAKING': '烘焙',
    'CHRISTMAS': '圣诞装饰',
    'HEART/LOVE': '爱心礼品',
    'CLOCK & ALARM': '钟表闹钟',
    'BUNTING & FLAGS': '彩旗与旗帜',
    'STATIONERY': '文具',
    'METAL SIGN': '金属标牌',
    'FRAME': '相框',
    'STORAGE': '收纳',
    'CUSHION & TEXTILE': '靠垫与纺织品',
    'POUCH & PURSE': '小包与钱包',
    'LANTERN & LIGHT': '灯笼与灯具',
    'VINTAGE': '复古',
    'LUNCH BOX': '饭盒',
    'TEACUP': '茶杯',
    'TOY & GAME': '玩具与游戏',
    'ORNAMENT': '装饰品',
    'KITCHEN': '厨房用品',
}
CATEGORY_DEFAULT_CN = '家居装饰与其他'


def categorize_product(desc):
    desc_lower = desc.lower()
    keywords = {
        'BAG': ['bag', 'tote', 'satchel', 'shopper'],
        'CANDLE & HOLDER': ['candle', 'tealight', 'holder'],
        'BAKING': ['muffin', 'cake', 'baking', 'cupcake'],
        'CHRISTMAS': ['christmas', 'xmas', 'santa', 'reindeer'],
        'HEART/LOVE': ['heart', 'love'],
        'CLOCK & ALARM': ['clock', 'alarm'],
        'BUNTING & FLAGS': ['bunting', 'banner', 'flag'],
        'STATIONERY': ['notebook', 'journal', 'diary', 'pen', 'pencil'],
        'METAL SIGN': ['metal', 'sign', 'plaque', 'tin'],
        'FRAME': ['frame', 'photo'],
        'STORAGE': ['jar', 'bottle', 'storage', 'box', 'basket'],
        'CUSHION & TEXTILE': ['cushion', 'pillow', 'towel'],
        'POUCH & PURSE': ['pouch', 'purse', 'wallet'],
        'LANTERN & LIGHT': ['lantern', 'lamp', 'light'],
        'VINTAGE': ['vintage', 'retro', 'antique'],
        'LUNCH BOX': ['lunch box', 'lunch bag'],
        'TEACUP': ['teacup', 'tea cup', 'saucer'],
        'TOY & GAME': ['doll', 'teddy', 'toy', 'game', 'puzzle'],
        'ORNAMENT': ['ornament', 'decoration', 'hanging'],
        'KITCHEN': ['kitchen', 'cooking', 'utensil'],
    }
    for cat, kws in keywords.items():
        if any(kw in desc_lower for kw in kws):
            return cat
    return 'HOME DECOR & OTHER'


def import_uci_data(force=False):
    app = create_app("development")
    with app.app_context():
        print("=" * 60)
        print("  ShopMiner — Import UCI Online Retail Data")
        print("=" * 60)

        if force:
            print("\n[0/4] Clearing existing data...")
            OrderItem.query.delete()
            Order.query.delete()
            Product.query.delete()
            User.query.filter(User.role != "admin").delete()
            db.session.commit()
            print("  Cleared existing non-admin data.")

        # 检查是否已有UCI数据
        existing_orders = Order.query.count()
        if existing_orders > 0 and not force:
            print(f"  Data already imported ({existing_orders} orders), skip")
            return

        # 读取UCI数据
        print("\n[1/4] Loading UCI data...")
        if not os.path.exists(UCI_PATH):
            print(f"  ERROR: UCI data not found at {UCI_PATH}")
            print("  Please place online_retail.csv in ShopMiner/data/raw/")
            return

        df = pd.read_csv(UCI_PATH, encoding="latin-1")
        print(f"  Raw records: {len(df):,}")

        # 清洗
        df = df.dropna(subset=["CustomerID", "InvoiceNo", "StockCode", "Description"])
        df = df[~df["InvoiceNo"].astype(str).str.startswith("C")]  # 移除取消订单
        df["CustomerID"] = df["CustomerID"].astype(int)
        df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
        df["UnitPrice"] = df["UnitPrice"].astype(float)
        df["Quantity"] = df["Quantity"].astype(int)
        df = df[df["Quantity"] > 0]
        df = df[df["UnitPrice"] > 0]
        print(f"  After cleaning: {len(df):,}")

        # 生成Product表
        print("\n[2/4] Creating Products...")
        product_map = {}  # StockCode -> Product.id
        stockcode_to_product = {}
        unique_products = df[["StockCode", "Description"]].drop_duplicates()

        for _, row in unique_products.iterrows():
            stockcode = row["StockCode"].strip()
            desc = row["Description"].strip()
            category = categorize_product(desc)
            short_name = desc[:50] if len(desc) <= 50 else desc[:47] + "..."

            # 翻译为中文
            cn_name = translate_product_name(desc)

            # 检查是否已存在（用翻译后的中文名或原始描述查重）
            existing = Product.query.filter(
                (Product.name == cn_name) | (Product.description == desc)
            ).first()
            if existing:
                product_map[stockcode] = existing.id
                stockcode_to_product[stockcode] = existing
                continue

            # 生成价格：取该StockCode的中位数单价（×100=pence，保留2位小数精度）
            median_price = df[df["StockCode"] == stockcode]["UnitPrice"].median()
            price_cents = int(round(median_price * 100))

            product = Product(
                name=cn_name,
                description=desc,
                image=f"/images/products/{stockcode}.jpg",  # 占位图片
                price=price_cents,
                type=CATEGORY_CN.get(category, CATEGORY_DEFAULT_CN),
                category_name=CATEGORY_CN.get(category, CATEGORY_DEFAULT_CN),
                is_active=True,
            )
            db.session.add(product)
            db.session.flush()  # 获取ID
            product_map[stockcode] = product.id
            stockcode_to_product[stockcode] = product

        db.session.commit()
        print(f"  Created: {len(product_map)} products")

        # 生成User表（CustomerID -> User）
        print("\n[3/4] Creating Users...")
        user_map = {}  # CustomerID -> User.id
        unique_customers = df[["CustomerID", "Country"]].drop_duplicates()

        for _, row in unique_customers.iterrows():
            customer_id = int(row["CustomerID"])
            country = row["Country"] if pd.notna(row["Country"]) else "Unknown"

            # 生成模拟用户信息
            email = f"customer_{customer_id}@shopminer.uci"
            # 检查是否已存在
            existing = User.query.filter_by(email=email).first()
            if existing:
                user_map[customer_id] = existing.id
                continue

            # 生成随机姓名
            first_names = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Henry", "Ivy", "Jack"]
            last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]
            hash_val = int(hashlib.md5(str(customer_id).encode()).hexdigest(), 16)
            first_name = first_names[hash_val % len(first_names)]
            last_name = last_names[(hash_val // 10) % len(last_names)]

            user = User(
                first_name=first_name,
                last_name=last_name,
                email=email,
                password="$2b$12$" + "x" * 53,  # 占位密码，无法登录
                address=country,
                role="user",
                balance=0,
            )
            db.session.add(user)
            db.session.flush()
            user_map[customer_id] = user.id

        db.session.commit()
        print(f"  Created: {len(user_map)} users")

        # 生成Order和OrderItem
        print("\n[4/4] Creating Orders and OrderItems...")
        # 按InvoiceNo分组
        invoice_groups = df.groupby("InvoiceNo")
        total_invoices = len(invoice_groups)
        print(f"  Total invoices: {total_invoices:,}")

        batch_size = 500
        order_count = 0
        item_count = 0

        for invoice_no, group in invoice_groups:
            # 取该订单的第一个记录获取CustomerID和Date
            first_row = group.iloc[0]
            customer_id = int(first_row["CustomerID"])
            invoice_date = first_row["InvoiceDate"]

            user_id = user_map.get(customer_id)
            if not user_id:
                continue

            # 计算订单总金额（×100=pence，避免浮点精度问题）
            total_amount = int(round((group["Quantity"] * group["UnitPrice"]).sum() * 100))

            # 创建Order
            order = Order(
                user_id=user_id,
                total_amount=total_amount,
                status=Order.STATUS_DELIVERED,  # UCI数据假设已完成
                shipping_address="",
                shipping_phone="",
                tracking_number="",
                created_at=invoice_date,
            )
            db.session.add(order)
            db.session.flush()
            order_count += 1

            # 创建OrderItem
            for _, item_row in group.iterrows():
                stockcode = item_row["StockCode"].strip()
                product_id = product_map.get(stockcode)
                if not product_id:
                    continue

                quantity = int(item_row["Quantity"])
                unit_price = int(round(item_row["UnitPrice"] * 100))

                order_item = OrderItem(
                    order_id=order.id,
                    product_id=product_id,
                    quantity=quantity,
                    unit_price=unit_price,
                )
                db.session.add(order_item)
                item_count += 1

            if order_count % batch_size == 0:
                db.session.commit()
                print(f"    Progress: {order_count}/{total_invoices} orders, {item_count} items")

        db.session.commit()
        print(f"  Created: {order_count} orders, {item_count} items")

        print("\n" + "=" * 60)
        print("  UCI DATA IMPORT COMPLETE!")
        print("=" * 60)
        print(f"  Products: {Product.query.count()}")
        print(f"  Users: {User.query.count()}")
        print(f"  Orders: {Order.query.count()}")
        print(f"  OrderItems: {OrderItem.query.count()}")


if __name__ == "__main__":
    force = "--force" in sys.argv
    import_uci_data(force=force)
