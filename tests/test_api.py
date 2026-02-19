"""
API endpoint tests for the CAMELS Analyzer — v4 (Spreading App integration).
Uses mocked Supabase and statement_reader to test the FastAPI endpoints.
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Mock data
# ---------------------------------------------------------------------------

MOCK_USER_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"

MOCK_COMPANIES = [
    {
        "user_id": MOCK_USER_ID,
        "company_name": "Banque Atlantique",
        "type_institution": "banque",
        "statement_count": 4,
        "last_updated": "2024-01-15T10:00:00Z",
    },
    {
        "user_id": MOCK_USER_ID,
        "company_name": "PAMECAS",
        "type_institution": "microfinance",
        "statement_count": 4,
        "last_updated": "2024-01-10T10:00:00Z",
    },
]

MOCK_PERIODS = ["2023-12-31", "2022-12-31"]

MOCK_EXTRACTED = {
    "bank_name": "Banque Atlantique",
    "name": "Banque Atlantique",
    "fiscal_year": "2023",
    "currency": "XOF",
    "type_institution": "banque",
    "total_assets": 1_000_000,
    "total_equity": 120_000,
    "total_liabilities": 880_000,
    "cash_reserves_requirements": 50_000,
    "due_from_banks": 30_000,
    "investment_securities": 100_000,
    "gross_loans": 600_000,
    "loan_loss_provisions": 30_000,
    "foreclosed_assets": 0,
    "npls_mn": 20_000,
    "deposits": 700_000,
    "short_term_borrowings": 50_000,
    "long_term_debt": 80_000,
    "interbank_liabilities": 30_000,
    "paid_in_capital": 60_000,
    "reserves": 40_000,
    "retained_earnings": 10_000,
    "net_profit": 10_000,
    "interest_income": 80_000,
    "interest_expenses": 30_000,
    "net_interest_income": 50_000,
    "operating_income": 64_000,
    "operating_expenses": 30_000,
    "cost_of_risk": 10_000,
    "provision_expenses": 10_000,
    "income_tax": 5_000,
    "net_income": 10_000,
    "fees_commissions": 8_000,
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestHealthAndRoutes:
    def test_root(self):
        r = client.get("/")
        assert r.status_code == 200
        assert r.json()["version"] == "4.0.0"

    def test_health(self):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


class TestCompanies:
    @patch("main.list_companies_for_user", return_value=MOCK_COMPANIES)
    def test_list_companies(self, mock_list):
        r = client.get(f"/companies?user_id={MOCK_USER_ID}")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 2
        assert data["companies"][0]["company_name"] == "Banque Atlantique"

    @patch("main.list_companies_for_user", return_value=[])
    def test_list_companies_empty(self, mock_list):
        r = client.get(f"/companies?user_id={MOCK_USER_ID}")
        assert r.status_code == 200
        assert r.json()["total"] == 0

    def test_list_companies_no_user(self):
        r = client.get("/companies")
        assert r.status_code == 400


class TestPeriods:
    @patch("main.list_periods_for_company", return_value=MOCK_PERIODS)
    def test_get_periods(self, mock_periods):
        r = client.get(f"/companies/Banque%20Atlantique/periods?user_id={MOCK_USER_ID}")
        assert r.status_code == 200
        data = r.json()
        assert "2023-12-31" in data["periods"]

    @patch("main.list_periods_for_company", return_value=[])
    def test_get_periods_not_found(self, mock_periods):
        r = client.get(f"/companies/Unknown/periods?user_id={MOCK_USER_ID}")
        assert r.status_code == 404


class TestAnalysis:
    @patch("main.get_client")
    @patch("main.extract_previous_period_data", return_value=None)
    @patch("main.extract_statement_data", return_value=MOCK_EXTRACTED)
    def test_analyze(self, mock_extract, mock_prev, mock_sb):
        mock_table = MagicMock()
        mock_sb.return_value.table.return_value = mock_table
        mock_table.upsert.return_value.execute.return_value = MagicMock(data=[{}])

        r = client.post(
            f"/analyze?company_name=Banque%20Atlantique&period=2023-12-31&user_id={MOCK_USER_ID}"
        )
        assert r.status_code == 200
        data = r.json()
        assert data["message"] == "Analysis complete"
        assert data["company_name"] == "Banque Atlantique"
        assert "ratios" in data
        assert "ratings" in data
        assert "analysis" in data
        assert "key_metrics" in data

    @patch("main.extract_statement_data", side_effect=ValueError("Not found"))
    def test_analyze_not_found(self, mock_extract):
        r = client.post(
            f"/analyze?company_name=NoSuchBank&period=2023-12-31&user_id={MOCK_USER_ID}"
        )
        assert r.status_code == 404

    @patch("main.get_client")
    def test_list_analyses(self, mock_sb):
        mock_result = MagicMock()
        mock_result.data = [
            {"id": "xxx", "company_name": "Test", "period": "2023-12-31",
             "composite_rating": {"composite_rating": 2}, "created_at": "2024-01-01"}
        ]
        mock_sb.return_value.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_result

        r = client.get(f"/analyses?user_id={MOCK_USER_ID}")
        assert r.status_code == 200
        assert r.json()["total"] == 1

    @patch("main.get_client")
    def test_get_analysis(self, mock_sb):
        mock_result = MagicMock()
        mock_result.data = [{"id": "xxx", "company_name": "Test", "period": "2023-12-31"}]
        mock_sb.return_value.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = mock_result

        r = client.get(f"/analyses/Test/2023-12-31?user_id={MOCK_USER_ID}")
        assert r.status_code == 200

    @patch("main.get_client")
    def test_get_analysis_not_found(self, mock_sb):
        mock_result = MagicMock()
        mock_result.data = []
        mock_sb.return_value.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = mock_result

        r = client.get(f"/analyses/Missing/2099-12-31?user_id={MOCK_USER_ID}")
        assert r.status_code == 404


class TestAnalysisDataIntegrity:
    """Verify the full analysis response has the correct structure."""

    @patch("main.get_client")
    @patch("main.extract_previous_period_data", return_value=None)
    @patch("main.extract_statement_data", return_value=MOCK_EXTRACTED)
    def test_full_response_structure(self, mock_extract, mock_prev, mock_sb):
        mock_table = MagicMock()
        mock_sb.return_value.table.return_value = mock_table
        mock_table.upsert.return_value.execute.return_value = MagicMock(data=[{}])

        r = client.post(
            f"/analyze?company_name=Banque%20Atlantique&period=2023-12-31&user_id={MOCK_USER_ID}"
        )
        data = r.json()

        # Top-level keys
        assert "ratios" in data
        assert "ratings" in data
        assert "analysis" in data
        assert "key_metrics" in data

        # Ratings structure
        for component in ("capital", "asset_quality", "management", "earnings", "liquidity"):
            assert component in data["ratings"]
            assert "rating" in data["ratings"][component]
            assert "status" in data["ratings"][component]
        assert "composite" in data["ratings"]

        # Analysis paragraphs
        for component in ("capital", "asset_quality", "management", "earnings", "liquidity", "composite"):
            assert component in data["analysis"]
            assert len(data["analysis"][component]) > 0

        # Key metrics
        km = data["key_metrics"]
        assert km["total_assets"] == 1_000_000
        assert km["total_equity"] == 120_000
