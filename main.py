import os
import logging
import threading
from datetime import datetime

# Configure logging before other imports
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

from fastapi import FastAPI, Depends, UploadFile, File, HTTPException
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

# ===== Config =====
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".xlsx", ".xls"}

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ===== App =====
app = FastAPI(title="CAMELS Analyzer API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in CORS_ORIGINS],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


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
    safe_name = file.filename.replace("/", "_").replace("\\", "_")
    filename = f"{timestamp}_{safe_name}"
    file_path = os.path.join(UPLOAD_FOLDER, filename)

    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > MAX_UPLOAD_SIZE_MB:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({size_mb:.1f} MB). Maximum is {MAX_UPLOAD_SIZE_MB} MB"
        )

    with open(file_path, "wb") as buffer:
        buffer.write(content)

    return file_path, filename


# ===== Pydantic models =====

class BankCreate(BaseModel):
    name: str
    country: str
    total_assets: float
    currency: str = "XOF"


class BankResponse(BankCreate):
    id: int

    class Config:
        from_attributes = True


# ===== Routes =====

@app.get("/")
def home():
    return {"message": "CAMELS Analyzer API", "version": "2.0.0"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/banks", response_model=BankResponse)
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
    return db_bank


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
        "file_url": f"/uploads/{filename}"
    }


@app.get("/files")
def list_files():
    if not os.path.exists(UPLOAD_FOLDER):
        return {"files": [], "total": 0}
    files = os.listdir(UPLOAD_FOLDER)
    return {"total": len(files), "files": files}


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
async def upload_and_analyze(file: UploadFile = File(...)):
    _validate_upload(file)
    file_path, filename = await _save_upload(file)

    job_id = create_job(file_path, filename)

    thread = threading.Thread(target=process_job_async, args=(job_id, file_path))
    thread.daemon = True
    thread.start()

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
