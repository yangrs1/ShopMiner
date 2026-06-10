"""Decision table tests for _compute_segment RFM scoring function.

The _compute_segment(r_score, f_score, m_score) function categorizes customers
into 5 segments based on their RFM scores (each 1-5):
  - r>=4 & f>=4 & m>=4  → "高价值客户"
  - r>=3 & f>=3 & m>=3  → "潜力客户"
  - r<=2 & f<=2 & m<=2  → "低价值客户"
  - r<=2 & f>=3         → "流失预警"
  - everything else      → "一般客户"
"""

import pytest
from app.services.analytics_service import _compute_segment

pytestmark = pytest.mark.unit

VALID_SEGMENTS = ("高价值客户", "潜力客户", "低价值客户", "流失预警", "一般客户")


class TestComputeSegment:
    """Decision table coverage for _compute_segment."""

    # ── 高价值客户: r >= 4, f >= 4, m >= 4 ──────────────────────────
    @pytest.mark.parametrize("r,f,m,expected", [
        pytest.param(5, 5, 5, "高价值客户", id="max_all"),
        pytest.param(4, 4, 4, "高价值客户", id="min_boundary"),
        pytest.param(5, 4, 5, "高价值客户", id="r5_f4_m5"),
        pytest.param(4, 5, 4, "高价值客户", id="r4_f5_m4"),
        pytest.param(5, 5, 4, "高价值客户", id="r5_f5_m4"),
        pytest.param(4, 4, 5, "高价值客户", id="r4_f4_m5"),
    ])
    def test_high_value(self, r, f, m, expected):
        assert _compute_segment(r, f, m) == expected

    # ── 潜力客户: r >= 3, f >= 3, m >= 3  (but NOT all >= 4) ───────
    @pytest.mark.parametrize("r,f,m,expected", [
        pytest.param(3, 3, 3, "潜力客户", id="min_boundary"),
        pytest.param(3, 3, 4, "潜力客户", id="r3_f3_m4"),
        pytest.param(3, 4, 3, "潜力客户", id="r3_f4_m3"),
        pytest.param(4, 3, 3, "潜力客户", id="r4_f3_m3"),
        pytest.param(3, 5, 5, "潜力客户", id="r3_f5_m5"),
        pytest.param(5, 3, 5, "潜力客户", id="r5_f3_m5"),
        pytest.param(5, 5, 3, "潜力客户", id="r5_f5_m3"),
    ])
    def test_potential(self, r, f, m, expected):
        assert _compute_segment(r, f, m) == expected

    # ── 低价值客户: r <= 2, f <= 2, m <= 2 ──────────────────────────
    @pytest.mark.parametrize("r,f,m,expected", [
        pytest.param(1, 1, 1, "低价值客户", id="min_all"),
        pytest.param(2, 2, 2, "低价值客户", id="max_boundary"),
        pytest.param(1, 2, 1, "低价值客户", id="r1_f2_m1"),
        pytest.param(2, 1, 2, "低价值客户", id="r2_f1_m2"),
        pytest.param(1, 1, 2, "低价值客户", id="r1_f1_m2"),
        pytest.param(2, 2, 1, "低价值客户", id="r2_f2_m1"),
    ])
    def test_low_value(self, r, f, m, expected):
        assert _compute_segment(r, f, m) == expected

    # ── 流失预警: r <= 2, f >= 3 (any m) ────────────────────────────
    @pytest.mark.parametrize("r,f,m,expected", [
        pytest.param(1, 3, 1, "流失预警", id="r1_f3_m1"),
        pytest.param(2, 4, 5, "流失预警", id="r2_f4_m5"),
        pytest.param(1, 5, 2, "流失预警", id="r1_f5_m2"),
        pytest.param(2, 3, 3, "流失预警", id="r2_f3_m3"),
        pytest.param(1, 3, 5, "流失预警", id="r1_f3_m5"),
        pytest.param(2, 5, 1, "流失预警", id="r2_f5_m1"),
    ])
    def test_churn_warning(self, r, f, m, expected):
        assert _compute_segment(r, f, m) == expected

    # ── 一般客户: everything else ────────────────────────────────────
    @pytest.mark.parametrize("r,f,m,expected", [
        # r >= 3 but f < 3 → no rule matches
        pytest.param(3, 2, 5, "一般客户", id="r3_f2_m5"),
        pytest.param(4, 2, 3, "一般客户", id="r4_f2_m3"),
        pytest.param(3, 1, 4, "一般客户", id="r3_f1_m4"),
        pytest.param(5, 2, 2, "一般客户", id="r5_f2_m2"),
        # r >= 3, f >= 3 but m < 3 → no rule matches
        pytest.param(3, 3, 2, "一般客户", id="r3_f3_m2"),
        pytest.param(4, 5, 2, "一般客户", id="r4_f5_m2"),
        pytest.param(5, 3, 1, "一般客户", id="r5_f3_m1"),
        # r >= 3, m >= 3 but f < 3 → no rule matches
        pytest.param(3, 2, 3, "一般客户", id="r3_f2_m3"),
        pytest.param(5, 1, 5, "一般客户", id="r5_f1_m5"),
        # r <= 2 but f < 3 and m > 2 → only rule 4 fails too
        pytest.param(2, 2, 5, "一般客户", id="r2_f2_m5"),
        pytest.param(1, 1, 5, "一般客户", id="r1_f1_m5"),
    ])
    def test_general(self, r, f, m, expected):
        assert _compute_segment(r, f, m) == expected

    # ── All valid scores 1-5 return valid segment strings ────────────
    @pytest.mark.parametrize("r", [1, 2, 3, 4, 5])
    @pytest.mark.parametrize("f", [1, 2, 3, 4, 5])
    @pytest.mark.parametrize("m", [1, 2, 3, 4, 5])
    def test_all_valid_scores_return_valid_segment(self, r, f, m):
        """Every combination of scores 1-5 returns one of the 5 segments."""
        result = _compute_segment(r, f, m)
        assert result in VALID_SEGMENTS, f"({r},{f},{m}) → '{result}' not in {VALID_SEGMENTS}"

    # ── Out-of-range scores ──────────────────────────────────────────
    @pytest.mark.parametrize("r,f,m", [
        pytest.param(0, 5, 5, id="r_zero"),
        pytest.param(6, 6, 6, id="all_above_range"),
        pytest.param(0, 0, 0, id="all_zero"),
        pytest.param(6, 1, 2, id="r_above_range"),
        pytest.param(3, 6, 4, id="f_above_range"),
        pytest.param(4, 3, 6, id="m_above_range"),
        pytest.param(-1, 3, 4, id="r_negative"),
    ])
    def test_out_of_range_scores(self, r, f, m):
        """Out-of-range scores don't crash and return a valid segment."""
        result = _compute_segment(r, f, m)
        assert isinstance(result, str)
        assert result in VALID_SEGMENTS, f"({r},{f},{m}) → '{result}' unexpected"
