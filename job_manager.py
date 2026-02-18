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

# All BankDB fields that can be populated from either LLM extraction or IRP parser
_FIELD_MAP = [
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
    "npl_ratio_reported", "coverage_ratio_reported",
    "roe_reported", "roa_reported", "cost_income_reported",
    "fx_rate_period_end", "fx_rate_period_avg",
]


def _make_bank_obj(extracted: dict, file_path: str) -> "BankDB":
    """Build an unsaved BankDB instance from an extracted/parsed data dict."""
    from models import BankDB
    kwargs = {
        "bank_name":   extracted.get("name", "Unknown"),
        "country":     extracted.get("country"),
        "fiscal_year": extracted.get("fiscal_year"),
        "currency":    extracted.get("currency", "XOF"),
        "file_urls":   file_path,
        "total_assets": extracted.get("total_assets", 0),
    }
    for field in _FIELD_MAP:
        kwargs[field] = extracted.get(field)
    return BankDB(**kwargs)


def _rate_and_analyse(bank, db) -> tuple[dict, dict]:
    """Compute CAMELS ratings + analysis paragraphs; persist bank to DB. Returns (ratings, paragraphs)."""
    from camels_calculator import (
        rate_capital, rate_asset_quality, rate_management,
        rate_earnings, rate_liquidity, get_composite_rating,
        generate_analysis_paragraphs,
    )
    ratings = {
        "capital":       rate_capital(bank),
        "asset_quality": rate_asset_quality(bank),
        "management":    rate_management(bank),
        "earnings":      rate_earnings(bank),
        "liquidity":     rate_liquidity(bank),
    }
    composite = get_composite_rating(
        ratings["capital"], ratings["asset_quality"],
        ratings["management"], ratings["earnings"], ratings["liquidity"],
    )
    ratings["composite"] = composite
    paragraphs = generate_analysis_paragraphs(bank, ratings)
    bank.analysis_complete = True
    db.commit()
    db.refresh(bank)  # reload all attributes — commit expires them
    return ratings, paragraphs


def _build_period_result(bank, ratings: dict, paragraphs: dict) -> dict:
    bank_dict = {k: v for k, v in bank.__dict__.items() if not k.startswith("_")}
    composite = ratings.get("composite", {})
    return {
        "bank":             bank_dict,
        "camels_rating":    composite,
        "detailed_ratings": ratings,
        "analysis":         paragraphs,
        "key_metrics": {
            "total_assets":            bank.total_assets,
            "total_equity":            bank.total_equity,
            "net_income":              bank.net_income,
            # CAR is stored as percentage (e.g. 9.8 = 9.8%); convert to decimal
            "car":                     bank.car_regulatory / 100.0 if bank.car_regulatory else None,
            "equity_assets":           bank.equity_assets,
            "debt_assets":             bank.debt_assets,
            "npl_ratio":               bank.npl_ratio,
            "coverage_ratio":          bank.coverage_ratio,
            "cost_of_risk_avg_assets": bank.cost_of_risk_avg_assets,
            "cost_to_income":          bank.cost_to_income,
            "roaa":                    bank.roaa,
            "roae":                    bank.roae,
            "liquid_assets_total_assets": bank.liquid_assets_total_assets,
            "loans_deposits":          bank.gross_loans_deposits,
        },
    }


def process_job_async(job_id: str, file_path: str):
    from irp_parser import is_irp_report, parse_irp_excel
    from camels_calculator import calculate_all_ratios

    db = None
    try:
        # ── Route: IRP Report (structured Excel) vs raw document (LLM) ────────
        if is_irp_report(file_path):
            result = _process_irp_job(job_id, file_path)
        else:
            result = _process_llm_job(job_id, file_path)

        update_job(job_id, "completed", step="Done!", result=result)
        logger.info("Job %s completed successfully", job_id)

    except Exception as e:
        logger.error("Job %s failed: %s", job_id, str(e))
        logger.error(traceback.format_exc())
        update_job(job_id, "failed", step="Failed", error=str(e))
    finally:
        if db is not None:
            db.close()


