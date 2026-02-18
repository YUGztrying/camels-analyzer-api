"""
Unit tests for camels_calculator.py

Tests every ratio formula and rating function with known inputs/outputs
to ensure correctness against the CAMELS cheat sheet.
"""
import pytest
from types import SimpleNamespace

from camels_calculator import (
    _safe_divide,
    _calculate_average,
    _get,
    _pct,
    _rating_label,
    calculate_all_ratios,
    rate_capital,
    rate_asset_quality,
    rate_management,
    rate_earnings,
    rate_liquidity,
    get_composite_rating,
    generate_analysis_paragraphs,
)


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------

class TestSafeDivide:
    def test_normal(self):
        assert _safe_divide(10, 2) == 5.0

    def test_zero_denominator(self):
        assert _safe_divide(10, 0) is None

    def test_none_denominator(self):
        assert _safe_divide(10, None) is None

    def test_none_numerator(self):
        assert _safe_divide(None, 5) is None

    def test_both_none(self):
        assert _safe_divide(None, None) is None

    def test_negative_values(self):
        assert _safe_divide(-10, 2) == -5.0

    def test_float_precision(self):
        result = _safe_divide(1, 3)
        assert abs(result - 0.333333) < 0.001


class TestCalculateAverage:
    def test_with_previous(self):
        assert _calculate_average(100, 80) == 90.0

    def test_without_previous(self):
        assert _calculate_average(100) == 100

    def test_previous_none(self):
        assert _calculate_average(100, None) == 100

    def test_previous_zero(self):
        assert _calculate_average(100, 0) == 100

    def test_current_zero_with_previous(self):
        # current is 0 (valid number), previous exists -> averages them
        assert _calculate_average(0, 80) == 40.0

    def test_both_zero(self):
        assert _calculate_average(0, 0) is None

    def test_current_none(self):
        # current is None, no previous -> None
        assert _calculate_average(None) is None

    def test_current_none_with_previous(self):
        # current is None, previous exists -> returns previous
        assert _calculate_average(None, 80) == 80


class TestGet:
    def test_existing_attr(self):
        obj = SimpleNamespace(total_assets=1000)
        assert _get(obj, 'total_assets') == 1000

    def test_missing_attr(self):
        obj = SimpleNamespace()
        assert _get(obj, 'total_assets') is None

    def test_none_attr(self):
        obj = SimpleNamespace(total_assets=None)
        assert _get(obj, 'total_assets') is None

    def test_custom_default(self):
        obj = SimpleNamespace()
        assert _get(obj, 'total_assets', 999) == 999

    def test_zero_is_valid(self):
        obj = SimpleNamespace(total_assets=0)
        assert _get(obj, 'total_assets') == 0

    def test_none_obj(self):
        assert _get(None, 'total_assets') is None

    def test_none_obj_with_default(self):
        assert _get(None, 'total_assets', 42) == 42


class TestPct:
    def test_format(self):
        assert _pct(0.12) == "12.00%"

    def test_none(self):
        assert _pct(None) == "N/A"

    def test_zero(self):
        assert _pct(0) == "0.00%"

    def test_negative(self):
        assert _pct(-0.05) == "-5.00%"


class TestRatingLabel:
    def test_all_labels(self):
        assert _rating_label(1) == "Strong"
        assert _rating_label(2) == "Satisfactory"
        assert _rating_label(3) == "Fair"
        assert _rating_label(4) == "Marginal"
        assert _rating_label(5) == "Unsatisfactory"

    def test_invalid(self):
        assert _rating_label(0) == "N/A"
        assert _rating_label(6) == "N/A"


# ---------------------------------------------------------------------------
# Bank fixture — a SimpleNamespace that mimics BankDB
# ---------------------------------------------------------------------------

