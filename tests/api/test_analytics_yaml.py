import allure
import pytest
from tests.utils.yaml_loader import load_yaml
from app.extensions import db
from app.models.analytics import ChurnPrediction

DATA = load_yaml("analytics")


@allure.feature("数据分析模块")
class TestClusteringDetail:

    @allure.story("聚类详情")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("{case[name]}")
    @pytest.mark.parametrize("case", DATA["clustering_detail"])
    def test_clustering_detail(self, client, auth_headers, admin_headers, case):
        headers = admin_headers if case["as_admin"] else auth_headers
        with allure.step(f"GET /api/v1/analytics/clustering/detail: {case['name']}"):
            resp = client.get("/api/v1/analytics/clustering/detail", headers=headers)
        with allure.step("验证状态码"):
            assert resp.status_code == case["expected_status"]


@allure.feature("数据分析模块")
class TestDashboard:

    @allure.story("管理员仪表盘")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("{case[name]}")
    @pytest.mark.parametrize("case", DATA["dashboard"])
    def test_dashboard(self, client, auth_headers, admin_headers, case):
        headers = admin_headers if case["as_admin"] else auth_headers
        with allure.step(f"GET /api/v1/analytics/dashboard: {case['name']}"):
            resp = client.get("/api/v1/analytics/dashboard", headers=headers)
        with allure.step("验证状态码"):
            assert resp.status_code == case["expected_status"]


@allure.feature("数据分析模块")
class TestRFMSummary:

    @allure.story("RFM分群摘要")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("{case[name]}")
    @pytest.mark.parametrize("case", DATA["rfm_summary"])
    def test_rfm_summary(self, client, auth_headers, admin_headers, case):
        headers = admin_headers if case["as_admin"] else auth_headers
        with allure.step("GET /api/v1/analytics/rfm/summary"):
            resp = client.get("/api/v1/analytics/rfm/summary", headers=headers)
        with allure.step("验证状态码"):
            assert resp.status_code == case["expected_status"]


@allure.feature("数据分析模块")
class TestSalesTrend:

    @allure.story("销售趋势")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("{case[name]}")
    @pytest.mark.parametrize("case", DATA["sales_trend"])
    def test_sales_trend(self, client, admin_headers, case):
        with allure.step("GET /api/v1/analytics/sales/trend"):
            resp = client.get("/api/v1/analytics/sales/trend", headers=admin_headers)
        with allure.step("验证状态码"):
            assert resp.status_code == case["expected_status"]


@allure.feature("数据分析模块")
class TestSalesPrediction:

    @allure.story("销售预测")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("{case[name]}")
    @pytest.mark.parametrize("case", DATA["sales_prediction"])
    def test_sales_prediction(self, client, admin_headers, case):
        with allure.step("GET /api/v1/analytics/sales/prediction"):
            resp = client.get("/api/v1/analytics/sales/prediction", headers=admin_headers)
        with allure.step("验证状态码"):
            assert resp.status_code == case["expected_status"]


@allure.feature("数据分析模块")
class TestAssociationList:

    @allure.story("关联规则列表")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("{case[name]}")
    @pytest.mark.parametrize("case", DATA["association_list"])
    def test_association_list(self, client, admin_headers, case):
        with allure.step("GET /api/v1/analytics/association/list"):
            resp = client.get("/api/v1/analytics/association/list", headers=admin_headers)
        with allure.step("验证状态码"):
            assert resp.status_code == case["expected_status"]


@allure.feature("数据分析模块")
class TestAssociationForProduct:

    @allure.story("商品关联推荐")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("{case[name]}")
    @pytest.mark.parametrize("case", DATA["association_for_product"])
    def test_association_for_product(self, client, case):
        with allure.step(f"GET /api/v1/analytics/association/product/{case['product_id']}"):
            resp = client.get(f"/api/v1/analytics/association/product/{case['product_id']}")
        with allure.step("验证状态码"):
            assert resp.status_code == case["expected_status"]


