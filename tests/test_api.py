"""
API tests for main.py — mocks Supabase client to test endpoints
without a real database connection.
"""
import os
import pytest
from unittest.mock import patch, MagicMock

os.environ["SUPABASE_URL"] = "https://test.supabase.co"
os.environ["SUPABASE_SERVICE_KEY"] = "test-key"
os.environ["ENABLE_DOCS"] = "true"

from main import app


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    return TestClient(app)


def _mock_execute(data):
    """Create a mock Supabase execute() result."""
    result = MagicMock()
    result.data = data
    return result


def _mock_table(table_responses):
    """
    Create a mock Supabase client where .table(name) returns
    a chainable query builder that resolves to the given data.
    """
    mock_client = MagicMock()

    def table_side_effect(table_name):
        builder = MagicMock()
        data = table_responses.get(table_name, [])
        # Make all chained methods return the builder itself
        builder.select.return_value = builder
        builder.eq.return_value = builder
        builder.order.return_value = builder
        builder.upsert.return_value = builder
        builder.execute.return_value = _mock_execute(data)
        return builder

    mock_client.table.side_effect = table_side_effect
    return mock_client


# ---------------------------------------------------------------------------
# Health & basic routes
# ---------------------------------------------------------------------------

class TestHealthAndRoutes:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_root(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "CAMELS" in resp.json()["message"]
        assert resp.json()["version"] == "3.0.0"


# ---------------------------------------------------------------------------
# Companies
# ---------------------------------------------------------------------------

class TestCompanies:
    @patch("main.get_client")
    def test_list_companies(self, mock_get_client, client):
        companies = [
            {"id": "c1", "name": "Test Bank", "country": "Senegal", "entity_type": "bank", "created_at": "2024-01-01"},
        ]
        mock_get_client.return_value = _mock_table({"companies": companies})

        resp = client.get("/companies")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["companies"][0]["name"] == "Test Bank"

    @patch("main.get_client")
    def test_list_companies_empty(self, mock_get_client, client):
        mock_get_client.return_value = _mock_table({"companies": []})

        resp = client.get("/companies")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    @patch("main.get_client")
    def test_get_company(self, mock_get_client, client):
        companies = [{"id": "c1", "name": "Test Bank", "country": "Senegal"}]
        mock_get_client.return_value = _mock_table({"companies": companies})

        resp = client.get("/companies/c1")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Test Bank"

    @patch("main.get_client")
    def test_get_company_not_found(self, mock_get_client, client):
        mock_get_client.return_value = _mock_table({"companies": []})

        resp = client.get("/companies/nonexistent")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Financial Statements
# ---------------------------------------------------------------------------

class TestStatements:
    @patch("main.get_client")
    def test_list_statements(self, mock_get_client, client):
        stmts = [
            {"id": "s1", "company_id": "c1", "fiscal_year": "2023", "statement_type": "annual",
             "currency": "XOF", "total_assets": 1000000, "total_equity": 120000, "net_income": 10000,
             "created_at": "2024-01-01"},
        ]
        mock_get_client.return_value = _mock_table({"financial_statements": stmts})

        resp = client.get("/companies/c1/statements")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    @patch("main.get_client")
    def test_get_statement(self, mock_get_client, client):
        stmts = [{"id": "s1", "company_id": "c1", "fiscal_year": "2023", "total_assets": 1000000}]
        mock_get_client.return_value = _mock_table({"financial_statements": stmts})

        resp = client.get("/statements/s1")
        assert resp.status_code == 200
        assert resp.json()["fiscal_year"] == "2023"

    @patch("main.get_client")
    def test_get_statement_not_found(self, mock_get_client, client):
        mock_get_client.return_value = _mock_table({"financial_statements": []})

        resp = client.get("/statements/nonexistent")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# CAMELS Analysis
# ---------------------------------------------------------------------------

class TestAnalysis:
    @patch("main.get_client")
    def test_analyze_statement(self, mock_get_client, client):
        statement = {
            "id": "s1", "company_id": "c1", "user_id": "u1",
            "fiscal_year": "2023", "statement_type": "annual", "currency": "XOF",
            "total_assets": 1_000_000, "total_equity": 120_000,
            "gross_loans": 600_000, "deposits": 700_000,
            "npls_mn": 20_000, "loan_loss_provisions": -30_000,
            "net_income": 10_000, "net_interest_income": 50_000,
            "operating_expenses": 30_000, "operating_income": 64_000,
            "provision_expenses": 10_000, "income_tax": 5_000,
            "cash_reserves_requirements": 50_000, "due_from_banks": 30_000,
            "investment_securities": 100_000, "short_term_borrowings": 50_000,
            "long_term_debt": 80_000,
        }
        company = {"name": "Test Bank", "country": "Senegal"}

        mock_client = MagicMock()
        call_count = {"n": 0}

        def table_side_effect(table_name):
            builder = MagicMock()
            builder.select.return_value = builder
            builder.eq.return_value = builder
            builder.order.return_value = builder
            builder.upsert.return_value = builder

            if table_name == "financial_statements":
                builder.execute.return_value = _mock_execute([statement])
            elif table_name == "companies":
                builder.execute.return_value = _mock_execute([company])
            elif table_name == "camels_analyses":
                builder.execute.return_value = _mock_execute([])
            else:
                builder.execute.return_value = _mock_execute([])
            return builder

        mock_client.table.side_effect = table_side_effect
        mock_get_client.return_value = mock_client

        resp = client.post("/statements/s1/analyze")
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "Analysis complete"
        assert data["bank_name"] == "Test Bank"
        assert "ratios" in data
        assert "ratings" in data
        assert "analysis" in data
        assert "key_metrics" in data
        # Verify ratios were computed
        assert data["ratios"]["equity_assets"] is not None
        assert data["ratings"]["composite"]["composite_rating"] is not None

    @patch("main.get_client")
    def test_analyze_not_found(self, mock_get_client, client):
        mock_get_client.return_value = _mock_table({"financial_statements": []})

        resp = client.post("/statements/nonexistent/analyze")
        assert resp.status_code == 404

    @patch("main.get_client")
    def test_get_analysis(self, mock_get_client, client):
        analysis = {"id": "a1", "statement_id": "s1", "composite_rating": {"composite_rating": 2}}
        mock_get_client.return_value = _mock_table({"camels_analyses": [analysis]})

        resp = client.get("/statements/s1/analysis")
        assert resp.status_code == 200

    @patch("main.get_client")
    def test_get_analysis_not_found(self, mock_get_client, client):
        mock_get_client.return_value = _mock_table({"camels_analyses": []})

        resp = client.get("/statements/nonexistent/analysis")
        assert resp.status_code == 404

    @patch("main.get_client")
    def test_list_analyses(self, mock_get_client, client):
        analyses = [
            {"id": "a1", "statement_id": "s1", "company_id": "c1", "composite_rating": {}, "created_at": "2024-01-01"},
        ]
        mock_get_client.return_value = _mock_table({"camels_analyses": analyses})

        resp = client.get("/analyses")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1
