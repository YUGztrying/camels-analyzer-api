import os
import logging
import time
import threading
from collections import defaultdict
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# Configure logging before other imports
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

from fastapi import FastAPI, Depends, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import BankDB
from camels_calculator import (
    calculate_all_ratios, rate_capital, rate_asset_quality,
    rate_management, rate_earnings, rate_liquidity,
    get_composite_rating, generate_analysis_paragraphs
)
from job_manager import create_job, get_job, process_job_async

logger = logging.getLogger(__name__)
logger.info("Starting CAMELS Analyzer API...")

# ===== Config =====
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".xlsx", ".xls"}

CORS_ORIGINS = [o.strip().rstrip("/") for o in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",") if o.strip()]

# Disable docs in production (set ENABLE_DOCS=true to enable)
_enable_docs = os.getenv("ENABLE_DOCS", "false").lower() == "true"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

logger.info(f"CORS origins: {CORS_ORIGINS}")
logger.info(f"Upload folder: {UPLOAD_FOLDER}")
logger.info(f"Max upload size: {MAX_UPLOAD_SIZE_MB} MB")
logger.info(f"Docs enabled: {_enable_docs}")

# Thread pool to limit concurrent background jobs
_job_executor = ThreadPoolExecutor(max_workers=4)

# ===== Lifespan (runs init_db in background) =====

_db_ready = False

def _init_db_background():
    """Run init_db in a background thread so it doesn't block startup."""
    global _db_ready
    try:
        from init_db import init_database
        init_database()
        _db_ready = True
        logger.info("Background DB init complete.")
    except Exception as e:
        logger.error(f"Background DB init failed: {e}")

@asynccontextmanager
async def lifespan(app):
    """Start app immediately, init DB in background."""
    threading.Thread(target=_init_db_background, daemon=True).start()
    logger.info("Application startup complete (DB init running in background).")
    yield
    logger.info("Application shutting down.")


# ===== App =====
app = FastAPI(
    title="CAMELS Analyzer API",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs" if _enable_docs else None,
    redoc_url="/redoc" if _enable_docs else None,
    openapi_url="/openapi.json" if _enable_docs else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# ===== Rate Limiter =====

class RateLimiter:
    """Simple in-memory rate limiter per IP address."""

    def __init__(self, max_requests: int = 20, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str) -> bool:
        """Return True if request is allowed, False if rate-limited."""
        now = time.time()
        # Prune old entries
        self._requests[key] = [t for t in self._requests[key] if now - t < self.window]
        if len(self._requests[key]) >= self.max_requests:
            return False
        self._requests[key].append(now)
        return True


# 20 requests per minute for uploads (each costs API credits)
_upload_limiter = RateLimiter(max_requests=20, window_seconds=60)


# ===== Helpers =====

def _validate_upload(file: UploadFile) -> None:
    """Validate file extension and size."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{ext}' not allowed. Accepted: {', '.join(ALLOWED_EXTENSIONS)}"
        )


async def _save_upload(file: UploadFile) -> tuple[str, str]:
    """Save upload to disk, enforce size limit. Returns (file_path, filename)."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Sanitize filename: strip path separators and directory traversal
    raw_name = file.filename or "upload"
    safe_name = os.path.basename(raw_name).replace("..", "_").replace("\x00", "_")
    safe_name = safe_name.replace("/", "_").replace("\\", "_")
    filename = f"{timestamp}_{safe_name}"
    file_path = os.path.join(UPLOAD_FOLDER, filename)

    # Verify the resolved path is inside the upload folder (prevent traversal)
    real_upload = os.path.realpath(UPLOAD_FOLDER)
    real_path = os.path.realpath(file_path)
    if not real_path.startswith(real_upload):
        raise HTTPException(status_code=400, detail="Invalid filename")

    # Read in chunks to limit memory for oversized files
    max_bytes = MAX_UPLOAD_SIZE_MB * 1024 * 1024
    chunks = []
    total_read = 0
    while True:
        chunk = await file.read(1024 * 1024)  # 1MB chunks
        if not chunk:
            break
        total_read += len(chunk)
        if total_read > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum is {MAX_UPLOAD_SIZE_MB} MB"
            )
        chunks.append(chunk)

    with open(file_path, "wb") as buffer:
        for chunk in chunks:
            buffer.write(chunk)

    return file_path, filename


# ===== Pydantic models =====

class BankCreate(BaseModel):
    name: str
    country: str
    total_assets: float
    currency: str = "XOF"


class BankResponse(BaseModel):
    id: int
    name: str
    country: str
    total_assets: float
    currency: str = "XOF"


# ===== Routes =====

@app.get("/")
def home():
    return {"message": "CAMELS Analyzer API", "version": "2.0.0"}


@app.get("/health")
def health():
    """Lightweight health check — returns immediately so Railway marks us healthy."""
    return {"status": "ok", "database_ready": _db_ready}