@allure.feature("数据分析模块")
class TestChurnList:

    @allure.story("流失预警列表")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("{case[name]}")
    @pytest.mark.parametrize("case", DATA["churn_list"])
    def test_churn_list(self, client, admin_headers, case):
        params = {}
        if case.get("risk_only"):
            params["risk_only"] = "1"
        with allure.step(f"GET /api/v1/analytics/churn/list: {case['name']}"):
            resp = client.get("/api/v1/analytics/churn/list", headers=admin_headers, query_string=params)
        with allure.step("验证状态码"):
            assert resp.status_code == case["expected_status"]


@allure.feature("数据分析模块")
class TestChurnImportance:

    @allure.story("特征重要性")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("{case[name]}")
    @pytest.mark.parametrize("case", DATA["churn_importance"])
    def test_churn_importance(self, client, admin_headers, case):
        with allure.step("GET /api/v1/analytics/churn/importance"):
            resp = client.get("/api/v1/analytics/churn/importance", headers=admin_headers)
        with allure.step("验证状态码"):
            assert resp.status_code == case["expected_status"]


@allure.feature("数据分析模块")
class TestUserRFM:

    @allure.story("用户个人RFM")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("{case[name]}")
    @pytest.mark.parametrize("case", DATA["user_rfm"])
    def test_user_rfm(self, client, auth_headers, case):
        with allure.step("GET /api/v1/analytics/user/rfm"):
            resp = client.get("/api/v1/analytics/user/rfm", headers=auth_headers)
        with allure.step("验证状态码"):
            assert resp.status_code == case["expected_status"]


@allure.feature("数据分析模块")
class TestUserTrend:

    @allure.story("用户消费趋势")
    @allure.severity(allure.severity_level.MINOR)
    @allure.title("{case[name]}")
    @pytest.mark.parametrize("case", DATA["user_trend"])
    def test_user_trend(self, client, auth_headers, case):
        with allure.step("GET /api/v1/analytics/user/trend"):
            resp = client.get("/api/v1/analytics/user/trend", headers=auth_headers)
        with allure.step("验证状态码"):
            assert resp.status_code == case["expected_status"]


@allure.feature("数据分析模块")
class TestUserCategoryPreference:

    @allure.story("用户品类偏好")
    @allure.severity(allure.severity_level.MINOR)
    @allure.title("{case[name]}")
    @pytest.mark.parametrize("case", DATA["user_category_preference"])
    def test_user_category_preference(self, client, auth_headers, case):
        with allure.step("GET /api/v1/analytics/user/category-preference"):
            resp = client.get("/api/v1/analytics/user/category-preference", headers=auth_headers)
        with allure.step("验证状态码"):
            assert resp.status_code == case["expected_status"]


@allure.feature("数据分析模块")
class TestModelMetrics:

    @allure.story("模型指标")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("{case[name]}")
    @pytest.mark.parametrize("case", DATA["model_metrics"])
    def test_model_metrics(self, client, admin_headers, case):
        with allure.step("GET /api/v1/analytics/metrics"):
            resp = client.get("/api/v1/analytics/metrics", headers=admin_headers)
        with allure.step("验证状态码"):
            assert resp.status_code == case["expected_status"]


@allure.feature("数据分析模块")
class TestHotProducts:

    @allure.story("热门商品")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("{case[name]}")
    @pytest.mark.parametrize("case", DATA["hot_products"])
    def test_hot_products(self, client, case):
        params = {"limit": case.get("limit", 6)}
        if case.get("category"):
            params["category"] = case["category"]
        with allure.step(f"GET /api/v1/analytics/products/hot: {case['name']}"):
            resp = client.get("/api/v1/analytics/products/hot", query_string=params)
        with allure.step("验证状态码"):
            assert resp.status_code == case["expected_status"]


@allure.feature("数据分析模块")
class TestRecompute:

    @allure.story("重算")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("{case[name]}")
    @pytest.mark.parametrize("case", DATA["recompute"])
    def test_recompute(self, client, auth_headers, admin_headers, case):
        headers = admin_headers if case["as_admin"] else auth_headers
        with allure.step(f"POST /api/v1/analytics/admin/recompute: {case['name']}"):
            resp = client.post("/api/v1/analytics/admin/recompute", headers=headers)
        with allure.step("验证状态码"):
            assert resp.status_code == case["expected_status"]


