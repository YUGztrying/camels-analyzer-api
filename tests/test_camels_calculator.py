"""
Unit tests for camels_calculator.py

Tests every ratio formula and rating function with known inputs/outputs
to ensure correctness against the CAMELS cheat sheet.
All functions now work with plain dicts.
"""
import pytest

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
    run_full_analysis,
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
        assert _calculate_average(0, 80) == 80

    def test_both_zero(self):
        assert _calculate_average(0, 0) == 0

    def test_current_none(self):
        assert _calculate_average(None) == 0


class TestGet:
    def test_existing_key(self):
        data = {"total_assets": 1000}
        assert _get(data, 'total_assets') == 1000

    def test_missing_key(self):
        data = {}
        assert _get(data, 'total_assets') == 0

    def test_none_value(self):
        data = {"total_assets": None}
        assert _get(data, 'total_assets') == 0

    def test_custom_default(self):
        data = {}
        assert _get(data, 'total_assets', 999) == 999

    def test_zero_is_valid(self):
        data = {"total_assets": 0}
        assert _get(data, 'total_assets') == 0

    def test_none_data(self):
        assert _get(None, 'total_assets') == 0


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
# Statement fixture — a plain dict mimicking a Supabase row
# ---------------------------------------------------------------------------

def _make_statement(**overrides):
    """Create a financial statement dict with sensible defaults."""
    defaults = dict(
        bank_name="Test Bank",
        name="Test Bank",
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
    )
    defaults.update(overrides)
    return defaults


# ---------------------------------------------------------------------------
# Ratio calculation tests
# ---------------------------------------------------------------------------

class TestCalculateAllRatios:

    def test_equity_assets(self):
        stmt = _make_statement(total_equity=120_000, total_assets=1_000_000)
        ratios = calculate_all_ratios(stmt)
        assert abs(ratios['equity_assets'] - 0.12) < 1e-9

    def test_debt_assets(self):
        stmt = _make_statement(short_term_borrowings=50_000, long_term_debt=80_000, total_assets=1_000_000)
        ratios = calculate_all_ratios(stmt)
        assert abs(ratios['debt_assets'] - 0.13) < 1e-9

    def test_debt_assets_no_debt(self):
        stmt = _make_statement(short_term_borrowings=0, long_term_debt=0)
        ratios = calculate_all_ratios(stmt)
        assert ratios['debt_assets'] is None

    def test_npl_ratio(self):
        stmt = _make_statement(npls_mn=20_000, gross_loans=600_000)
        ratios = calculate_all_ratios(stmt)
        expected = 20_000 / 600_000
        assert abs(ratios['npl_ratio'] - expected) < 1e-9

    def test_coverage_ratio(self):
        stmt = _make_statement(loan_loss_provisions=-30_000, npls_mn=20_000)
        ratios = calculate_all_ratios(stmt)
        expected = 30_000 / 20_000
        assert abs(ratios['coverage_ratio'] - expected) < 1e-9

    def test_cost_of_risk(self):
        stmt = _make_statement(provision_expenses=10_000, total_assets=1_000_000)
        ratios = calculate_all_ratios(stmt)
        expected = 10_000 / 1_000_000
        assert abs(ratios['cost_of_risk_avg_assets'] - expected) < 1e-9

    def test_cost_to_income(self):
        stmt = _make_statement(operating_expenses=30_000, operating_income=64_000)
        ratios = calculate_all_ratios(stmt)
        expected = 30_000 / 64_000
        assert abs(ratios['cost_to_income'] - expected) < 1e-9

    def test_roaa(self):
        stmt = _make_statement(net_income=10_000, total_assets=1_000_000)
        ratios = calculate_all_ratios(stmt)
        expected = 10_000 / 1_000_000
        assert abs(ratios['roaa'] - expected) < 1e-9

    def test_roae(self):
        stmt = _make_statement(net_income=10_000, total_equity=120_000)
        ratios = calculate_all_ratios(stmt)
        expected = 10_000 / 120_000
        assert abs(ratios['roae'] - expected) < 1e-9

    def test_nii_avg_assets(self):
        stmt = _make_statement(net_interest_income=50_000, total_assets=1_000_000)
        ratios = calculate_all_ratios(stmt)
        expected = 50_000 / 1_000_000
        assert abs(ratios['net_interest_income_avg_assets'] - expected) < 1e-9

    def test_liquid_assets_total_assets(self):
        stmt = _make_statement(
            cash_reserves_requirements=50_000,
            due_from_banks=30_000,
            investment_securities=100_000,
            total_assets=1_000_000,
        )
        ratios = calculate_all_ratios(stmt)
        expected = (50_000 + 30_000 + 100_000) / 1_000_000
        assert abs(ratios['liquid_assets_total_assets'] - expected) < 1e-9

    def test_gross_loans_deposits(self):
        stmt = _make_statement(gross_loans=600_000, deposits=700_000)
        ratios = calculate_all_ratios(stmt)
        expected = 600_000 / 700_000
        assert abs(ratios['gross_loans_deposits'] - expected) < 1e-9

    def test_opex_avg_assets_granular(self):
        stmt = _make_statement(
            wages_salaries=15_000,
            other_opex=10_000,
            intangible_amortization=2_000,
            fixed_asset_depreciation=3_000,
            total_assets=1_000_000,
        )
        ratios = calculate_all_ratios(stmt)
        expected = 30_000 / 1_000_000
        assert abs(ratios['opex_avg_assets'] - expected) < 1e-9

    def test_tax_expenses_avg_assets(self):
        stmt = _make_statement(income_tax=5_000, total_assets=1_000_000)
        ratios = calculate_all_ratios(stmt)
        expected = 5_000 / 1_000_000
        assert abs(ratios['tax_expenses_avg_assets'] - expected) < 1e-9

    def test_with_previous_statement(self):
        stmt = _make_statement(net_income=10_000, total_assets=1_200_000, total_equity=140_000)
        prev = _make_statement(total_assets=800_000, total_equity=100_000)
        ratios = calculate_all_ratios(stmt, prev_statement=prev)
        avg_assets = (1_200_000 + 800_000) / 2
        avg_equity = (140_000 + 100_000) / 2
        assert abs(ratios['roaa'] - 10_000 / avg_assets) < 1e-9
        assert abs(ratios['roae'] - 10_000 / avg_equity) < 1e-9

    def test_returns_dict_not_mutating_input(self):
        stmt = _make_statement()
        original_keys = set(stmt.keys())
        ratios = calculate_all_ratios(stmt)
        # Input dict should not have new keys
        assert set(stmt.keys()) == original_keys
        # Return value should be a separate dict
        assert isinstance(ratios, dict)
        assert 'equity_assets' in ratios

    def test_all_zeros_no_crash(self):
        stmt = _make_statement(
            total_assets=0, total_equity=0, gross_loans=0,
            npls_mn=0, net_income=0, deposits=0,
            operating_expenses=0, operating_income=0,
            short_term_borrowings=0, long_term_debt=0,
            loan_loss_provisions=0, provision_expenses=0,
            cash_reserves_requirements=0, due_from_banks=0,
            investment_securities=0, interest_income=0,
            interest_expenses=0, net_interest_income=0,
        )
        ratios = calculate_all_ratios(stmt)
        assert isinstance(ratios, dict)

    def test_all_none_no_crash(self):
        stmt = _make_statement(
            total_assets=1000,
            total_equity=None, gross_loans=None,
            npls_mn=None, net_income=None, deposits=None,
            operating_expenses=None, operating_income=None,
            short_term_borrowings=None, long_term_debt=None,
            loan_loss_provisions=None, provision_expenses=None,
            cash_reserves_requirements=None, due_from_banks=None,
            investment_securities=None,
        )
        ratios = calculate_all_ratios(stmt)
        assert isinstance(ratios, dict)