def _process_irp_job(job_id: str, file_path: str) -> dict:
    """
    Fast path: IRP Report Excel — deterministic parsing, no LLM.
    All periods in the file are processed; result includes all periods
    with the most recent as the primary display target.
    """
    from irp_parser import parse_irp_excel
    from camels_calculator import calculate_all_ratios, generate_analysis_paragraphs

    update_job(job_id, "processing", step="Parsing IRP Report (structured Excel)...")
    periods = parse_irp_excel(file_path)

    if not periods:
        raise ValueError("IRP Report contains no period data")

    update_job(job_id, "processing", step=f"Processing {len(periods)} period(s)...")
    db = SessionLocal()
    try:
        saved_banks = []
        prev_bank = None

        for i, period_data in enumerate(periods):
            bank = _make_bank_obj(period_data, file_path)
            # Override period_end_date with parsed date object
            bank.period_end_date = period_data.get("period_end_date")

            # Compute ratios (uses prev_bank for averages if available)
            bank = calculate_all_ratios(bank, prev_bank=prev_bank)

            db.add(bank)
            db.commit()
            db.refresh(bank)

            update_job(
                job_id, "processing",
                step=f"Analysing {period_data.get('period_label', period_data.get('fiscal_year', i+1))}..."
            )
            ratings, paragraphs = _rate_and_analyse(bank, db)
            saved_banks.append((bank, ratings, paragraphs, period_data))
            prev_bank = bank

        # Most recent period = last (sorted oldest→newest by parse_irp_excel)
        latest_bank, latest_ratings, latest_paragraphs, latest_data = saved_banks[-1]

        # Re-generate latest period's analysis with multi-period evolution context
        if len(saved_banks) > 1:
            all_bank_objs = [b for b, _, _, _ in saved_banks]
            latest_paragraphs = generate_analysis_paragraphs(
                latest_bank, latest_ratings, all_banks=all_bank_objs,
            )
            db.commit()
            db.refresh(latest_bank)
            saved_banks[-1] = (latest_bank, latest_ratings, latest_paragraphs, latest_data)

        # Build per-period summary list (oldest→newest)
        all_periods = []
        for bank, ratings, paragraphs, pdata in saved_banks:
            pr = _build_period_result(bank, ratings, paragraphs)
            pr["period_label"] = pdata.get("period_label")
            all_periods.append(pr)

        primary = _build_period_result(latest_bank, latest_ratings, latest_paragraphs)
        return {
            "message":     f"IRP analysis complete — {len(periods)} period(s) processed.",
            "file":        latest_bank.bank_name,
            "all_periods": all_periods,
            **primary,
        }
    finally:
        db.close()


def _process_llm_job(job_id: str, file_path: str) -> dict:
    """
    Legacy path: raw bank document → Claude API extraction → CAMELS.
    """
    from llm_service import extract_bank_data_from_file
    from camels_calculator import calculate_all_ratios

    update_job(job_id, "processing", step="Extracting data from document...")
    extracted_data = extract_bank_data_from_file(file_path)

    update_job(job_id, "processing", step="Preparing data...")
    db = SessionLocal()
    try:
        bank = _make_bank_obj(extracted_data, file_path)

        update_job(job_id, "processing", step="Calculating CAMELS ratios...")
        bank = calculate_all_ratios(bank)

        update_job(job_id, "processing", step="Saving to database...")
        db.add(bank)
        db.commit()
        db.refresh(bank)

        update_job(job_id, "processing", step="Generating CAMELS ratings and analysis...")
        ratings, paragraphs = _rate_and_analyse(bank, db)

        result = _build_period_result(bank, ratings, paragraphs)
        result["message"] = "Analysis complete!"
        result["file"] = extracted_data.get("name", "Document")
        return result
    finally:
        db.close()
