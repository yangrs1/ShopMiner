import json
from deepdiff import DeepDiff


def assert_response_schema(resp_json, expected_schema, ignore_extra=True):
    expected_keys = set(expected_schema.keys())
    actual_keys = set(resp_json.keys()) if isinstance(resp_json, dict) else set()
    if not ignore_extra:
        missing = expected_keys - actual_keys
        extra = actual_keys - expected_keys
        assert not missing, f"缺少字段: {missing}"
        assert not extra, f"多余字段: {extra}"
    else:
        missing = expected_keys - actual_keys
        assert not missing, f"缺少字段: {missing}"


def assert_json_contains(actual, expected, ignore_paths=None):
    diff = DeepDiff(expected, actual, ignore_order=True, exclude_paths=ignore_paths or [])
    assert not diff, f"JSON不匹配:\n{json.dumps(diff, indent=2, ensure_ascii=False, default=str)}"


def assert_field_type(data, field, expected_type):
    value = data.get(field) if isinstance(data, dict) else None
    assert value is not None, f"字段 {field} 不存在"
    assert isinstance(value, expected_type), (
        f"字段 {field} 类型不符: 期望 {expected_type.__name__}, 实际 {type(value).__name__}"
    )


def assert_field_in(data, field, valid_values):
    value = data.get(field) if isinstance(data, dict) else None
    assert value in valid_values, (
        f"字段 {field} 值 {value} 不在有效范围 {valid_values} 内"
    )


def assert_pagination(data, min_total=0):
    assert "total" in data, "分页数据缺少 total"
    assert "pages" in data, "分页数据缺少 pages"
    assert "page" in data, "分页数据缺少 page"
    assert data["total"] >= min_total, f"总数 {data['total']} < 最低期望 {min_total}"