# ---------------------------------------------------------------------------
# Rating function tests (now take dicts of ratios)
# ---------------------------------------------------------------------------

class TestRateCapital:
    def test_strong(self):
        assert rate_capital({"equity_assets": 0.15})["rating"] == 1

    def test_satisfactory(self):
        result = rate_capital({"equity_assets": 0.10, "debt_assets": 0.2})
        assert result["rating"] == 2

    def test_fair(self):
        assert rate_capital({"equity_assets": 0.07})["rating"] == 3

    def test_marginal(self):
        assert rate_capital({"equity_assets": 0.05})["rating"] == 4

    def test_unsatisfactory(self):
        assert rate_capital({"equity_assets": 0.02})["rating"] == 5

    def test_none(self):
        assert rate_capital({"equity_assets": None})["rating"] is None

    def test_missing_key(self):
        assert rate_capital({})["rating"] is None

    def test_boundary_12_pct(self):
        assert rate_capital({"equity_assets": 0.12})["rating"] == 1

    def test_boundary_9_pct(self):
        assert rate_capital({"equity_assets": 0.09})["rating"] == 2


class TestRateAssetQuality:
    def test_strong(self):
        assert rate_asset_quality({"npl_ratio": 0.01})["rating"] == 1

    def test_satisfactory(self):
        assert rate_asset_quality({"npl_ratio": 0.04})["rating"] == 2

    def test_fair(self):
        assert rate_asset_quality({"npl_ratio": 0.06})["rating"] == 3

    def test_marginal(self):
        assert rate_asset_quality({"npl_ratio": 0.10})["rating"] == 4

    def test_unsatisfactory(self):
        assert rate_asset_quality({"npl_ratio": 0.15})["rating"] == 5

    def test_none(self):
        assert rate_asset_quality({"npl_ratio": None})["rating"] is None