@allure.feature("数据分析模块")
class TestLastComputeTime:

    @allure.story("最后计算时间")
    @allure.severity(allure.severity_level.MINOR)
    @allure.title("{case[name]}")
    @pytest.mark.parametrize("case", DATA["last_compute_time"])
    def test_last_compute_time(self, client, admin_headers, case):
        with allure.step("GET /api/v1/analytics/admin/last-compute-time"):
            resp = client.get("/api/v1/analytics/admin/last-compute-time", headers=admin_headers)
        with allure.step("验证状态码"):
            assert resp.status_code == case["expected_status"]


@allure.feature("数据分析模块")
class TestChurnStatusUpdate:

    @allure.story("流失状态更新")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("{case[name]}")
    @pytest.mark.parametrize("case", DATA["churn_status_update"])
    def test_churn_status_update(self, client, admin_headers, app, case):
        with app.app_context():
            cp = ChurnPrediction(
                user_id=2, churn_prob=0.7, is_churn_risk=True,
                top_features='["monetary"]', status="pending",
            )
            db.session.add(cp)
            db.session.commit()
            churn_id = cp.id

        with allure.step(f"PUT /api/v1/analytics/churn/{churn_id}/status: {case['status']}"):
            resp = client.put(
                f"/api/v1/analytics/churn/{churn_id}/status",
                json={"status": case["status"]},
                headers=admin_headers,
            )
        with allure.step("验证状态码"):
            assert resp.status_code == case["expected_status"]


@allure.feature("数据分析模块")
class TestChurnTrend:

    @allure.story("流失趋势")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("{case[name]}")
    @pytest.mark.parametrize("case", DATA["churn_trend"])
    def test_churn_trend(self, client, auth_headers, admin_headers, case):
        headers = admin_headers if case["as_admin"] else auth_headers
        with allure.step(f"GET /api/v1/analytics/churn/trend: {case['name']}"):
            resp = client.get("/api/v1/analytics/churn/trend", headers=headers)
        with allure.step("验证状态码"):
            assert resp.status_code == case["expected_status"]


@allure.feature("数据分析模块")
class TestSalesHeatmap:

    @allure.story("销售热力图")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("{case[name]}")
    @pytest.mark.parametrize("case", DATA["sales_heatmap"])
    def test_sales_heatmap(self, client, auth_headers, admin_headers, case):
        headers = admin_headers if case["as_admin"] else auth_headers
        with allure.step(f"GET /api/v1/analytics/sales/heatmap: {case['name']}"):
            resp = client.get("/api/v1/analytics/sales/heatmap", headers=headers)
        with allure.step("验证状态码"):
            assert resp.status_code == case["expected_status"]


@allure.feature("数据分析模块")
class TestPredictionMetrics:

    @allure.story("预测指标")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("{case[name]}")
    @pytest.mark.parametrize("case", DATA["prediction_metrics"])
    def test_prediction_metrics(self, client, auth_headers, admin_headers, case):
        headers = admin_headers if case["as_admin"] else auth_headers
        with allure.step(f"GET /api/v1/analytics/sales/prediction-metrics: {case['name']}"):
            resp = client.get("/api/v1/analytics/sales/prediction-metrics", headers=headers)
        with allure.step("验证状态码"):
            assert resp.status_code == case["expected_status"]


@allure.feature("数据分析模块")
class TestModelViz:
    """模型可视化数据接口 /analytics/viz/<model>"""

    @allure.story("模型可视化")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("{case[name]}")
    @pytest.mark.parametrize("case", DATA["model_viz"])
    def test_model_viz(self, client, auth_headers, admin_headers, case):
        if case["as_admin"] is True:
            headers = admin_headers
        elif case["as_admin"] is False:
            headers = auth_headers
        else:
            headers = {}
        with allure.step(f"GET /api/v1/analytics/viz/{case['model']}: {case['name']}"):
            resp = client.get(f"/api/v1/analytics/viz/{case['model']}", headers=headers)
        with allure.step("验证状态码"):
            assert resp.status_code == case["expected_status"]
        if case["expected_status"] == 200:
            data = resp.get_json().get("data")
            assert data is not None, "viz response.data should not be None"
            assert "metadata" in data, "viz response should contain metadata"
            with allure.step("验证metadata.version字段存在"):
                assert "version" in data.get("metadata", {}), \
                    f"metadata.version missing for {case['model']}"


