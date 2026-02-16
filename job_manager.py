import uuid
import json
import logging
import traceback
from datetime import datetime

from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.sql import func
from database import Base, SessionLocal

logger = logging.getLogger(__name__)


# ===== Job DB Model =====

class JobDB(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, index=True)
    status = Column(String, nullable=False, default="processing")
    step = Column(String)
    file_path = Column(String)
    filename = Column(String)
    result_json = Column(Text)
    error = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


# ===== Public API =====

def create_job(file_path: str, filename: str) -> str:
    job_id = str(uuid.uuid4())
    db = SessionLocal()
    try:
        job = JobDB(
            id=job_id,
            status="processing",
            step="Initializing...",
            file_path=file_path,
            filename=filename,
        )
        db.add(job)
        db.commit()
    finally:
        db.close()
    return job_id


def get_job(job_id: str) -> dict | None:
    db = SessionLocal()
    try:
        job = db.query(JobDB).filter(JobDB.id == job_id).first()
        if not job:
            return None

        result = None
        if job.result_json:
            try:
                result = json.loads(job.result_json)
            except json.JSONDecodeError:
                result = None

        return {
            "id": job.id,
            "status": job.status,
            "step": job.step,
            "result": result,
            "error": job.error,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "updated_at": job.updated_at.isoformat() if job.updated_at else None,
        }
    finally:
        db.close()


def update_job(job_id: str, status: str, step: str = None, result=None, error=None):
    db = SessionLocal()
    try:
        job = db.query(JobDB).filter(JobDB.id == job_id).first()
        if not job:
            return
        job.status = status
        if step:
            job.step = step
        if result is not None:
            job.result_json = _serialize_result(result)
        if error:
            job.error = error
        db.commit()
    finally:
        db.close()


def _serialize_result(result: dict) -> str:
    """Serialize result dict to JSON, handling datetime and other types."""
    def default_serializer(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return str(obj)
    return json.dumps(result, default=default_serializer)


# ===== Background processing =====

def process_job_async(job_id: str, file_path: str):
    from llm_service import extract_bank_data_from_file
    from camels_calculator import (
        calculate_all_ratios, rate_capital, rate_asset_quality,
        rate_management, rate_earnings, rate_liquidity,
        get_composite_rating, generate_analysis_paragraphs
    )
    from models import BankDB

    FIELD_MAP = [
        "cash_reserves_requirements", "due_from_banks", "investment_securities",
        "gross_loans", "loan_loss_provisions", "foreclosed_assets",
        "investment_in_subs_affiliates", "other_assets", "fixed_assets",
        "deposits", "short_term_borrowings", "long_term_debt",
        "interbank_liabilities", "other_liabilities", "total_liabilities",
        "paid_in_capital", "reserves", "retained_earnings", "net_profit", "total_equity",
        "interest_income", "interest_expenses", "net_interest_income",
        "fees_commissions", "net_sales", "dividends", "fvtpl_changes",
        "securitization_gains", "provisions_no_longer_required",
        "share_profit_associates", "other_revenues", "gain_acquisition_subsidiaries",
        "non_interest_income_commissions", "net_income_investment", "other_net_income",
        "wages_salaries", "other_opex", "intangible_amortization", "fixed_asset_depreciation",
        "operating_expenses", "operating_income", "operating_profit",
        "provision_expenses", "provisions_formed", "impairment_financial_assets", "fx_exchange",
        "non_operating_profit_loss", "income_tax", "net_income",
        "car_regulatory", "car_bank_reported", "npls_mn", "llr_mn",
        "fx_rate_period_end", "fx_rate_period_avg",
    ]

    db = None
    try:
        # Step 1: Extract
        update_job(job_id, "processing", step="Extracting data from document...")
        extracted_data = extract_bank_data_from_file(file_path)

        # Step 2: Create BankDB object
        update_job(job_id, "processing", step="Preparing data...")
        db = SessionLocal()

        kwargs = {
            "bank_name": extracted_data.get("name", "Unknown"),
            "country": extracted_data.get("country", "Unknown"),
            "fiscal_year": extracted_data.get("fiscal_year"),
            "currency": extracted_data.get("currency", "XOF"),
            "file_urls": file_path,
            "total_assets": extracted_data.get("total_assets", 0),
        }
        for field in FIELD_MAP:
            kwargs[field] = extracted_data.get(field)

        bank = BankDB(**kwargs)

        # Step 3: Calculate ratios
        update_job(job_id, "processing", step="Calculating CAMELS ratios...")
        bank = calculate_all_ratios(bank)

        # Step 4: Save to DB
        update_job(job_id, "processing", step="Saving to database...")
        db.add(bank)
        db.commit()
        db.refresh(bank)

        # Step 5: Generate ratings
        update_job(job_id, "processing", step="Generating CAMELS ratings and analysis...")
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

        # Step 6: Generate analysis paragraphs
        paragraphs = generate_analysis_paragraphs(bank, ratings)
        bank.analysis_complete = True
        db.commit()

        bank_dict = {k: v for k, v in bank.__dict__.items() if not k.startswith('_')}

        result = {
            "message": "Analysis complete!",
            "file": extracted_data.get("name", "Document"),
            "bank": bank_dict,
            "camels_rating": composite,
            "detailed_ratings": ratings,
            "analysis": paragraphs,
            "key_metrics": {
                "total_assets": bank.total_assets,
                "total_equity": bank.total_equity,
                "net_income": bank.net_income,
                "car": bank.car_regulatory,
                "equity_assets": bank.equity_assets,
                "debt_assets": bank.debt_assets,
                "npl_ratio": bank.npl_ratio,
                "coverage_ratio": bank.coverage_ratio,
                "cost_of_risk_avg_assets": bank.cost_of_risk_avg_assets,
                "cost_to_income": bank.cost_to_income,
                "roaa": bank.roaa,
                "roae": bank.roae,
                "liquid_assets_total_assets": bank.liquid_assets_total_assets,
                "loans_deposits": bank.gross_loans_deposits,
            }
        }

        update_job(job_id, "completed", step="Done!", result=result)
        logger.info(f"Job {job_id} completed successfully for {bank.bank_name}")

    except Exception as e:
        logger.error(f"Job {job_id} failed: {str(e)}")
        logger.error(traceback.format_exc())
        update_job(job_id, "failed", step="Failed", error=str(e))
    finally:
        if db is not None:
            db.close()
