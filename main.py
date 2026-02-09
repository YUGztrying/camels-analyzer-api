from fastapi import FastAPI, Depends, UploadFile, File, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
from models import BankDB
import os
import shutil
from datetime import datetime
from llm_service import extract_bank_data_from_file
from camels_calculator import (
    calculate_all_ratios, rate_capital, rate_asset_quality,
    rate_management, rate_earnings, rate_liquidity,
    get_composite_rating, generate_analysis_paragraphs
)
from fastapi.middleware.cors import CORSMiddleware
from job_manager import create_job, get_job, process_job_async
import threading

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ===== Pydantic models =====

class Bank(BaseModel):
    name: str
    country: str
    total_assets: float
    currency: str = "XOF"


class BankResponse(Bank):
    id: int

    class Config:
        from_attributes = True


# ===== Routes =====

@app.get("/")
def home():
    return {"message": "CAMELS Analyzer API"}


@app.post("/banks", response_model=BankResponse)
def create_bank(bank: Bank, db: Session = Depends(get_db)):
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
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_filename = f"{timestamp}_{file.filename}"
    file_path = f"{UPLOAD_FOLDER}/{unique_filename}"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {
        "message": "File uploaded",
        "filename": file.filename,
        "saved_as": unique_filename,
        "file_url": f"/uploads/{unique_filename}"
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
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{file.filename}"
    file_path = os.path.join(UPLOAD_FOLDER, filename)

    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

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
