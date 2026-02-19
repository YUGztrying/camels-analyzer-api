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
from camels_calculator import run_full_analysis, run_multi_period_analysis
from statement_reader import (
    extract_statement_data,
    extract_all_periods_data,
    extract_previous_period_data,
    list_companies_for_user,
    list_periods_for_company,
    period_label,
)
from narrative_generator import generate_narrative

logger = logging.getLogger(__name__)

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
CORS_REGEX = os.getenv("CORS_ORIGIN_REGEX", r"https://.*\.vercel\.app")
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
    allow_origin_regex=CORS_REGEX,
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
    user_id: str = None,
    authorization: str | None = Header(None),
):
    """
    Run multi-period CAMELS analysis on a company (all available periods).

    Reads financial data from the Spreading App's financial_statements table,
    computes ratios/ratings across every period, optionally generates a
    Claude-powered narrative, and returns the full analysis.
    """
    uid = user_id or _get_user_id(authorization)
    if not uid:
        raise HTTPException(status_code=400, detail="user_id required")

    # 1. Extract ALL periods at once
    try:
        statements, periods, type_inst = extract_all_periods_data(
            uid, company_name, type_institution=None,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if not statements:
        raise HTTPException(status_code=404, detail="No period data found")

    labels = [period_label(p) for p in periods]
    logger.info(f"Analyzing {company_name}: {len(periods)} periods ({labels})")

    # 2. Run multi-period CAMELS analysis
    result = run_multi_period_analysis(statements, periods)

    # 3. Rich narrative via Claude (falls back to deterministic if unavailable)
    narrative = generate_narrative(
        company_name, type_inst, "XOF", labels,
        statements, result["ratios_by_period"],
        result["ratings"], result["financial_summary"],
    )
    analysis = narrative if narrative else result["analysis"]

    # 4. Save latest-period snapshot to Supabase
    latest_ratios = result["ratios_by_period"][-1]
    latest_period = periods[-1]
    analysis_row = {
        "user_id": uid,
        "company_name": company_name,
        "period": latest_period,
        "type_institution": type_inst,
        **{k: v for k, v in latest_ratios.items()
           if k not in ("total_asset_growth", "gross_loan_growth",
                        "deposit_growth", "equity_growth")},
        "capital_rating": result["ratings"]["capital"],
        "asset_quality_rating": result["ratings"]["asset_quality"],
        "management_rating": result["ratings"]["management"],
        "earnings_rating": result["ratings"]["earnings"],
        "liquidity_rating": result["ratings"]["liquidity"],
        "composite_rating": result["ratings"]["composite"],
        "analysis_capital": analysis.get("capital", ""),
        "analysis_asset_quality": analysis.get("asset_quality", ""),
        "analysis_management": analysis.get("management", ""),
        "analysis_earnings": analysis.get("earnings", ""),
        "analysis_liquidity": analysis.get("liquidity", ""),
        "analysis_composite": analysis.get("composite", ""),
    }
    try:
        sb = get_client()
        sb.table("camels_analyses").upsert(
            analysis_row, on_conflict="user_id,company_name,period"
        ).execute()
        logger.info(f"Analysis saved for {company_name} / {latest_period}")
    except Exception as e:
        logger.error(f"Failed to save analysis: {e}")

    # 5. Build key_metrics from latest period
    latest_stmt = statements[-1]
    key_metrics = {
        "total_assets": latest_stmt.get("total_assets"),
        "total_equity": latest_stmt.get("total_equity"),
        "net_income": latest_stmt.get("net_income"),
        "gross_loans": latest_stmt.get("gross_loans"),
        "deposits": latest_stmt.get("deposits"),
        "equity_assets": latest_ratios.get("equity_assets"),
        "debt_assets": latest_ratios.get("debt_assets"),
        "npl_ratio": latest_ratios.get("npl_ratio"),
        "coverage_ratio": latest_ratios.get("coverage_ratio"),
        "cost_of_risk_avg_assets": latest_ratios.get("cost_of_risk_avg_assets"),
        "cost_to_income": latest_ratios.get("cost_to_income"),
        "roaa": latest_ratios.get("roaa"),
        "roae": latest_ratios.get("roae"),
        "liquid_assets_total_assets": latest_ratios.get("liquid_assets_total_assets"),
        "gross_loans_deposits": latest_ratios.get("gross_loans_deposits"),
    }

    return {
        "message": "Analysis complete",
        "company_name": company_name,
        "type_institution": type_inst,
        "currency": "XOF",
        "periods": periods,
        "period_labels": labels,
        "financial_summary": result["financial_summary"],
        "ratio_tables": result["ratio_tables"],
        "ratings": result["ratings"],
        "analysis": analysis,
        "key_metrics": key_metrics,
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