@allure.feature("数据分析模块")
class TestModelVersionInDB:
    """验证 DB 中 4 个模型 version 字段"""

    @allure.story("模型版本")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("{case[name]}")
    @pytest.mark.parametrize("case", DATA["model_version"])
    def test_model_version_in_db(self, app, case):
        from app.models.analytics import ModelMetric
        with app.app_context():
            with allure.step(f"查询 {case['model_name']}.version"):
                metric = ModelMetric.query.filter_by(
                    model_name=case["model_name"], metric_name="version"
                ).first()
            with allure.step("验证version字段存在"):
                assert metric is not None, f"{case['model_name']}.version not found in DB"
                assert metric.detail == case["expected_version"], \
                    f"Expected {case['expected_version']}, got {metric.detail}"


@allure.feature("数据分析模块")
class TestPredictionMetricsNewFields:
    """验证预测指标接口返回新字段 cv_smape_std, cv_folds, best_r2, version"""

    @allure.story("预测指标新字段")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("{case[name]}")
    @pytest.mark.parametrize("case", DATA["prediction_metrics_new_fields"])
    def test_prediction_metrics_new_fields(self, client, admin_headers, case):
        with allure.step("GET /api/v1/analytics/sales/prediction-metrics"):
            resp = client.get("/api/v1/analytics/sales/prediction-metrics", headers=admin_headers)
        with allure.step("验证状态码为200"):
            assert resp.status_code == 200
        data = resp.get_json().get("data", {})
        lgbm = data.get("LightGBM_Weekly", {})
        with allure.step(f"验证字段 {case['field']} 存在"):
            assert case["field"] in lgbm, \
                f"Field {case['field']} missing from LightGBM_Weekly metrics. Got keys: {list(lgbm.keys())}"


@allure.feature("数据分析模块")
class TestModelMetricsVersion:
    """验证 /analytics/model-metrics 接口返回 4 个模型的 version 字段"""

    @allure.story("模型指标version")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("{case[name]}")
    @pytest.mark.parametrize("case", DATA["model_metrics_version"])
    def test_model_metrics_version(self, client, admin_headers, case):
        with allure.step(f"GET /api/v1/analytics/metrics?model={case['model_name']}"):
            resp = client.get(f"/api/v1/analytics/metrics?model={case['model_name']}", headers=admin_headers)
        with allure.step("验证状态码为200"):
            assert resp.status_code == 200
        data = resp.get_json().get("data", {})
        with allure.step(f"验证 {case['model_name']} 数据非空"):
            assert case["model_name"] in data, \
                f"Model {case['model_name']} missing. Got keys: {list(data.keys())}"
            metrics_list = data[case["model_name"]]
            assert isinstance(metrics_list, list) and len(metrics_list) > 0, \
                f"Expected non-empty list of metrics for {case['model_name']}"
        with allure.step(f"验证 {case['model_name']} 含 {case['field']} 指标项"):
            metric_names = [m.get("metric_name") for m in metrics_list]
            assert case["field"] in metric_names, \
                f"Field {case['field']} missing. Got metric_names: {metric_names}"


@allure.feature("数据分析模块")
class TestReview:

    @allure.story("商品评价")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("创建评价")
    def test_create_review(self, client, auth_headers):
        with allure.step("POST /api/v1/reviews"):
            resp = client.post("/api/v1/reviews", headers=auth_headers, json={
                "product_id": 1,
                "rating": 5,
                "content": "非常好的商品！",
            })
        with allure.step("验证状态码为201"):
            assert resp.status_code == 201
            data = resp.get_json()
            assert data["data"]["rating"] == 5

    @allure.story("商品评价")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("获取商品评价")
    def test_get_product_reviews(self, client):
        with allure.step("GET /api/v1/reviews/product/1"):
            resp = client.get("/api/v1/reviews/product/1")
        with allure.step("验证状态码为200"):
            assert resp.status_code == 200

    @allure.story("商品评价")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("评价-无效评分")
    def test_create_review_invalid_rating(self, client, auth_headers):
        with allure.step("POST /api/v1/reviews (rating=6)"):
            resp = client.post("/api/v1/reviews", headers=auth_headers, json={
                "product_id": 1,
                "rating": 6,
                "content": "无效评分",
            })
        with allure.step("验证状态码为400"):
            assert resp.status_code == 400
