# [GAP: missing-test] product_translator.py had 0% coverage
"""Tests for app.services.product_translator.

Covers translate_product_name and _apply_dict — pure function
translation engine for English-to-Chinese product name mapping.
"""

import pytest

from app.services.product_translator import (
    _apply_dict,
    translate_product_name,
)

pytestmark = pytest.mark.unit


class TestTranslateProductName:
    """Tests for translate_product_name()."""

    @pytest.mark.parametrize(
        "name, expected",
        [
            # ── Basic name translations ──────────────────────
            pytest.param(
                "RED GLASS CUP",
                "红色玻璃杯子",
                id="basic-color-material-product",
            ),
            pytest.param(
                "BLUE METAL BOX",
                "蓝色金属盒子",
                id="basic-color-material-product-2",
            ),
            pytest.param(
                "GREEN WOODEN BOWL",
                "绿色木质碗",
                id="basic-color-material-product-3",
            ),
            pytest.param(
                "PURPLE CERAMIC MUG",
                "紫色陶瓷马克杯",
                id="basic-color-material-mug",
            ),
            # ── Empty / None / short strings ─────────────────
            pytest.param(
                "",
                "",
                id="empty-string",
            ),
            pytest.param(
                None,
                None,
                id="none-input",
            ),
            pytest.param(
                "  ",
                "  ",
                id="whitespace-only",
            ),
            pytest.param(
                "A",
                "A",
                id="single-char",
            ),
            # ── Names with color words ───────────────────────
            pytest.param(
                "SILVER SPOON",
                "银色勺子",
                id="color-metal-spoon",
            ),
            pytest.param(
                "GOLD RING",
                "金色戒指",
                id="color-gold-ring",
            ),
            pytest.param(
                "PINK CUSHION",
                "粉色靠垫",
                id="color-pink-cushion",
            ),
            # ── Names with material words ────────────────────
            pytest.param(
                "WOODEN BOWL",
                "木质碗",
                id="material-wooden-bowl",
            ),
            pytest.param(
                "LEATHER BAG",
                "皮革包",
                id="material-leather-bag",
            ),
            pytest.param(
                "CERAMIC PLATE",
                "陶瓷盘子",
                id="material-ceramic-plate",
            ),
            # ── Case sensitivity (all handled insensitively) ─
            pytest.param(
                "red glass cup",
                "红色玻璃杯子",
                id="case-lowercase",
            ),
            pytest.param(
                "Red Glass Cup",
                "红色玻璃杯子",
                id="case-titlecase",
            ),
            pytest.param(
                "RED glass CUP",
                "红色玻璃杯子",
                id="case-mixed",
            ),
        ],
    )
    def test_translate_product_name(self, name, expected):
        if expected is None:
            assert translate_product_name(name) is None
        else:
            assert translate_product_name(name) == expected


class TestApplyDict:
    """Tests for _apply_dict()."""

    @pytest.mark.parametrize(
        "text, dictionary, case_sensitive, expected",
        [
            # ── Exact match ──────────────────────────────────
            pytest.param(
                "CUP",
                {"CUP": "杯子"},
                False,
                "杯子",
                id="exact-match-single",
            ),
            pytest.param(
                "CUP CUP",
                {"CUP": "杯子"},
                False,
                "杯子 杯子",
                id="exact-match-multiple",
            ),
            # ── Case sensitive vs insensitive ────────────────
            pytest.param(
                "cup",
                {"CUP": "杯子"},
                True,
                "cup",
                id="case-sensitive-no-match",
            ),
            pytest.param(
                "CUP",
                {"CUP": "杯子"},
                True,
                "杯子",
                id="case-sensitive-exact-match",
            ),
            pytest.param(
                "cup",
                {"CUP": "杯子"},
                False,
                "杯子",
                id="case-insensitive-match",
            ),
            # ── Partial match ────────────────────────────────
            pytest.param(
                "COFFEE CUP DISH",
                {"CUP": "杯子"},
                False,
                "COFFEE 杯子 DISH",
                id="partial-match-middle",
            ),
            # ── Longest key matched first ────────────────────
            pytest.param(
                "COFFEE CUP",
                {"CUP": "杯子", "COFFEE CUP": "咖啡杯"},
                False,
                "咖啡杯",
                id="longest-key-first",
            ),
            # ── No match returns original ────────────────────
            pytest.param(
                "XYZ",
                {"ABC": "123"},
                False,
                "XYZ",
                id="no-match",
            ),
            pytest.param(
                "hello",
                {},
                False,
                "hello",
                id="empty-dict",
            ),
            # ── Empty text ───────────────────────────────────
            pytest.param(
                "",
                {"CUP": "杯子"},
                False,
                "",
                id="empty-text",
            ),
        ],
    )
    def test_apply_dict(self, text, dictionary, case_sensitive, expected):
        assert _apply_dict(text, dictionary, case_sensitive) == expected