@app.post("/banks")
def create_bank(bank: BankCreate, db: Session = Depends(get_db)):
    db_bank = BankDB(
        bank_name=bank.name,
        country=bank.country,
        total_assets=bank.total_assets,
        currency=bank.currency
    )
    db.add(db_bank)
    db.commit()
    db.refresh(db_bank)
    return {
        "id": db_bank.id,
        "name": db_bank.bank_name,
        "country": db_bank.country,
        "total_assets": db_bank.total_assets,
        "currency": db_bank.currency,
    }


@app.get("/banks")
def list_banks(db: Session = Depends(get_db)):
    banks = db.query(BankDB).all()
    return {"total": len(banks), "banks": banks}


@app.get("/banks/{bank_id}")
def get_bank(bank_id: int, db: Session = Depends(get_db)):
    bank = db.query(BankDB).filter(BankDB.id == bank_id).first()
    if not bank:
        raise HTTPException(status_code=404, detail="Bank not found")
    return bank


# ===== Upload routes =====

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    _validate_upload(file)
    file_path, filename = await _save_upload(file)
    return {
        "message": "File uploaded",
        "filename": file.filename,
        "saved_as": filename,
    }


@app.get("/files")
def list_files():
    if not os.path.exists(UPLOAD_FOLDER):
        return {"files": [], "total": 0}
    files = os.listdir(UPLOAD_FOLDER)
    return {"total": len(files)}


# ===== Calculate & Rating routes =====

@app.get("/banks/{bank_id}/calculate")
def calculate_ratios(bank_id: int, db: Session = Depends(get_db)):
    bank = db.query(BankDB).filter(BankDB.id == bank_id).first()
    if not bank:
        raise HTTPException(status_code=404, detail="Bank not found")

    bank = calculate_all_ratios(bank)
    db.commit()
    db.refresh(bank)

    return {
        "message": "Ratios calculated",
        "bank_id": bank.id,
        "bank_name": bank.bank_name,
        "ratios": {
            "capital": {"equity_assets": bank.equity_assets, "debt_assets": bank.debt_assets},
            "asset_quality": {"npl_ratio": bank.npl_ratio, "coverage_ratio": bank.coverage_ratio, "cost_of_risk_avg_assets": bank.cost_of_risk_avg_assets},
            "management": {"cost_to_income": bank.cost_to_income},
            "earnings": {"roaa": bank.roaa, "roae": bank.roae, "net_interest_income_avg_assets": bank.net_interest_income_avg_assets},
            "liquidity": {"liquid_assets_total_assets": bank.liquid_assets_total_assets, "gross_loans_deposits": bank.gross_loans_deposits},
        }
    }


@app.get("/banks/{bank_id}/rating")
def get_camels_rating(bank_id: int, db: Session = Depends(get_db)):
    bank = db.query(BankDB).filter(BankDB.id == bank_id).first()
    if not bank:
        raise HTTPException(status_code=404, detail="Bank not found")

    bank = calculate_all_ratios(bank)
    db.commit()

    ratings = {
        "capital": rate_capital(bank),
        "asset_quality": rate_asset_quality(bank),
        "management": rate_management(bank),
        "earnings": rate_earnings(bank),
        "liquidity": rate_liquidity(bank),
    }
    composite = get_composite_rating(
        ratings["capital"], ratings["asset_quality"],
        ratings["management"], ratings["earnings"], ratings["liquidity"]
    )
    ratings["composite"] = composite

    paragraphs = generate_analysis_paragraphs(bank, ratings)
    db.commit()

    return {
        "bank_id": bank.id,
        "bank_name": bank.bank_name,
        "fiscal_year": bank.fiscal_year,
        "country": bank.country,
        "camels_ratings": ratings,
        "composite_rating": composite,
        "analysis": paragraphs,
        "summary": {
            "total_assets": bank.total_assets,
            "total_equity": bank.total_equity,
            "net_income": bank.net_income,
            "car": bank.car_regulatory or bank.car_bank_reported,
            "roae": bank.roae,
            "npl_ratio": bank.npl_ratio
        }
    }


# ===== Async upload & analyze =====

@app.post("/upload-and-analyze")
async def upload_and_analyze(request: Request, file: UploadFile = File(...)):
    # Rate limiting per IP
    client_ip = request.client.host if request.client else "unknown"
    if not _upload_limiter.check(client_ip):
        raise HTTPException(status_code=429, detail="Too many requests. Please wait before uploading again.")

    _validate_upload(file)
    file_path, filename = await _save_upload(file)

    job_id = create_job(file_path, filename)

    # Use thread pool instead of unbounded thread creation
    _job_executor.submit(process_job_async, job_id, file_path)

    return {
        "job_id": job_id,
        "status": "processing",
        "message": "Analysis started. Poll GET /job/{job_id} for status."
    }


@app.get("/job/{job_id}")
async def get_job_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "job_id": job["id"],
        "status": job["status"],
        "step": job.get("step"),
        "result": job.get("result"),
        "error": job.get("error"),
        "created_at": job.get("created_at"),
        "updated_at": job.get("updated_at")
    }