def _make_bank(**overrides):
    """Create a bank-like object with sensible defaults for testing."""
    defaults = dict(
        bank_name="Test Bank",
        country="Senegal",
        fiscal_year="2023",
        currency="XOF",
        # Balance sheet
        total_assets=1_000_000,
        total_equity=120_000,
        total_liabilities=880_000,
        cash_reserves_requirements=50_000,
        due_from_banks=30_000,
        investment_securities=100_000,
        gross_loans=600_000,
        loan_loss_provisions=-30_000,
        foreclosed_assets=5_000,
        fixed_assets=40_000,
        other_assets=10_000,
        deposits=700_000,
        short_term_borrowings=50_000,
        long_term_debt=80_000,
        interbank_liabilities=30_000,
        other_liabilities=20_000,
        paid_in_capital=60_000,
        reserves=40_000,
        retained_earnings=10_000,
        net_profit=10_000,
        investment_in_subs_affiliates=None,
        # Income statement
        interest_income=80_000,
        interest_expenses=30_000,
        net_interest_income=50_000,
        fees_commissions=8_000,
        net_sales=0,
        dividends=1_000,
        fvtpl_changes=0,
        securitization_gains=0,
        provisions_no_longer_required=2_000,
        share_profit_associates=0,
        other_revenues=3_000,
        gain_acquisition_subsidiaries=0,
        non_interest_income_commissions=14_000,
        net_income_investment=0,
        other_net_income=0,
        wages_salaries=15_000,
        other_opex=10_000,
        intangible_amortization=2_000,
        fixed_asset_depreciation=3_000,
        operating_expenses=30_000,
        operating_income=64_000,
        operating_profit=34_000,
        provision_expenses=10_000,
        provisions_formed=5_000,
        impairment_financial_assets=2_000,
        fx_exchange=1_000,
        non_operating_profit_loss=0,
        income_tax=5_000,
        net_income=10_000,
        # NPL data
        npls_mn=20_000,
        llr_mn=25_000,
        car_regulatory=14.3,
        car_bank_reported=None,
        # Reported ratios
        npl_ratio_reported=None,
        coverage_ratio_reported=None,
        roe_reported=None,
        roa_reported=None,
        cost_income_reported=None,
        # FX
        fx_rate_period_end=None,
        fx_rate_period_avg=None,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


# ---------------------------------------------------------------------------
# Ratio calculation tests
# ---------------------------------------------------------------------------

class TestCalculateAllRatios:

    def test_equity_assets(self):
        bank = _make_bank(total_equity=120_000, total_assets=1_000_000)
        bank = calculate_all_ratios(bank)
        assert abs(bank.equity_assets - 0.12) < 1e-9

    def test_debt_assets(self):
        bank = _make_bank(short_term_borrowings=50_000, long_term_debt=80_000, total_assets=1_000_000)
        bank = calculate_all_ratios(bank)
        assert abs(bank.debt_assets - 0.13) < 1e-9

    def test_debt_assets_no_debt(self):
        bank = _make_bank(short_term_borrowings=None, long_term_debt=None)
        bank = calculate_all_ratios(bank)
        assert bank.debt_assets is None

    def test_debt_assets_zero_debt(self):
        bank = _make_bank(short_term_borrowings=0, long_term_debt=0)
        bank = calculate_all_ratios(bank)
        assert bank.debt_assets == 0.0

    def test_npl_ratio(self):
        bank = _make_bank(npls_mn=20_000, gross_loans=600_000)
        bank = calculate_all_ratios(bank)
        expected = 20_000 / 600_000
        assert abs(bank.npl_ratio - expected) < 1e-9

    def test_coverage_ratio(self):
        bank = _make_bank(loan_loss_provisions=-30_000, npls_mn=20_000)
        bank = calculate_all_ratios(bank)
        expected = 30_000 / 20_000  # abs(provisions) / NPLs
        assert abs(bank.coverage_ratio - expected) < 1e-9

    def test_cost_of_risk(self):
        bank = _make_bank(provision_expenses=10_000, total_assets=1_000_000)
        bank = calculate_all_ratios(bank)
        expected = 10_000 / 1_000_000
        assert abs(bank.cost_of_risk_avg_assets - expected) < 1e-9

    def test_cost_to_income(self):
        bank = _make_bank(operating_expenses=30_000, operating_income=64_000)
        bank = calculate_all_ratios(bank)
        expected = 30_000 / 64_000
        assert abs(bank.cost_to_income - expected) < 1e-9

    def test_roaa(self):
        bank = _make_bank(net_income=10_000, total_assets=1_000_000)
        bank = calculate_all_ratios(bank)
        expected = 10_000 / 1_000_000
        assert abs(bank.roaa - expected) < 1e-9

    def test_roae(self):
        bank = _make_bank(net_income=10_000, total_equity=120_000)
        bank = calculate_all_ratios(bank)
        expected = 10_000 / 120_000
        assert abs(bank.roae - expected) < 1e-9

    def test_nii_avg_assets(self):
        bank = _make_bank(net_interest_income=50_000, total_assets=1_000_000)
        bank = calculate_all_ratios(bank)
        expected = 50_000 / 1_000_000
        assert abs(bank.net_interest_income_avg_assets - expected) < 1e-9

    def test_liquid_assets_total_assets(self):
        bank = _make_bank(
            cash_reserves_requirements=50_000,
            due_from_banks=30_000,
            investment_securities=100_000,
            total_assets=1_000_000,
        )
        bank = calculate_all_ratios(bank)
        expected = (50_000 + 30_000 + 100_000) / 1_000_000
        assert abs(bank.liquid_assets_total_assets - expected) < 1e-9

    def test_gross_loans_deposits(self):
        bank = _make_bank(gross_loans=600_000, deposits=700_000)
        bank = calculate_all_ratios(bank)
        expected = 600_000 / 700_000
        assert abs(bank.gross_loans_deposits - expected) < 1e-9

    def test_opex_avg_assets_granular(self):
        bank = _make_bank(
            wages_salaries=15_000,
            other_opex=10_000,
            intangible_amortization=2_000,
            fixed_asset_depreciation=3_000,
            total_assets=1_000_000,
        )
        bank = calculate_all_ratios(bank)
        expected = 30_000 / 1_000_000
        assert abs(bank.opex_avg_assets - expected) < 1e-9

    def test_tax_expenses_avg_assets(self):
        bank = _make_bank(income_tax=5_000, total_assets=1_000_000)
        bank = calculate_all_ratios(bank)
        expected = 5_000 / 1_000_000
        assert abs(bank.tax_expenses_avg_assets - expected) < 1e-9

    def test_with_previous_bank(self):
        bank = _make_bank(net_income=10_000, total_assets=1_200_000, total_equity=140_000)
        prev = _make_bank(total_assets=800_000, total_equity=100_000)
        bank = calculate_all_ratios(bank, prev_bank=prev)
        avg_assets = (1_200_000 + 800_000) / 2  # 1_000_000
        avg_equity = (140_000 + 100_000) / 2  # 120_000
        assert abs(bank.roaa - 10_000 / avg_assets) < 1e-9
        assert abs(bank.roae - 10_000 / avg_equity) < 1e-9

    def test_npl_ratio_fallback_to_reported(self):
        bank = _make_bank(npls_mn=None, gross_loans=600_000, npl_ratio_reported=5.2)
        bank = calculate_all_ratios(bank)
        assert abs(bank.npl_ratio - 0.052) < 1e-9

    def test_roae_fallback_to_reported(self):
        bank = _make_bank(net_income=None, net_profit=None, roe_reported=28.5)
        bank = calculate_all_ratios(bank)
        assert abs(bank.roae - 0.285) < 1e-9

    def test_cost_to_income_fallback_to_reported(self):
        bank = _make_bank(operating_expenses=None, operating_income=None, cost_income_reported=55.0)
        bank = calculate_all_ratios(bank)
        assert abs(bank.cost_to_income - 0.55) < 1e-9

    def test_none_fields_produce_none_not_zero(self):
        """Verify that missing data shows as None (N/A), not false 0.00%."""
        bank = _make_bank(
            npls_mn=None, gross_loans=600_000,
            cash_reserves_requirements=None, due_from_banks=None, investment_securities=None,
            npl_ratio_reported=None,
        )
        bank = calculate_all_ratios(bank)
        assert bank.npl_ratio is None
        assert bank.liquid_assets_total_assets is None

    def test_all_zeros_no_crash(self):
        bank = _make_bank(
            total_assets=0, total_equity=0, gross_loans=0,
            npls_mn=0, net_income=0, deposits=0,
            operating_expenses=0, operating_income=0,
            short_term_borrowings=0, long_term_debt=0,
            loan_loss_provisions=0, provision_expenses=0,
            cash_reserves_requirements=0, due_from_banks=0,
            investment_securities=0, interest_income=0,
            interest_expenses=0, net_interest_income=0,
        )
        # Should not raise
        bank = calculate_all_ratios(bank)
        assert bank is not None

    def test_all_none_no_crash(self):
        bank = _make_bank(
            total_assets=1000,  # must be non-zero for some calcs
            total_equity=None, gross_loans=None,
            npls_mn=None, net_income=None, deposits=None,
            operating_expenses=None, operating_income=None,
            short_term_borrowings=None, long_term_debt=None,
            loan_loss_provisions=None, provision_expenses=None,
            cash_reserves_requirements=None, due_from_banks=None,
            investment_securities=None,
        )
        bank = calculate_all_ratios(bank)
        assert bank is not None


# ---------------------------------------------------------------------------
# Rating function tests
# ---------------------------------------------------------------------------

class TestRateCapital:
    def test_strong(self):
        bank = SimpleNamespace(equity_assets=0.15)
        assert rate_capital(bank)["rating"] == 1

    def test_satisfactory(self):
        bank = SimpleNamespace(equity_assets=0.10, debt_assets=0.2)
        result = rate_capital(bank)
        assert result["rating"] == 2

    def test_fair(self):
        bank = SimpleNamespace(equity_assets=0.07, debt_assets=None)
        assert rate_capital(bank)["rating"] == 3

    def test_marginal(self):
        bank = SimpleNamespace(equity_assets=0.05)
        assert rate_capital(bank)["rating"] == 4

    def test_unsatisfactory(self):
        bank = SimpleNamespace(equity_assets=0.02)
        assert rate_capital(bank)["rating"] == 5

    def test_none(self):
        bank = SimpleNamespace(equity_assets=None)
        assert rate_capital(bank)["rating"] is None

    def test_boundary_12_pct(self):
        bank = SimpleNamespace(equity_assets=0.12, debt_assets=None)
        assert rate_capital(bank)["rating"] == 1

    def test_boundary_9_pct(self):
        bank = SimpleNamespace(equity_assets=0.09, debt_assets=None)
        assert rate_capital(bank)["rating"] == 2


class TestRateAssetQuality:
    def test_strong(self):
        bank = SimpleNamespace(npl_ratio=0.01, coverage_ratio=1.2, cost_of_risk_avg_assets=0.005)
        assert rate_asset_quality(bank)["rating"] == 1

    def test_satisfactory(self):
        bank = SimpleNamespace(npl_ratio=0.04, coverage_ratio=0.9, cost_of_risk_avg_assets=0.01)
        assert rate_asset_quality(bank)["rating"] == 2

    def test_fair(self):
        bank = SimpleNamespace(npl_ratio=0.06, coverage_ratio=None, cost_of_risk_avg_assets=None)
        assert rate_asset_quality(bank)["rating"] == 3

    def test_marginal(self):
        bank = SimpleNamespace(npl_ratio=0.10, coverage_ratio=None, cost_of_risk_avg_assets=None)
        assert rate_asset_quality(bank)["rating"] == 4

    def test_unsatisfactory(self):
        bank = SimpleNamespace(npl_ratio=0.15, coverage_ratio=None, cost_of_risk_avg_assets=None)
        assert rate_asset_quality(bank)["rating"] == 5

    def test_none(self):
        bank = SimpleNamespace(npl_ratio=None)
        assert rate_asset_quality(bank)["rating"] is None


class TestRateManagement:
    def test_strong(self):
        bank = SimpleNamespace(cost_to_income=0.35)
        assert rate_management(bank)["rating"] == 1

    def test_satisfactory(self):
        bank = SimpleNamespace(cost_to_income=0.50)
        assert rate_management(bank)["rating"] == 2

    def test_fair(self):
        bank = SimpleNamespace(cost_to_income=0.65)
        assert rate_management(bank)["rating"] == 3

    def test_marginal(self):
        bank = SimpleNamespace(cost_to_income=0.80)
        assert rate_management(bank)["rating"] == 4

    def test_unsatisfactory(self):
        bank = SimpleNamespace(cost_to_income=0.90)
        assert rate_management(bank)["rating"] == 5

    def test_none(self):
        bank = SimpleNamespace(cost_to_income=None)
        assert rate_management(bank)["rating"] is None


class TestRateEarnings:
    def test_strong(self):
        bank = SimpleNamespace(roae=0.20, roaa=0.03, net_interest_income_avg_assets=0.05,
                               non_interest_income_avg_assets=0.02, opex_avg_assets=0.03,
                               tax_expenses_avg_assets=0.005, other_income_avg_assets=0.001)
        assert rate_earnings(bank)["rating"] == 1

    def test_satisfactory(self):
        bank = SimpleNamespace(roae=0.12, roaa=0.02, net_interest_income_avg_assets=None,
                               non_interest_income_avg_assets=None, opex_avg_assets=None,
                               tax_expenses_avg_assets=None, other_income_avg_assets=None)
        assert rate_earnings(bank)["rating"] == 2

    def test_fair(self):
        bank = SimpleNamespace(roae=0.07, roaa=None, net_interest_income_avg_assets=None,
                               non_interest_income_avg_assets=None, opex_avg_assets=None,
                               tax_expenses_avg_assets=None, other_income_avg_assets=None)
        assert rate_earnings(bank)["rating"] == 3

    def test_marginal(self):
        bank = SimpleNamespace(roae=0.02, roaa=None, net_interest_income_avg_assets=None,
                               non_interest_income_avg_assets=None, opex_avg_assets=None,
                               tax_expenses_avg_assets=None, other_income_avg_assets=None)
        assert rate_earnings(bank)["rating"] == 4

    def test_unsatisfactory(self):
        bank = SimpleNamespace(roae=-0.05, roaa=None, net_interest_income_avg_assets=None,
                               non_interest_income_avg_assets=None, opex_avg_assets=None,
                               tax_expenses_avg_assets=None, other_income_avg_assets=None)
        assert rate_earnings(bank)["rating"] == 5

    def test_none(self):
        bank = SimpleNamespace(roae=None)
        assert rate_earnings(bank)["rating"] is None


class TestRateLiquidity:
    def test_strong(self):
        bank = SimpleNamespace(liquid_assets_total_assets=0.40)
        assert rate_liquidity(bank)["rating"] == 1

    def test_satisfactory(self):
        bank = SimpleNamespace(liquid_assets_total_assets=0.30)
        assert rate_liquidity(bank)["rating"] == 2

    def test_fair(self):
        bank = SimpleNamespace(liquid_assets_total_assets=0.20)
        assert rate_liquidity(bank)["rating"] == 3

    def test_marginal(self):
        bank = SimpleNamespace(liquid_assets_total_assets=0.12)
        assert rate_liquidity(bank)["rating"] == 4

    def test_unsatisfactory(self):
        bank = SimpleNamespace(liquid_assets_total_assets=0.05)
        assert rate_liquidity(bank)["rating"] == 5

    def test_none(self):
        bank = SimpleNamespace(liquid_assets_total_assets=None)
        assert rate_liquidity(bank)["rating"] is None


class TestCompositeRating:
    def test_average(self):
        c = {"rating": 1}
        a = {"rating": 2}
        m = {"rating": 3}
        e = {"rating": 2}
        l = {"rating": 2}
        result = get_composite_rating(c, a, m, e, l)
        assert result["composite_rating"] == 2
        assert result["average"] == 2.0

    def test_rounds_up(self):
        # avg = 2.6 -> rounds to 3
        c = {"rating": 2}
        a = {"rating": 3}
        m = {"rating": 3}
        e = {"rating": 3}
        l = {"rating": 2}
        result = get_composite_rating(c, a, m, e, l)
        assert result["composite_rating"] == 3

    def test_some_none(self):
        c = {"rating": 1}
        a = {"rating": None}
        m = {"rating": 3}
        e = {"rating": None}
        l = {"rating": 2}
        result = get_composite_rating(c, a, m, e, l)
        assert result["components_used"] == 3
        assert result["composite_rating"] == 2

    def test_all_none(self):
        none_rating = {"rating": None}
        result = get_composite_rating(none_rating, none_rating, none_rating, none_rating, none_rating)
        assert result["composite_rating"] is None


# ---------------------------------------------------------------------------
# Analysis paragraph tests
# ---------------------------------------------------------------------------

class TestGenerateAnalysisParagraphs:
    def test_returns_all_sections(self):
        bank = _make_bank()
        bank = calculate_all_ratios(bank)
        ratings = {
            "capital": rate_capital(bank),
            "asset_quality": rate_asset_quality(bank),
            "management": rate_management(bank),
            "earnings": rate_earnings(bank),
            "liquidity": rate_liquidity(bank),
        }
        ratings["composite"] = get_composite_rating(
            ratings["capital"], ratings["asset_quality"],
            ratings["management"], ratings["earnings"], ratings["liquidity"]
        )
        paragraphs = generate_analysis_paragraphs(bank, ratings)

        assert "capital" in paragraphs
        assert "asset_quality" in paragraphs
        assert "management" in paragraphs
        assert "earnings" in paragraphs
        assert "liquidity" in paragraphs
        assert "composite" in paragraphs

    def test_writes_to_bank_object(self):
        bank = _make_bank()
        bank = calculate_all_ratios(bank)
        ratings = {
            "capital": rate_capital(bank),
            "asset_quality": rate_asset_quality(bank),
            "management": rate_management(bank),
            "earnings": rate_earnings(bank),
            "liquidity": rate_liquidity(bank),
        }
        ratings["composite"] = get_composite_rating(
            ratings["capital"], ratings["asset_quality"],
            ratings["management"], ratings["earnings"], ratings["liquidity"]
        )
        generate_analysis_paragraphs(bank, ratings)

        assert bank.analysis_capital is not None
        assert bank.analysis_asset_quality is not None
        assert bank.analysis_management is not None
        assert bank.analysis_earnings is not None
        assert bank.analysis_liquidity is not None
        assert bank.analysis_composite is not None

    def test_paragraphs_contain_bank_name(self):
        bank = _make_bank(bank_name="Banque Atlantique")
        bank = calculate_all_ratios(bank)
        ratings = {
            "capital": rate_capital(bank),
            "asset_quality": rate_asset_quality(bank),
            "management": rate_management(bank),
            "earnings": rate_earnings(bank),
            "liquidity": rate_liquidity(bank),
        }
        ratings["composite"] = get_composite_rating(
            ratings["capital"], ratings["asset_quality"],
            ratings["management"], ratings["earnings"], ratings["liquidity"]
        )
        paragraphs = generate_analysis_paragraphs(bank, ratings)
        assert "Banque Atlantique" in paragraphs["capital"]
