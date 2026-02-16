"""
API integration tests for main.py — uses FastAPI's TestClient with an
in-memory SQLite database (no PostgreSQL needed for tests).
"""
import os
import io
import pytest
from unittest.mock import patch, MagicMock

# Use SQLite for tests
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test-key"
os.environ["ENABLE_DOCS"] = "true"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, get_db
from main import app, _upload_limiter

# Override DB with SQLite
TEST_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    """Create tables before each test, drop after."""
    from models import BankDB  # noqa
    from job_manager import JobDB  # noqa
    Base.metadata.create_all(bind=engine)
    # Reset rate limiter between tests
    _upload_limiter._requests.clear()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    return TestClient(app)


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

    def test_list_banks_empty(self, client):
        resp = client.get("/banks")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_get_bank_not_found(self, client):
        resp = client.get("/banks/9999")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Bank CRUD
# ---------------------------------------------------------------------------

class TestBankCRUD:
    def test_create_bank(self, client):
        resp = client.post("/banks", json={
            "name": "Test Bank",
            "country": "Senegal",
            "total_assets": 1000000.0,
            "currency": "XOF"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Test Bank"

    def test_list_banks_after_create(self, client):
        client.post("/banks", json={
            "name": "Bank A",
            "country": "Mali",
            "total_assets": 500000.0,
        })
        resp = client.get("/banks")
        assert resp.json()["total"] == 1

    def test_get_bank_success(self, client):
        create_resp = client.post("/banks", json={
            "name": "Bank B",
            "country": "Ivory Coast",
            "total_assets": 750000.0,
        })
        bank_id = create_resp.json()["id"]
        resp = client.get(f"/banks/{bank_id}")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# File upload validation
# ---------------------------------------------------------------------------

class TestUploadValidation:
    def test_reject_unsupported_extension(self, client):
        file_content = b"not a real file"
        resp = client.post("/upload", files={
            "file": ("test.exe", io.BytesIO(file_content), "application/octet-stream")
        })
        assert resp.status_code == 400
        assert "not allowed" in resp.json()["detail"]

    def test_reject_no_filename(self, client):
        file_content = b"test"
        resp = client.post("/upload", files={
            "file": ("", io.BytesIO(file_content), "application/octet-stream")
        })
        # Empty filename should be rejected (400) or at least not succeed (not 200)
        assert resp.status_code != 200

    def test_accept_pdf(self, client):
        file_content = b"%PDF-1.4 fake pdf content"
        resp = client.post("/upload", files={
            "file": ("report.pdf", io.BytesIO(file_content), "application/pdf")
        })
        assert resp.status_code == 200
        assert resp.json()["message"] == "File uploaded"

    def test_accept_xlsx(self, client):
        file_content = b"PK\x03\x04 fake xlsx"
        resp = client.post("/upload", files={
            "file": ("data.xlsx", io.BytesIO(file_content), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        })
        assert resp.status_code == 200

    def test_accept_png(self, client):
        file_content = b"\x89PNG fake image"
        resp = client.post("/upload", files={
            "file": ("scan.png", io.BytesIO(file_content), "image/png")
        })
        assert resp.status_code == 200

    def test_reject_too_large(self, client):
        with patch('main.MAX_UPLOAD_SIZE_MB', 0):
            file_content = b"x" * 100
            resp = client.post("/upload", files={
                "file": ("big.pdf", io.BytesIO(file_content), "application/pdf")
            })
            assert resp.status_code == 413


# ---------------------------------------------------------------------------
# Upload-and-analyze (job creation)
# ---------------------------------------------------------------------------

class TestUploadAndAnalyze:
    def test_creates_job(self, client):
        with patch('main._job_executor') as mock_executor:
            file_content = b"%PDF-1.4 test content"
            resp = client.post("/upload-and-analyze", files={
                "file": ("report.pdf", io.BytesIO(file_content), "application/pdf")
            })
            assert resp.status_code == 200
            data = resp.json()
            assert "job_id" in data
            assert data["status"] == "processing"
            # Verify the executor was called
            mock_executor.submit.assert_called_once()

    def test_job_status_not_found(self, client):
        resp = client.get("/job/nonexistent-id")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------

class TestRateLimiting:
    def test_rate_limit_upload(self, client):
        """Hit the upload endpoint many times rapidly to test rate limiting."""
        file_content = b"%PDF-1.4 test"
        responses = []
        with patch('main._job_executor'):
            for _ in range(25):
                resp = client.post("/upload-and-analyze", files={
                    "file": ("report.pdf", io.BytesIO(file_content), "application/pdf")
                })
                responses.append(resp.status_code)

        # At least some should be rate-limited (429)
        assert 429 in responses, "Rate limiter should reject some requests"

    def test_rate_limiter_allows_within_limit(self):
        """Test RateLimiter class directly."""
        from main import RateLimiter
        limiter = RateLimiter(max_requests=3, window_seconds=60)
        assert limiter.check("test-ip") is True
        assert limiter.check("test-ip") is True
        assert limiter.check("test-ip") is True
        assert limiter.check("test-ip") is False  # 4th request blocked

    def test_rate_limiter_different_keys(self):
        from main import RateLimiter
        limiter = RateLimiter(max_requests=1, window_seconds=60)
        assert limiter.check("ip-1") is True
        assert limiter.check("ip-2") is True  # Different key


# ---------------------------------------------------------------------------
# Calculate & rating routes
# ---------------------------------------------------------------------------

class TestCalculateRoutes:
    def test_calculate_ratios(self, client):
        create_resp = client.post("/banks", json={
            "name": "Calc Bank",
            "country": "Senegal",
            "total_assets": 1000000.0,
        })
        bank_id = create_resp.json()["id"]

        resp = client.get(f"/banks/{bank_id}/calculate")
        assert resp.status_code == 200
        assert "ratios" in resp.json()

    def test_calculate_not_found(self, client):
        resp = client.get("/banks/9999/calculate")
        assert resp.status_code == 404

    def test_rating_route(self, client):
        create_resp = client.post("/banks", json={
            "name": "Rate Bank",
            "country": "Mali",
            "total_assets": 1000000.0,
        })
        bank_id = create_resp.json()["id"]

        resp = client.get(f"/banks/{bank_id}/rating")
        assert resp.status_code == 200
        data = resp.json()
        assert "camels_ratings" in data
        assert "composite_rating" in data
        assert "analysis" in data

    def test_rating_not_found(self, client):
        resp = client.get("/banks/9999/rating")
        assert resp.status_code == 404
