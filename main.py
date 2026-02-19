import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware

from supabase_client import get_client
from camels_calculator import run_full_analysis
from statement_reader import (
    extract_statement_data,
    extract_previous_period_data,
    list_companies_for_user,
    list_periods_for_company,
)

logger = logging.getLogger(__name__)

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
_enable_docs = os.getenv("ENABLE_DOCS", "false").lower() == "true"

app = FastAPI(
    title="CAMELS Analyzer API",
    version="4.0.0",
    docs_url="/docs" if _enable_docs else None,
    redoc_url="/redoc" if _enable_docs else None,
    openapi_url="/openapi.json" if _enable_docs else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)


def _get_user_id(authorization: str | None) -> str:
    """
    Extract user_id from Supabase JWT in Authorization header.
    For now, also supports a direct user_id query param for development.
    In production, this should validate the JWT and extract the sub claim.
    """
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        # Decode JWT to get user_id (sub claim)
        # For service-role usage, we trust the token
        try:
            sb = get_client()
            user = sb.auth.get_user(token)
            return user.user.id
        except Exception:
            pass
    return None


# ===== Routes =====

@app.get("/")
def home():
    return {"message": "CAMELS Analyzer API", "version": "4.0.0"}


@app.get("/health")
def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Companies (from the Spreading App's user_companies view)
# ---------------------------------------------------------------------------

@app.get("/companies")
def list_companies(user_id: str = None, authorization: str | None = Header(None)):
    """List companies available for CAMELS analysis."""
    uid = user_id or _get_user_id(authorization)
    if not uid:
        raise HTTPException(status_code=400, detail="user_id query param or Authorization header required")

    companies = list_companies_for_user(uid)
    return {"total": len(companies), "companies": companies}


@app.get("/companies/{company_name}/periods")
def get_periods(company_name: str, user_id: str = None, authorization: str | None = Header(None)):
    """List available periods for a company."""
    uid = user_id or _get_user_id(authorization)
    if not uid:
        raise HTTPException(status_code=400, detail="user_id required")

    periods = list_periods_for_company(uid, company_name)
    if not periods:
        raise HTTPException(status_code=404, detail=f"No data found for company '{company_name}'")
    return {"company_name": company_name, "periods": periods}


# ---------------------------------------------------------------------------
# CAMELS Analysis
# ---------------------------------------------------------------------------

@app.post("/analyze")
def analyze(
    company_name: str,
    period: str,
    user_id: str = None,
    authorization: str | None = Header(None),
):
    """
    Run CAMELS analysis on a company for a specific period.

    Reads financial data from the Spreading App's financial_statements table,
    maps poste codes to calculator fields, computes ratios/ratings,
    saves results, and returns the full analysis.
    """
    uid = user_id or _get_user_id(authorization)
    if not uid:
        raise HTTPException(status_code=400, detail="user_id required")

    # 1. Extract current period data from Spreading App's financial_statements
    try:
        statement = extract_statement_data(uid, company_name, period, type_institution=None)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    type_inst = statement.get("type_institution", "banque")

    # 2. Try to get previous period for averaging
    prev_statement = extract_previous_period_data(uid, company_name, period, type_inst)
    if prev_statement:
        logger.info(f"Found previous period data for averaging")

    # 3. Run CAMELS analysis
    analysis_result = run_full_analysis(statement, prev_statement)

    # 4. Save to Supabase
    analysis_row = {
        "user_id": uid,
        "company_name": company_name,
        "period": period,
        "type_institution": type_inst,
        **{k: v for k, v in analysis_result["ratios"].items()},
        "capital_rating": analysis_result["ratings"]["capital"],
        "asset_quality_rating": analysis_result["ratings"]["asset_quality"],
        "management_rating": analysis_result["ratings"]["management"],
        "earnings_rating": analysis_result["ratings"]["earnings"],
        "liquidity_rating": analysis_result["ratings"]["liquidity"],
        "composite_rating": analysis_result["ratings"]["composite"],
        "analysis_capital": analysis_result["analysis"].get("capital"),
        "analysis_asset_quality": analysis_result["analysis"].get("asset_quality"),
        "analysis_management": analysis_result["analysis"].get("management"),
        "analysis_earnings": analysis_result["analysis"].get("earnings"),
        "analysis_liquidity": analysis_result["analysis"].get("liquidity"),
        "analysis_composite": analysis_result["analysis"].get("composite"),
    }

    try:
        sb = get_client()
        sb.table("camels_analyses").upsert(
            analysis_row, on_conflict="user_id,company_name,period"
        ).execute()
        logger.info(f"Analysis saved for {company_name} / {period}")
    except Exception as e:
        logger.error(f"Failed to save analysis: {e}")

    # 5. Return response
    return {
        "message": "Analysis complete",
        "company_name": company_name,
        "period": period,
        "type_institution": type_inst,
        "currency": "XOF",
        "extracted_data": statement,
        "ratios": analysis_result["ratios"],
        "ratings": analysis_result["ratings"],
        "analysis": analysis_result["analysis"],
        "key_metrics": {
            "total_assets": statement.get("total_assets"),
            "total_equity": statement.get("total_equity"),
            "net_income": statement.get("net_income"),
            "gross_loans": statement.get("gross_loans"),
            "deposits": statement.get("deposits"),
            "equity_assets": analysis_result["ratios"].get("equity_assets"),
            "debt_assets": analysis_result["ratios"].get("debt_assets"),
            "npl_ratio": analysis_result["ratios"].get("npl_ratio"),
            "coverage_ratio": analysis_result["ratios"].get("coverage_ratio"),
            "cost_of_risk_avg_assets": analysis_result["ratios"].get("cost_of_risk_avg_assets"),
            "cost_to_income": analysis_result["ratios"].get("cost_to_income"),
            "roaa": analysis_result["ratios"].get("roaa"),
            "roae": analysis_result["ratios"].get("roae"),
            "liquid_assets_total_assets": analysis_result["ratios"].get("liquid_assets_total_assets"),
            "gross_loans_deposits": analysis_result["ratios"].get("gross_loans_deposits"),
        },
    }


@app.get("/analyses")
def list_analyses(user_id: str = None, authorization: str | None = Header(None)):
    """List all CAMELS analyses for a user."""
    uid = user_id or _get_user_id(authorization)
    if not uid:
        raise HTTPException(status_code=400, detail="user_id required")

    sb = get_client()
    result = (
        sb.table("camels_analyses")
        .select("id, company_name, period, type_institution, composite_rating, created_at")
        .eq("user_id", uid)
        .order("created_at", desc=True)
        .execute()
    )
    return {"total": len(result.data), "analyses": result.data}


@app.get("/analyses/{company_name}/{period}")
def get_analysis(
    company_name: str,
    period: str,
    user_id: str = None,
    authorization: str | None = Header(None),
):
    """Retrieve a previously computed CAMELS analysis."""
    uid = user_id or _get_user_id(authorization)
    if not uid:
        raise HTTPException(status_code=400, detail="user_id required")

    sb = get_client()
    result = (
        sb.table("camels_analyses")
        .select("*")
        .eq("user_id", uid)
        .eq("company_name", company_name)
        .eq("period", period)
        .execute()
    )
    if not result.data:
        raise HTTPException(
            status_code=404,
            detail=f"No analysis found for {company_name} / {period}. Run POST /analyze first.",
        )
    return result.data[0]
