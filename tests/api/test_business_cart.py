import allure

import pytest

import time

from tests.utils.faker_data import resolve_faker

from app.extensions import db


@allure.feature("业务逻辑验证")

class TestInactiveProductAddToCart:



    @allure.story("下架商品加购")

    @allure.severity(allure.severity_level.NORMAL)

    @allure.title("BIZ-006 下架商品无法加入购物车→返回404")

    def test_inactive_product_cannot_add_to_cart(self, client, admin_headers, auth_headers, app):

        with allure.step("1. 管理员下架商品"):

            resp = client.delete("/api/v1/products/3", headers=admin_headers)

            assert resp.status_code == 200



        with allure.step("2. DB验证: 商品is_active=False"):

            with app.app_context():

                from app.models.product import Product

                p = db.session.get(Product, 3)

                assert p.is_active is False



        with allure.step("3. 尝试将下架商品加入购物车→预期404"):

            cart_resp = client.post("/api/v1/cart", headers=auth_headers, json={

                "product_id": 3, "quantity": 1,

            })

            assert cart_resp.status_code == 404



        with allure.step("4. 验证下架商品详情也返回404"):

            detail_resp = client.get("/api/v1/products/3")

            assert detail_resp.status_code == 404




@allure.feature("业务逻辑验证")

class TestProductStockValidation:



    @allure.story("库存校验")

    @allure.severity(allure.severity_level.NORMAL)

    @allure.title("BIZ-011 超库存数量加购→返回400")

    def test_add_to_cart_exceeds_stock(self, client, auth_headers, app):

        with allure.step("1. 查看商品库存"):

            with app.app_context():

                from app.models.product import Product

                product = db.session.get(Product, 1)

                stock = product.stock



        with allure.step(f"2. 尝试加购超过库存的数量({stock + 100})"):

            resp = client.post("/api/v1/cart", headers=auth_headers, json={

                "product_id": 1,

                "quantity": stock + 100,

            })

            assert resp.status_code == 400

            assert "stock" in resp.get_json()["message"].lower()




@allure.feature("业务逻辑验证")

class TestCartMergeQuantity:



    @allure.story("购物车合并数量")

    @allure.severity(allure.severity_level.NORMAL)

    @allure.title("BIZ-018 加购同一商品数量合并逻辑")

    def test_cart_merge_quantity(self, client, auth_headers, app):

        with allure.step("1. 第一次加购(2)"):

            resp1 = client.post("/api/v1/cart", headers=auth_headers, json={

                "product_id": 2, "quantity": 2,

            })

            assert resp1.status_code == 200



        with allure.step("2. DB验证: 购物车1条记录quantity=2"):

            with app.app_context():

                from app.models.order import CartItem

                item = CartItem.query.filter_by(user_id=2, product_id=2).first()

                assert item is not None

                assert item.quantity == 2



        with allure.step("3. 第二次加购(3,同一商品)"):

            resp2 = client.post("/api/v1/cart", headers=auth_headers, json={

                "product_id": 2, "quantity": 3,

            })

            assert resp2.status_code == 200



        with allure.step("4. DB验证: 仍然1条记录quantity=5(合并)"):

            with app.app_context():

                from app.models.order import CartItem

                items = CartItem.query.filter_by(user_id=2, product_id=2).all()

                assert len(items) == 1

                assert items[0].quantity == 5
