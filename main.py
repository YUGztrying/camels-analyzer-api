import os
import logging

# Configure logging before other imports
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from supabase_client import get_client
from camels_calculator import run_full_analysis

logger = logging.getLogger(__name__)

# ===== Config =====
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")

_enable_docs = os.getenv("ENABLE_DOCS", "false").lower() == "true"

# ===== App =====
app = FastAPI(
    title="CAMELS Analyzer API",
    version="3.0.0",
    docs_url="/docs" if _enable_docs else None,
    redoc_url="/redoc" if _enable_docs else None,
    openapi_url="/openapi.json" if _enable_docs else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in CORS_ORIGINS],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)


# ===== Routes =====

@app.get("/")
def home():
    return {"message": "CAMELS Analyzer API", "version": "3.0.0"}


@app.get("/health")
def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Companies (read from Supabase — populated by the Spreading App)
# ---------------------------------------------------------------------------

@app.get("/companies")
def list_companies():
    """List all companies available for analysis."""
    sb = get_client()
    result = sb.table("companies").select("id, name, country, entity_type, created_at").order("name").execute()
    return {"total": len(result.data), "companies": result.data}


@app.get("/companies/{company_id}")
def get_company(company_id: str):
    """Get a single company."""
    sb = get_client()
    result = sb.table("companies").select("*").eq("id", company_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Company not found")
    return result.data[0]


# ---------------------------------------------------------------------------
# Financial Statements (read from Supabase — populated by the Spreading App)
# ---------------------------------------------------------------------------

@app.get("/companies/{company_id}/statements")
def list_statements(company_id: str):
    """List financial statements for a company."""
    sb = get_client()
    result = (
        sb.table("financial_statements")
        .select("id, company_id, fiscal_year, statement_type, currency, total_assets, total_equity, net_income, created_at")
        .eq("company_id", company_id)
        .order("fiscal_year", desc=True)
        .execute()
    )
    return {"total": len(result.data), "statements": result.data}


@app.get("/statements/{statement_id}")
def get_statement(statement_id: str):
    """Get full financial statement data."""
    sb = get_client()
    result = sb.table("financial_statements").select("*").eq("id", statement_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Financial statement not found")
    return result.data[0]


# ---------------------------------------------------------------------------
# CAMELS Analysis
# ---------------------------------------------------------------------------

@app.post("/statements/{statement_id}/analyze")
def analyze_statement(statement_id: str):
    """
    Run CAMELS analysis on a financial statement.
    Fetches the statement from Supabase, computes ratios/ratings,
    saves the analysis, and returns the full result.
    """
    sb = get_client()

    # 1. Fetch the statement
    stmt_result = sb.table("financial_statements").select("*").eq("id", statement_id).execute()
    if not stmt_result.data:
        raise HTTPException(status_code=404, detail="Financial statement not found")
    statement = stmt_result.data[0]

    # 2. Try to fetch previous period for averages
    prev_statement = None
    try:
        fiscal_year = statement.get("fiscal_year", "")
        if fiscal_year.isdigit():
            prev_year = str(int(fiscal_year) - 1)
            prev_result = (
                sb.table("financial_statements")
                .select("*")
                .eq("company_id", statement["company_id"])
                .eq("fiscal_year", prev_year)
                .eq("statement_type", statement.get("statement_type", "annual"))
                .execute()
            )
            if prev_result.data:
                prev_statement = prev_result.data[0]
                logger.info(f"Found previous period ({prev_year}) for averaging")
    except Exception as e:
        logger.warning(f"Could not fetch previous period: {e}")

    # 3. Run the full CAMELS analysis
    analysis_result = run_full_analysis(statement, prev_statement)

    # 4. Fetch company name for the response
    company = None
    try:
        comp_result = sb.table("companies").select("name, country").eq("id", statement["company_id"]).execute()
        if comp_result.data:
            company = comp_result.data[0]
    except Exception:
        pass

    # 5. Save analysis to Supabase (upsert — re-running overwrites)
    analysis_row = {
        "statement_id": statement_id,
        "company_id": statement["company_id"],
        "user_id": statement["user_id"],
        # Computed ratios
        **{k: v for k, v in analysis_result["ratios"].items()},
        # Ratings as JSONB
        "capital_rating": analysis_result["ratings"]["capital"],
        "asset_quality_rating": analysis_result["ratings"]["asset_quality"],
        "management_rating": analysis_result["ratings"]["management"],
        "earnings_rating": analysis_result["ratings"]["earnings"],
        "liquidity_rating": analysis_result["ratings"]["liquidity"],
        "composite_rating": analysis_result["ratings"]["composite"],
        # Analysis paragraphs
        "analysis_capital": analysis_result["analysis"].get("capital"),
        "analysis_asset_quality": analysis_result["analysis"].get("asset_quality"),
        "analysis_management": analysis_result["analysis"].get("management"),
        "analysis_earnings": analysis_result["analysis"].get("earnings"),
        "analysis_liquidity": analysis_result["analysis"].get("liquidity"),
        "analysis_composite": analysis_result["analysis"].get("composite"),
    }

    try:
        sb.table("camels_analyses").upsert(analysis_row, on_conflict="statement_id").execute()
        logger.info(f"Analysis saved for statement {statement_id}")
    except Exception as e:
        logger.error(f"Failed to save analysis: {e}")

    # 6. Build response
    bank_name = company["name"] if company else statement.get("name", "Unknown")
    return {
        "message": "Analysis complete",
        "bank_name": bank_name,
        "country": company["country"] if company else statement.get("country"),
        "fiscal_year": statement.get("fiscal_year"),
        "currency": statement.get("currency", "XOF"),
        "statement": statement,
        "ratios": analysis_result["ratios"],
        "ratings": analysis_result["ratings"],
        "analysis": analysis_result["analysis"],
        "key_metrics": {
            "total_assets": statement.get("total_assets"),
            "total_equity": statement.get("total_equity"),
            "net_income": statement.get("net_income"),
            "car": statement.get("car_regulatory"),
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


@app.get("/statements/{statement_id}/analysis")
def get_analysis(statement_id: str):
    """Retrieve a previously computed CAMELS analysis."""
    sb = get_client()
    result = sb.table("camels_analyses").select("*").eq("statement_id", statement_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="No analysis found for this statement. Run POST /statements/{id}/analyze first.")
    return result.data[0]


@app.get("/analyses")
def list_analyses():
    """List all CAMELS analyses with company info."""
    sb = get_client()
    result = (
        sb.table("camels_analyses")
        .select("id, statement_id, company_id, composite_rating, created_at")
        .order("created_at", desc=True)
        .execute()
    )
    return {"total": len(result.data), "analyses": result.data}
