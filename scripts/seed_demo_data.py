"""Seed demo data for ShopMiner — run once after server starts."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import create_app
from app.extensions import db
from app.models.product import Product
from app.models.user import User
from app.models.analytics import Review

app = create_app("development")

with app.app_context():
    # Skip if already seeded
    if Product.query.count() > 10:
        print("Data already seeded, skipping.")
        sys.exit(0)

    # Demo products with real images from static/images/products/
    products = [
        Product(name="经典纯棉T恤 男士夏季短袖", description="100%纯棉面料，透气舒适，经典圆领设计，多色可选。适合日常休闲穿着。",
                image="/static/images/products/15056BL.jpg", price=12900, stock=200, type="tshirt", category_name="男装"),
        Product(name="休闲束脚运动裤 男士直筒长裤", description="弹力针织面料，宽松束脚版型，腰部松紧抽绳设计，运动休闲两不误。",
                image="/static/images/products/20685.jpg", price=19900, stock=150, type="pants", category_name="男装"),
        Product(name="纯棉中筒袜 5双装 透气吸汗", description="精梳棉材质，透气吸汗不闷脚，弹力罗纹口不勒脚踝。男女通用。",
                image="/static/images/products/21121.jpg", price=3999, stock=500, type="socks", category_name="配饰"),
        Product(name="商务休闲Polo衫 男士翻领T恤", description="珠地网眼面料，挺括有型，翻领设计简约干练，适合通勤与休闲场合。",
                image="/static/images/products/20712.jpg", price=25900, stock=120, type="tshirt", category_name="男装"),
        Product(name="日系复古工装裤 多口袋设计", description="厚实斜纹棉布，多口袋工装设计，直筒宽松版型，打造街头潮流感。",
                image="/static/images/products/20914.jpg", price=23900, stock=80, type="pants", category_name="男装"),
        Product(name="轻薄羽绒服 男款秋冬保暖外套", description="90%白鹅绒填充，轻薄保暖不臃肿，防风防泼水面料，可收纳设计。",
                image="/static/images/products/21034.jpg", price=45900, stock=60, type="outerwear", category_name="男装"),
        Product(name="女士雪纺碎花连衣裙 春夏新款", description="轻盈雪纺面料，浪漫碎花印花，收腰A字版型，优雅飘逸。适合约会出游。",
                image="/static/images/products/20718.jpg", price=29900, stock=90, type="dress", category_name="女装"),
        Product(name="法式复古方领上衣 泡泡袖设计", description="方领露锁骨设计，复古泡泡袖，温柔显气质。棉质面料亲肤舒适。",
                image="/static/images/products/20723.jpg", price=16900, stock=110, type="tops", category_name="女装"),
        Product(name="高腰直筒牛仔裤 女士显瘦百搭", description="高腰设计拉长腿部比例，直筒版型修饰腿型，经典牛仔蓝百搭不挑人。",
                image="/static/images/products/20971.jpg", price=27900, stock=75, type="pants", category_name="女装"),
        Product(name="运动休闲连帽卫衣 男女同款", description="加绒保暖内里，宽松落肩版型，经典连帽设计，简约字母印花。情侣款。",
                image="/static/images/products/20724.jpg", price=22900, stock=130, type="hoodie", category_name="男女同款"),
        Product(name="真皮商务腰带 自动扣头层牛皮", description="头层牛皮制作，自动扣设计方便调节，简约商务风格，适合正装与休闲搭配。",
                image="/static/images/products/21479.jpg", price=18900, stock=200, type="accessory", category_name="配饰"),
        Product(name="韩版斜挎包 男士潮流胸包", description="尼龙防水面料，多隔层收纳，可斜挎可胸背，轻便实用。日常出街必备。",
                image="/static/images/products/21523.jpg", price=15900, stock=85, type="bag", category_name="配饰"),
    ]

    # Ensure admin and customer users exist
    admin = User.query.filter_by(email="admin@shopminer.com").first()
    if not admin:
        admin = User(first_name="Admin", last_name="User", address="Admin Address",
                     email="admin@shopminer.com", role="admin", balance=1000000)
        admin.set_password("Admin@123")
        db.session.add(admin)

    customer = User.query.filter_by(email="customer@shopminer.com").first()
    if not customer:
        customer = User(first_name="Test", last_name="Customer", address="123 Test St",
                        email="customer@shopminer.com", balance=500000)
        customer.set_password("Customer@123")
        db.session.add(customer)

    db.session.add_all(products)
    db.session.flush()

    # Add some reviews
    reviews = [
        Review(product_id=products[0].id, user_id=customer.id, rating=5, content="质量很好，纯棉穿着很舒服，洗了也不变形。"),
        Review(product_id=products[1].id, user_id=customer.id, rating=4, content="版型不错，弹性好，运动穿很合适。"),
        Review(product_id=products[2].id, user_id=customer.id, rating=5, content="袜子很厚实，吸汗效果不错，5双够穿一季了。"),
        Review(product_id=products[3].id, user_id=customer.id, rating=4, content="面料挺括，适合上班穿，领子不会塌。"),
        Review(product_id=products[6].id, user_id=customer.id, rating=5, content="碎花很好看，面料轻盈，夏天穿很凉快。"),
        Review(product_id=products[7].id, user_id=customer.id, rating=4, content="方领设计很好看，泡泡袖不夸张，日常穿很合适。"),
        Review(product_id=products[9].id, user_id=customer.id, rating=5, content="卫衣很厚实，冬天穿刚好，情侣款和对象一人一件。"),
    ]
    for r in reviews:
        existing = Review.query.filter_by(product_id=r.product_id, user_id=r.user_id).first()
        if not existing:
            db.session.add(r)

    db.session.commit()
    print(f"Seeded {len(products)} products, {len(reviews)} reviews.")