class TestRateManagement:
    def test_strong(self):
        assert rate_management({"cost_to_income": 0.35})["rating"] == 1

    def test_satisfactory(self):
        assert rate_management({"cost_to_income": 0.50})["rating"] == 2

    def test_fair(self):
        assert rate_management({"cost_to_income": 0.65})["rating"] == 3

    def test_marginal(self):
        assert rate_management({"cost_to_income": 0.80})["rating"] == 4

    def test_unsatisfactory(self):
        assert rate_management({"cost_to_income": 0.90})["rating"] == 5

    def test_none(self):
        assert rate_management({"cost_to_income": None})["rating"] is None


class TestRateEarnings:
    def test_strong(self):
        assert rate_earnings({"roae": 0.20})["rating"] == 1

    def test_satisfactory(self):
        assert rate_earnings({"roae": 0.12})["rating"] == 2

    def test_fair(self):
        assert rate_earnings({"roae": 0.07})["rating"] == 3

    def test_marginal(self):
        assert rate_earnings({"roae": 0.02})["rating"] == 4

    def test_unsatisfactory(self):
        assert rate_earnings({"roae": -0.05})["rating"] == 5

    def test_none(self):
        assert rate_earnings({"roae": None})["rating"] is None


class TestRateLiquidity:
    def test_strong(self):
        assert rate_liquidity({"liquid_assets_total_assets": 0.40})["rating"] == 1

    def test_satisfactory(self):
        assert rate_liquidity({"liquid_assets_total_assets": 0.30})["rating"] == 2

    def test_fair(self):
        assert rate_liquidity({"liquid_assets_total_assets": 0.20})["rating"] == 3

    def test_marginal(self):
        assert rate_liquidity({"liquid_assets_total_assets": 0.12})["rating"] == 4

    def test_unsatisfactory(self):
        assert rate_liquidity({"liquid_assets_total_assets": 0.05})["rating"] == 5

    def test_none(self):
        assert rate_liquidity({"liquid_assets_total_assets": None})["rating"] is None


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
        stmt = _make_statement()
        ratios = calculate_all_ratios(stmt)
        ratings = {
            "capital": rate_capital(ratios),
            "asset_quality": rate_asset_quality(ratios),
            "management": rate_management(ratios),
            "earnings": rate_earnings(ratios),
            "liquidity": rate_liquidity(ratios),
        }
        ratings["composite"] = get_composite_rating(
            ratings["capital"], ratings["asset_quality"],
            ratings["management"], ratings["earnings"], ratings["liquidity"]
        )
        paragraphs = generate_analysis_paragraphs(stmt, ratios, ratings)

        assert "capital" in paragraphs
        assert "asset_quality" in paragraphs
        assert "management" in paragraphs
        assert "earnings" in paragraphs
        assert "liquidity" in paragraphs
        assert "composite" in paragraphs

    def test_paragraphs_contain_bank_name(self):
        stmt = _make_statement(bank_name="Banque Atlantique", name="Banque Atlantique")
        ratios = calculate_all_ratios(stmt)
        ratings = {
            "capital": rate_capital(ratios),
            "asset_quality": rate_asset_quality(ratios),
            "management": rate_management(ratios),
            "earnings": rate_earnings(ratios),
            "liquidity": rate_liquidity(ratios),
        }
        ratings["composite"] = get_composite_rating(
            ratings["capital"], ratings["asset_quality"],
            ratings["management"], ratings["earnings"], ratings["liquidity"]
        )
        paragraphs = generate_analysis_paragraphs(stmt, ratios, ratings)
        assert "Banque Atlantique" in paragraphs["capital"]

    def test_does_not_mutate_input(self):
        stmt = _make_statement()
        original_keys = set(stmt.keys())
        ratios = calculate_all_ratios(stmt)
        ratings = {
            "capital": rate_capital(ratios),
            "asset_quality": rate_asset_quality(ratios),
            "management": rate_management(ratios),
            "earnings": rate_earnings(ratios),
            "liquidity": rate_liquidity(ratios),
        }
        ratings["composite"] = get_composite_rating(
            ratings["capital"], ratings["asset_quality"],
            ratings["management"], ratings["earnings"], ratings["liquidity"]
        )
        generate_analysis_paragraphs(stmt, ratios, ratings)
        # Statement dict should not have been modified
        assert set(stmt.keys()) == original_keys


# ---------------------------------------------------------------------------
# run_full_analysis convenience function
# ---------------------------------------------------------------------------

class TestRunFullAnalysis:
    def test_returns_complete_result(self):
        stmt = _make_statement()
        result = run_full_analysis(stmt)
        assert "ratios" in result
        assert "ratings" in result
        assert "analysis" in result
        assert "composite" in result["ratings"]
        assert "composite" in result["analysis"]

    def test_with_previous_period(self):
        stmt = _make_statement(total_assets=1_200_000)
        prev = _make_statement(total_assets=800_000)
        result = run_full_analysis(stmt, prev_statement=prev)
        avg_assets = (1_200_000 + 800_000) / 2
        expected_roaa = 10_000 / avg_assets
        assert abs(result["ratios"]["roaa"] - expected_roaa) < 1e-9
