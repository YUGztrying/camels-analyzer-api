"""
Narrative Generator — uses Claude API to produce rich, multi-bullet
CAMELS analysis text from multi-period financial data.

Falls back to None when ANTHROPIC_API_KEY is not set, so callers can
use the deterministic paragraphs from camels_calculator instead.
"""

import os
import logging

logger = logging.getLogger(__name__)


def _fmt(v, pct=False):
    """Format a value for the prompt."""
    if v is None:
        return "N/A"
    if pct:
        return f"{v * 100:.2f}%"
    if abs(v) >= 1_000_000:
        return f"{v / 1_000_000:,.1f}M"
    if abs(v) >= 1_000:
        return f"{v / 1_000:,.1f}K"
    return f"{v:,.0f}"


def generate_narrative(
    company_name: str,
    type_institution: str,
    currency: str,
    period_labels: list[str],
    statements: list[dict],
    ratios_by_period: list[dict],
    ratings: dict,
    financial_summary: dict,
) -> dict | None:
    """
    Call Claude to generate rich bullet-point analysis per CAMELS component.
    Returns a dict {capital, asset_quality, management, earnings, liquidity, composite}
    or None if the API is unavailable.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.info("ANTHROPIC_API_KEY not set — skipping narrative generation")
        return None

    try:
        import anthropic
    except ImportError:
        logger.warning("anthropic package not installed — skipping narrative")
        return None

    data_block = _build_data_block(
        company_name, type_institution, currency,
        period_labels, statements, ratios_by_period, ratings, financial_summary,
    )

    prompt = f"""You are a senior credit analyst writing a CAMELS assessment report for a {type_institution} institution named "{company_name}". Currency is {currency}.

Below is the multi-period financial data and computed ratios.

{data_block}

Write a detailed analytical narrative for each CAMELS component. For each section:
- Use the exact header format: **Section Name (Rating: Status)**
- Write 3-5 bullet points starting with "•"
- Reference specific numbers, trends, and growth rates across periods (use the period labels like {', '.join(period_labels)})
- Note improving or deteriorating trends with precise figures
- For ratios, express as percentages (e.g. 12.5%)
- For monetary amounts, use {currency} with appropriate scale
- Compare to typical thresholds where relevant (e.g. "above the 8% regulatory minimum")
- Be concise but analytical — every bullet should add insight

Sections (use these exact headers):
1. **Capitalization (Rating: {ratings['capital'].get('status', 'N/A')})**
2. **Asset Quality (Rating: {ratings['asset_quality'].get('status', 'N/A')})**
3. **Management & Efficiency (Rating: {ratings['management'].get('status', 'N/A')})**
4. **Earnings (Rating: {ratings['earnings'].get('status', 'N/A')})**
5. **Liquidity (Rating: {ratings['liquidity'].get('status', 'N/A')})**
6. **Composite Assessment (Rating: {ratings['composite'].get('status', 'N/A')})**

Write ONLY the sections above, nothing else. Use === as separator between sections."""

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text
        return _parse_sections(text)
    except Exception as e:
        logger.error(f"Claude narrative generation failed: {e}")
        return None


def _build_data_block(
    company_name, type_institution, currency,
    period_labels, statements, ratios_by_period, ratings, financial_summary,
) -> str:
    lines = []
    plabels = "  |  ".join(period_labels)
    lines.append(f"Periods: {plabels}\n")

    # Financial summary
    lines.append("=== BALANCE SHEET ===")
    for row in financial_summary.get("balance_sheet", []):
        vals = "  |  ".join(_fmt(v) for v in row["values"])
        cagr = _fmt(row.get("cagr"), pct=True) if row.get("cagr") is not None else "—"
        lines.append(f"  {row['label']}: {vals}  (CAGR: {cagr})")

    lines.append("\n=== INCOME STATEMENT ===")
    for row in financial_summary.get("income_statement", []):
        vals = "  |  ".join(_fmt(v) for v in row["values"])
        cagr = _fmt(row.get("cagr"), pct=True) if row.get("cagr") is not None else "—"
        lines.append(f"  {row['label']}: {vals}  (CAGR: {cagr})")

    # Key ratios per period
    lines.append("\n=== KEY RATIOS PER PERIOD ===")
    ratio_keys = [
        ("Equity/Assets", "equity_assets"), ("Debt/Assets", "debt_assets"),
        ("NPL Ratio", "npl_ratio"), ("Coverage Ratio", "coverage_ratio"),
        ("Cost of Risk/Avg Assets", "cost_of_risk_avg_assets"),
        ("Cost-to-Income", "cost_to_income"),
        ("ROAA", "roaa"), ("ROAE", "roae"),
        ("NII/Avg Assets", "net_interest_income_avg_assets"),
        ("Liquid Assets/Total Assets", "liquid_assets_total_assets"),
        ("Gross Loans/Deposits", "gross_loans_deposits"),
        ("Asset Growth", "total_asset_growth"),
        ("Loan Growth", "gross_loan_growth"),
        ("Deposit Growth", "deposit_growth"),
    ]
    for label, key in ratio_keys:
        vals = "  |  ".join(_fmt(r.get(key), pct=True) for r in ratios_by_period)
        lines.append(f"  {label}: {vals}")

    # Ratings
    lines.append("\n=== LATEST RATINGS ===")
    for comp in ("capital", "asset_quality", "management", "earnings", "liquidity", "composite"):
        r = ratings.get(comp, {})
        lines.append(f"  {comp}: {r.get('rating', 'N/A')} ({r.get('status', 'N/A')})")

    return "\n".join(lines)


def _parse_sections(text: str) -> dict:
    """Parse Claude's response into per-component strings."""
    mapping = {
        "capitalization": "capital",
        "asset quality": "asset_quality",
        "management": "management",
        "earnings": "earnings",
        "liquidity": "liquidity",
        "composite": "composite",
    }
    sections = {}
    current_key = None
    current_lines = []

    for line in text.split("\n"):
        stripped = line.strip()
        # Check if this is a section header
        lower = stripped.lower()
        matched = False
        for keyword, key in mapping.items():
            if keyword in lower and ("rating" in lower or "**" in lower):
                # Save previous section
                if current_key and current_lines:
                    sections[current_key] = "\n".join(current_lines).strip()
                current_key = key
                current_lines = [stripped]
                matched = True
                break
        if not matched and stripped == "===":
            continue  # skip separator lines
        elif not matched and current_key:
            current_lines.append(line)

    # Save last section
    if current_key and current_lines:
        sections[current_key] = "\n".join(current_lines).strip()

    return sections if sections else None
