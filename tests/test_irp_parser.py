"""
Tests for irp_parser.py — deterministic IRP Report Excel parser.

We build in-memory openpyxl workbooks to simulate the exact layout
described in the spec (no real files needed).
"""

import os
import tempfile
import pytest
from datetime import date

import openpyxl

from irp_parser import is_irp_report, parse_irp_excel, _parse_period_date


# ---------------------------------------------------------------------------
# Helpers — build synthetic IRP workbooks
# ---------------------------------------------------------------------------

def _make_irp_wb(
    title="IRP REPORT - MICROFINANCE FORMAT",
    company="Test MFI",
    periods=("Dec 2022", "Dec 2023"),
    assets_rows=None,
    liab_rows=None,
    income_rows=None,
) -> openpyxl.Workbook:
    """
    Build a minimal IRP Report workbook in the exact layout the spreading
    app exports.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "IRP Report"

    # Row 1: title
    ws.append([title])
    # Row 2: company
    ws.append([f"Company: {company}"])
    # Row 3: generated
    ws.append(["Generated: 2/18/2026, 10:00:00 AM"])
    # Row 4: blank
    ws.append([None])
    # Row 5: "REPORTING PERIODS:"
    ws.append(["REPORTING PERIODS:"])
    # Row 6: period headers
    ws.append([""] + list(periods))
    # Row 7: blank
    ws.append([None])

    def _write_section(header, rows):
        ws.append([header])
        ws.append(["Description"] + list(periods))
        for label, *values in rows:
            ws.append([label] + list(values))
        ws.append([None])

    default_assets = [
        ("Cash & Due from Banks (Non Interest Earning)", 50_000, 55_000),
        ("Total Securities",                             120_000, 130_000),
        ("Gross Loans",                                  500_000, 550_000),
        ("Less: Allowance for Loan Loss Reserve",         25_000,  28_000),   # stored + → negated
        ("Interest Bearing Deposits",                     30_000,  32_000),
        ("Net Fixed Assets",                              20_000,  22_000),
        ("Investments in Subsidiaries/Affiliates",         5_000,   5_500),
        ("Total Other Assets",                            15_000,  16_000),
        ("Total Assets",                                 750_000, 820_000),
    ]
    default_liab = [
        ("Total Deposits",               550_000, 600_000),
        ("Total Short Term Loans",        40_000,  45_000),
        ("Total Other Current Liabilities", 10_000, 11_000),
        ("Total Non-Current Liabilities",  80_000,  85_000),
        ("Total Liabilities",            680_000, 741_000),
        ("Common Shares",                 20_000,  20_000),
        ("Paid-in Capital",               10_000,  10_000),
        ("Retained Earnings",             25_000,  30_000),
        ("Reserves",                      15_000,  19_000),
        ("TOTAL EQUITY",                  70_000,  79_000),
    ]
    default_income = [
        ("Total Interest Income",                          60_000,  65_000),
        ("Total Interest Expenses",                        18_000,  20_000),
        ("Net Interest Margin",                            42_000,  45_000),
        ("Total Fee Income",                               10_000,  11_000),
        ("Total Investment Income",                         3_000,   3_200),
        ("Total Other Income",                              2_000,   2_100),
        ("Total Operating Income",                         57_000,  61_300),
        ("Personnel Expenses",                             14_000,  15_000),
        ("Sales, General & Administrative Expenses",        8_000,   8_500),
        ("Depreciation & Amortization Expense",             2_000,   2_200),
        ("Total Operating Expenses",                       24_000,  25_700),
        ("Operating Profit before Provision Expenses",     33_000,  35_600),
        ("Net Provision Expenses on Loan Portfolio",        5_000,   5_500),
        ("Other Non-Operating Income & (Expenses)",           500,     400),
        ("Income Taxes",                                    8_000,   8_500),
        ("Net Income",                                     20_500,  22_000),
    ]

    _write_section("=== ASSETS ===",            assets_rows  or default_assets)
    _write_section("=== LIABILITIES & EQUITY ===", liab_rows or default_liab)
    _write_section("=== INCOME STATEMENT ===",   income_rows  or default_income)

    return wb


def _save_tmp(wb) -> str:
    fd, path = tempfile.mkstemp(suffix=".xlsx")
    os.close(fd)
    wb.save(path)
    return path


# ---------------------------------------------------------------------------
# _parse_period_date
# ---------------------------------------------------------------------------

class TestParsePeriodDate:
    def test_dec_2023(self):
        d = _parse_period_date("Dec 2023")
        assert d == date(2023, 12, 31)

    def test_jan_2022(self):
        d = _parse_period_date("Jan 2022")
        assert d == date(2022, 1, 31)

    def test_feb_leap(self):
        d = _parse_period_date("Feb 2024")    # 2024 is a leap year
        assert d == date(2024, 2, 29)

    def test_invalid(self):
        assert _parse_period_date("Description") is None
        assert _parse_period_date("") is None
        assert _parse_period_date("2023") is None


# ---------------------------------------------------------------------------
# is_irp_report
# ---------------------------------------------------------------------------

class TestIsIrpReport:
    def test_valid_irp(self):
        wb = _make_irp_wb()
        path = _save_tmp(wb)
        try:
            assert is_irp_report(path) is True
        finally:
            os.unlink(path)

    def test_non_irp_excel(self):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Sheet1"
        ws.append(["RANDOM DATA"])
        path = _save_tmp(wb)
        try:
            assert is_irp_report(path) is False
        finally:
            os.unlink(path)

    def test_non_excel_file(self):
        fd, path = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)
        try:
            assert is_irp_report(path) is False
        finally:
            os.unlink(path)

    def test_bank_format_detected(self):
        wb = _make_irp_wb(title="IRP REPORT - BANQUE FORMAT")
        path = _save_tmp(wb)
        try:
            assert is_irp_report(path) is True
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# parse_irp_excel — basic extraction
# ---------------------------------------------------------------------------

class TestParseIrpExcel:
    def setup_method(self):
        wb = _make_irp_wb(company="Banque Test", periods=("Dec 2022", "Dec 2023"))
        self.path = _save_tmp(wb)

    def teardown_method(self):
        os.unlink(self.path)

    def test_returns_two_periods(self):
        results = parse_irp_excel(self.path)
        assert len(results) == 2

    def test_company_name(self):
        results = parse_irp_excel(self.path)
        assert results[0]["name"] == "Banque Test"

    def test_sorted_oldest_first(self):
        results = parse_irp_excel(self.path)
        assert results[0]["period_end_date"] < results[1]["period_end_date"]

    def test_period_dates(self):
        results = parse_irp_excel(self.path)
        assert results[0]["period_end_date"] == date(2022, 12, 31)
        assert results[1]["period_end_date"] == date(2023, 12, 31)

    def test_fiscal_years(self):
        results = parse_irp_excel(self.path)
        assert results[0]["fiscal_year"] == "2022"
        assert results[1]["fiscal_year"] == "2023"

    def test_institution_type_mfi(self):
        results = parse_irp_excel(self.path)
        assert results[0]["institution_type"] == "mfi"

    def test_total_assets(self):
        results = parse_irp_excel(self.path)
        assert results[0]["total_assets"] == 750_000
        assert results[1]["total_assets"] == 820_000

    def test_gross_loans(self):
        results = parse_irp_excel(self.path)
        assert results[0]["gross_loans"] == 500_000

    def test_loan_loss_provisions_negated(self):
        # IFC stores "Less: Allowance" as positive; we must negate it
        results = parse_irp_excel(self.path)
        assert results[0]["loan_loss_provisions"] == -25_000
        assert results[1]["loan_loss_provisions"] == -28_000

    def test_deposits(self):
        results = parse_irp_excel(self.path)
        assert results[0]["deposits"] == 550_000

    def test_total_equity(self):
        results = parse_irp_excel(self.path)
        assert results[0]["total_equity"] == 70_000
        assert results[1]["total_equity"] == 79_000

    def test_paid_in_capital_summed(self):
        # Common Shares (20_000) + Paid-in Capital (10_000) = 30_000
        results = parse_irp_excel(self.path)
        assert results[0]["paid_in_capital"] == 30_000

    def test_interest_income(self):
        results = parse_irp_excel(self.path)
        assert results[0]["interest_income"] == 60_000

    def test_interest_expenses_positive(self):
        results = parse_irp_excel(self.path)
        assert results[0]["interest_expenses"] == 18_000    # already positive in IFC

    def test_net_interest_income(self):
        # "Net Interest Margin" in IFC = NII
        results = parse_irp_excel(self.path)
        assert results[0]["net_interest_income"] == 42_000

    def test_operating_income(self):
        results = parse_irp_excel(self.path)
        assert results[0]["operating_income"] == 57_000

    def test_operating_expenses(self):
        results = parse_irp_excel(self.path)
        assert results[0]["operating_expenses"] == 24_000

    def test_provision_expenses_positive(self):
        results = parse_irp_excel(self.path)
        assert results[0]["provision_expenses"] == 5_000

    def test_net_income(self):
        results = parse_irp_excel(self.path)
        assert results[0]["net_income"] == 20_500
        assert results[1]["net_income"] == 22_000

    def test_net_profit_mirrored(self):
        # net_profit should be set equal to net_income
        results = parse_irp_excel(self.path)
        assert results[0]["net_profit"] == results[0]["net_income"]

    def test_wages_salaries(self):
        results = parse_irp_excel(self.path)
        assert results[0]["wages_salaries"] == 14_000

    def test_investment_securities(self):
        results = parse_irp_excel(self.path)
        assert results[0]["investment_securities"] == 120_000   # "Total Securities" wins


class TestParseIrpExcelThreePeriods:
    def setup_method(self):
        wb = _make_irp_wb(periods=("Dec 2022", "Dec 2023", "Dec 2024"))
        # Patch the default rows to have 3 value columns
        # We re-create with correct data
        wb = _make_irp_wb(
            periods=("Dec 2022", "Dec 2023", "Dec 2024"),
            assets_rows=[
                ("Cash & Due from Banks (Non Interest Earning)", 50_000, 55_000, 60_000),
                ("Total Securities",                             120_000, 130_000, 140_000),
                ("Gross Loans",                                  500_000, 550_000, 600_000),
                ("Less: Allowance for Loan Loss Reserve",         25_000,  28_000,  30_000),
                ("Net Fixed Assets",                              20_000,  22_000,  24_000),
                ("Total Other Assets",                            15_000,  16_000,  17_000),
                ("Total Assets",                                 750_000, 820_000, 890_000),
            ],
            liab_rows=[
                ("Total Deposits",               550_000, 600_000, 650_000),
                ("Total Short Term Loans",        40_000,  45_000,  50_000),
                ("Total Non-Current Liabilities",  80_000,  85_000,  90_000),
                ("Total Liabilities",            680_000, 741_000, 802_000),
                ("Common Shares",                 20_000,  20_000,  20_000),
                ("Paid-in Capital",               10_000,  10_000,  10_000),
                ("Retained Earnings",             25_000,  30_000,  35_000),
                ("Reserves",                      15_000,  19_000,  23_000),
                ("TOTAL EQUITY",                  70_000,  79_000,  88_000),
            ],
            income_rows=[
                ("Total Interest Income",          60_000,  65_000,  70_000),
                ("Total Interest Expenses",         18_000,  20_000,  22_000),
                ("Net Interest Margin",             42_000,  45_000,  48_000),
                ("Total Fee Income",                10_000,  11_000,  12_000),
                ("Total Operating Income",          57_000,  61_300,  66_000),
                ("Personnel Expenses",              14_000,  15_000,  16_000),
                ("Total Operating Expenses",        24_000,  25_700,  27_500),
                ("Operating Profit before Provision Expenses", 33_000, 35_600, 38_500),
                ("Net Provision Expenses on Loan Portfolio",    5_000,  5_500,  6_000),
                ("Income Taxes",                     8_000,  8_500,  9_000),
                ("Net Income",                      20_500, 22_000,  23_500),
            ],
        )
        self.path = _save_tmp(wb)

    def teardown_method(self):
        os.unlink(self.path)

    def test_three_periods_returned(self):
        results = parse_irp_excel(self.path)
        assert len(results) == 3

    def test_period_labels(self):
        results = parse_irp_excel(self.path)
        assert results[0]["period_label"] == "Dec 2022"
        assert results[1]["period_label"] == "Dec 2023"
        assert results[2]["period_label"] == "Dec 2024"

    def test_all_total_assets(self):
        results = parse_irp_excel(self.path)
        assert results[0]["total_assets"] == 750_000
        assert results[1]["total_assets"] == 820_000
        assert results[2]["total_assets"] == 890_000


class TestBankFormat:
    def setup_method(self):
        wb = _make_irp_wb(
            title="IRP REPORT - BANQUE FORMAT",
            company="Bank Test",
            periods=("Dec 2023",),
            assets_rows=[
                ("Cash & Due from Banks",                           80_000),
                ("Total Securities",                               200_000),
                ("Gross Loans",                                    600_000),
                ("Less: Allowance for Loan Loss Reserve",           30_000),
                ("Net Fixed Assets",                                25_000),
                ("Total Assets",                                 1_000_000),
            ],
            liab_rows=[
                ("Total Deposits",                                 700_000),
                ("Deposits from Banks",                             50_000),
                ("Total Short Term Loans",                          80_000),
                ("Total Non-Current Liabilities",                  100_000),
                ("Total Liabilities",                              890_000),
                ("Common Shares",                                   50_000),
                ("Paid-in Capital",                                 20_000),
                ("Retained Earnings",                               30_000),
                ("Reserves",                                        10_000),
                ("TOTAL EQUITY",                                   110_000),
            ],
            income_rows=[
                ("Total Interest Income",                          120_000),
                ("Total Interest Expenses",                         40_000),
                ("Net Interest Margin",                             80_000),
                ("Net Fees & Commissions",                          25_000),   # bank-specific
                ("Net Gains/Losses from Trading (Securities/FX/Derivatives)", 5_000),
                ("Total Operating Income",                         115_000),
                ("Personnel Expenses",                              30_000),
                ("Total Operating Expenses",                        55_000),
                ("Operating Profit before Provision Expenses",      60_000),
                ("Net Provision Expenses on Loan Portfolio",        10_000),
                ("Income Taxes",                                    12_000),
                ("Net Income",                                      38_000),
            ],
        )
        self.path = _save_tmp(wb)

    def teardown_method(self):
        os.unlink(self.path)

    def test_institution_type_bank(self):
        results = parse_irp_excel(self.path)
        assert results[0]["institution_type"] == "bank"

    def test_bank_fee_label_wins(self):
        # "Net Fees & Commissions" (bank extra) should be used for fees_commissions
        results = parse_irp_excel(self.path)
        assert results[0]["fees_commissions"] == 25_000

    def test_fvtpl_changes(self):
        results = parse_irp_excel(self.path)
        assert results[0]["fvtpl_changes"] == 5_000

    def test_interbank_liabilities(self):
        results = parse_irp_excel(self.path)
        assert results[0]["interbank_liabilities"] == 50_000

    def test_paid_in_capital_summed(self):
        results = parse_irp_excel(self.path)
        assert results[0]["paid_in_capital"] == 70_000   # 50_000 + 20_000


class TestEdgeCases:
    def test_missing_optional_fields_are_absent(self):
        """Fields not in the Excel should simply not appear in the result dict."""
        wb = _make_irp_wb(
            assets_rows=[
                ("Total Assets", 500_000, 600_000),   # minimal — no loans etc.
            ],
            liab_rows=[
                ("Total Liabilities", 400_000, 480_000),
                ("TOTAL EQUITY",       100_000, 120_000),
            ],
            income_rows=[
                ("Net Interest Margin",  30_000, 32_000),
                ("Net Income",           10_000, 11_000),
            ],
        )
        path = _save_tmp(wb)
        try:
            results = parse_irp_excel(path)
            r = results[0]
            assert r["total_assets"] == 500_000
            assert "gross_loans" not in r or r.get("gross_loans") is None
        finally:
            os.unlink(path)

    def test_negative_interest_expenses_abs(self):
        """If IFC stores interest_expenses as negative, we take abs()."""
        wb = _make_irp_wb(
            income_rows=[
                ("Total Interest Income",   60_000, 65_000),
                ("Total Interest Expenses", -18_000, -20_000),   # negative in sheet
                ("Net Interest Margin",      42_000,  45_000),
                ("Net Income",               20_000,  22_000),
            ],
        )
        path = _save_tmp(wb)
        try:
            results = parse_irp_excel(path)
            assert results[0]["interest_expenses"] == 18_000
        finally:
            os.unlink(path)
