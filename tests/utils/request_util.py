import requests


class RequestUtil:
    def __init__(self, base_url="http://127.0.0.1:5000"):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.token = None

    def set_token(self, token):
        self.token = token
        self.session.headers.update({"Authorization": f"Bearer {token}"})

    def clear_token(self):
        self.token = None
        self.session.headers.pop("Authorization", None)

    def request(self, method, path, **kwargs):
        url = f"{self.base_url}{path}"
        resp = self.session.request(method, url, **kwargs)
        return ApiResponse(resp)

    def get(self, path, **kwargs):
        return self.request("GET", path, **kwargs)

    def post(self, path, **kwargs):
        return self.request("POST", path, **kwargs)

    def put(self, path, **kwargs):
        return self.request("PUT", path, **kwargs)

    def delete(self, path, **kwargs):
        return self.request("DELETE", path, **kwargs)

    def login(self, email, password):
        resp = self.post("/api/v1/auth/login", json={"email": email, "password": password})
        if resp.status_code == 200:
            self.set_token(resp.json["data"]["access_token"])
        return resp

    def close(self):
        self.session.close()


class ApiResponse:
    def __init__(self, resp):
        self.status_code = resp.status_code
        self.headers = dict(resp.headers)
        self.raw = resp
        try:
            self.json = resp.json()
        except Exception:
            self.json = {}

    @property
    def code(self):
        return self.json.get("code", 0)

    @property
    def message(self):
        return self.json.get("message", "")

    @property
    def data(self):
        return self.json.get("data", {})

    def assert_status(self, expected):
        assert self.status_code == expected, (
            f"HTTP状态码不符: 期望 {expected}, 实际 {self.status_code}\n"
            f"响应: {self.json}"
        )
        return self

    def assert_code(self, expected):
        assert self.code == expected, (
            f"业务码不符: 期望 {expected}, 实际 {self.code}\n"
            f"消息: {self.message}"
        )
        return self

    def assert_field(self, field, expected=None):
        value = self.data.get(field) if isinstance(self.data, dict) else None
        if expected is not None:
            assert value == expected, (
                f"字段 {field} 不符: 期望 {expected}, 实际 {value}"
            )
        else:
            assert value is not None, f"字段 {field} 不存在"
        return self
