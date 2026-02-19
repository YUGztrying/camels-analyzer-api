"""
CAMELS Calculator — computes all ratios per the analyst cheat sheet
and generates a short paragraph analysis for each CAMELS component.

All functions work with plain dicts (from Supabase rows) — no ORM objects.

Formulas
--------
C — Capital Adequacy
  Equity / Assets = Shareholders' Equity / Total Assets
  Debt / Assets   = (Short-Term Borrowings + Long-Term Debt) / Total Assets

A — Asset Quality
  NPL Ratio       = NPLs (Stage 3) / Gross Loans
  Coverage Ratio   = Loan Loss Provisions (ECL) / NPLs
  Cost of Risk / Avg Assets = ECL / Average Total Assets

M — Management (Efficiency)
  Cost-to-Income  = Operating Expenses / Operating Income

E — Earnings
  ROAA                          = Net Profit / Average Total Assets
  ROAE                          = Net Profit / Average Shareholders' Equity
  Net Interest Income / Avg Assets  = Net Interest Income / Avg Total Assets
  Non-Interest Income / Avg Assets  = (Fees & Commissions + ...) / Avg Total Assets
  Operating Expenses / Avg Assets   = (Wages + ...) / Avg Total Assets
  Tax Expenses / Avg Assets         = Tax Expenses / Avg Total Assets
  Other Income / Avg Assets         = (Provisions Formed + Impairment + FX) / Avg Total Assets

L — Liquidity
  Liquid Assets / Total Assets = (Cash & Deposits with Banks + Investment Securities) / Total Assets
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_divide(numerator, denominator):
    """Return numerator / denominator, or None when division is impossible."""
    if denominator is None or denominator == 0:
        return None
    if numerator is None:
        return None
    return numerator / denominator


def _calculate_average(current, previous=None):
    """Average of current and previous period value; falls back to current."""
    if previous is not None and previous != 0:
        if current:
            return (current + previous) / 2
        return previous
    return current if current else 0


def _get(data, key, default=0):
    """Safely read a key from a dict, returning *default* when None."""
    if data is None:
        return default
    val = data.get(key)
    return val if val is not None else default


def _pct(value):
    """Format a ratio (0.12) as '12.00%' string, or 'N/A'."""
    if value is None:
        return "N/A"
    return f"{value * 100:.2f}%"


def _rating_label(rating):
    return {1: "Strong", 2: "Satisfactory", 3: "Fair", 4: "Marginal", 5: "Unsatisfactory"}.get(rating, "N/A")


# ---------------------------------------------------------------------------
# Main calculation entry point
# ---------------------------------------------------------------------------

def calculate_all_ratios(statement: dict, prev_statement: dict = None) -> dict:
    """
    Compute every CAMELS ratio from a financial statement dict.
    Optionally uses *prev_statement* for period averages.
    Returns a new dict of computed ratios — does NOT mutate the input.
    """

    # Averages (current + previous period)
    avg_assets = _calculate_average(
        _get(statement, 'total_assets'),
        _get(prev_statement, 'total_assets') if prev_statement else None,
    )
    avg_equity = _calculate_average(
        _get(statement, 'total_equity'),
        _get(prev_statement, 'total_equity') if prev_statement else None,
    )
    avg_gross_loans = _calculate_average(
        _get(statement, 'gross_loans'),
        _get(prev_statement, 'gross_loans') if prev_statement else None,
    )

    ratios = {}

    # ===== C — CAPITAL ADEQUACY =====
    ratios['equity_assets'] = _safe_divide(
        _get(statement, 'total_equity'), _get(statement, 'total_assets'),
    )

    total_debt = _get(statement, 'short_term_borrowings') + _get(statement, 'long_term_debt')
    ratios['debt_assets'] = _safe_divide(total_debt, _get(statement, 'total_assets')) if total_debt else None

    # ===== A — ASSET QUALITY =====
    npls = _get(statement, 'npls_mn')
    llp = abs(_get(statement, 'loan_loss_provisions'))  # ECL — stored negative sometimes
    ecl = _get(statement, 'provision_expenses')  # income-statement ECL charge

    ratios['npl_ratio'] = _safe_divide(npls, _get(statement, 'gross_loans'))
    ratios['coverage_ratio'] = _safe_divide(llp, npls) if npls else None
    ratios['cost_of_risk_avg_assets'] = _safe_divide(ecl, avg_assets) if ecl else None

    # Extra asset quality ratios
    foreclosed = _get(statement, 'foreclosed_assets')
    problem_assets = npls + foreclosed
    ratios['problem_assets_mn'] = problem_assets if problem_assets else None

    llr = _get(statement, 'llr_mn')
    if llr == 0 and llp != 0:
        llr = llp

    npa_denom = _get(statement, 'gross_loans') + foreclosed
    ratios['npa_ratio'] = _safe_divide(problem_assets, npa_denom)
    ratios['llr_avg_loan'] = _safe_divide(llr, avg_gross_loans)
    ratios['oler'] = _safe_divide(problem_assets - llr, _get(statement, 'total_equity'))

    # ===== M — MANAGEMENT (Efficiency) =====
    op_income = _get(statement, 'operating_income')
    if not op_income:
        nii = _get(statement, 'net_interest_income')
        non_ii = (
            _get(statement, 'non_interest_income_commissions')
            + _get(statement, 'net_income_investment')
            + _get(statement, 'other_net_income')
        )
        # Also try granular non-interest income
        granular_non_ii = sum([
            _get(statement, 'fees_commissions'),
            _get(statement, 'net_sales'),
            _get(statement, 'dividends'),
            _get(statement, 'fvtpl_changes'),
            _get(statement, 'securitization_gains'),
            _get(statement, 'provisions_no_longer_required'),
            _get(statement, 'share_profit_associates'),
            _get(statement, 'other_revenues'),
            _get(statement, 'gain_acquisition_subsidiaries'),
        ])
        if granular_non_ii:
            non_ii = granular_non_ii
        op_income = nii + non_ii if (nii or non_ii) else 0

    ratios['cost_to_income'] = _safe_divide(_get(statement, 'operating_expenses'), op_income) if op_income else None

    # ===== E — EARNINGS =====
    net_profit = _get(statement, 'net_income') or _get(statement, 'net_profit')

    ratios['roaa'] = _safe_divide(net_profit, avg_assets)
    ratios['roae'] = _safe_divide(net_profit, avg_equity)

    # Net Interest Income / Avg Assets
    nii_val = _get(statement, 'net_interest_income')
    if not nii_val:
        ii = _get(statement, 'interest_income')
        ie = _get(statement, 'interest_expenses')
        nii_val = ii - ie if (ii or ie) else 0
    ratios['net_interest_income_avg_assets'] = _safe_divide(nii_val, avg_assets) if nii_val else None

    # Non-Interest Income / Avg Assets (granular)
    non_ii_total = sum([
        _get(statement, 'fees_commissions'),
        _get(statement, 'net_sales'),
        _get(statement, 'dividends'),
        _get(statement, 'fvtpl_changes'),
        _get(statement, 'securitization_gains'),
        _get(statement, 'provisions_no_longer_required'),
        _get(statement, 'share_profit_associates'),
        _get(statement, 'other_revenues'),
        _get(statement, 'gain_acquisition_subsidiaries'),
    ])
    if not non_ii_total:
        non_ii_total = (
            _get(statement, 'non_interest_income_commissions')
            + _get(statement, 'net_income_investment')
            + _get(statement, 'other_net_income')
        )
    ratios['non_interest_income_avg_assets'] = _safe_divide(non_ii_total, avg_assets) if non_ii_total else None

    # Operating Expenses / Avg Assets (granular)
    opex_granular = sum([
        _get(statement, 'wages_salaries'),
        _get(statement, 'other_opex'),
        _get(statement, 'intangible_amortization'),
        _get(statement, 'fixed_asset_depreciation'),
    ])
    opex_val = opex_granular if opex_granular else _get(statement, 'operating_expenses')
    ratios['opex_avg_assets'] = _safe_divide(opex_val, avg_assets)

    # Tax Expenses / Avg Assets
    ratios['tax_expenses_avg_assets'] = _safe_divide(_get(statement, 'income_tax'), avg_assets)

    # Other Income / Avg Assets
    other_income = sum([
        _get(statement, 'provisions_formed'),
        _get(statement, 'impairment_financial_assets'),
        _get(statement, 'fx_exchange'),
    ])
    ratios['other_income_avg_assets'] = _safe_divide(other_income, avg_assets) if other_income else None

    # Additional ratios
    ratios['net_interest_margin'] = _safe_divide(_get(statement, 'net_interest_income'), avg_assets)
    ratios['net_interest_spread'] = None
    yield_on_assets = _safe_divide(_get(statement, 'interest_income'), _get(statement, 'total_assets'))
    cost_of_liabs = _safe_divide(_get(statement, 'interest_expenses'), _get(statement, 'total_liabilities'))
    spread = (yield_on_assets or 0) - (cost_of_liabs or 0)
    if yield_on_assets is not None or cost_of_liabs is not None:
        ratios['net_interest_spread'] = spread

    ratios['interest_earning_assets_yield'] = _safe_divide(
        _get(statement, 'interest_income'),
        _get(statement, 'gross_loans') + _get(statement, 'investment_securities'),
    )
    ratios['cost_of_funds'] = _safe_divide(
        _get(statement, 'interest_expenses'), _get(statement, 'total_liabilities'),
    )
    ratios['assets_equity'] = _safe_divide(avg_assets, avg_equity)

    # ===== L — LIQUIDITY =====
    liquid_assets = (
        _get(statement, 'cash_reserves_requirements')
        + _get(statement, 'due_from_banks')
        + _get(statement, 'investment_securities')
    )
    ratios['liquid_assets_total_assets'] = _safe_divide(liquid_assets, _get(statement, 'total_assets'))
    ratios['cash_reserves_assets'] = _safe_divide(
        _get(statement, 'cash_reserves_requirements'), _get(statement, 'total_assets'),
    )
    ratios['gross_loans_deposits'] = _safe_divide(
        _get(statement, 'gross_loans'), _get(statement, 'deposits'),
    )

    return ratios


# ---------------------------------------------------------------------------
# Rating functions (1 = Strong ... 5 = Unsatisfactory)
# ---------------------------------------------------------------------------

def rate_capital(ratios: dict):
    """Rate C — Capital Adequacy using Equity/Assets."""
    ratio = ratios.get('equity_assets')
    if ratio is None:
        return {"rating": None, "status": "Insufficient data", "ratios": {}}

    if ratio >= 0.12:
        r = 1
    elif ratio >= 0.09:
        r = 2
    elif ratio >= 0.06:
        r = 3
    elif ratio >= 0.04:
        r = 4
    else:
        r = 5

    return {
        "rating": r,
        "status": _rating_label(r),
        "ratios": {
            "equity_assets": ratio,
            "debt_assets": ratios.get('debt_assets'),
        },
    }


def rate_asset_quality(ratios: dict):
    """Rate A — Asset Quality using NPL ratio."""
    npl = ratios.get('npl_ratio')
    if npl is None:
        return {"rating": None, "status": "Insufficient data", "ratios": {}}

    if npl < 0.02:
        r = 1
    elif npl < 0.05:
        r = 2
    elif npl < 0.08:
        r = 3
    elif npl < 0.12:
        r = 4
    else:
        r = 5

    return {
        "rating": r,
        "status": _rating_label(r),
        "ratios": {
            "npl_ratio": npl,
            "coverage_ratio": ratios.get('coverage_ratio'),
            "cost_of_risk_avg_assets": ratios.get('cost_of_risk_avg_assets'),
        },
    }


def rate_management(ratios: dict):
    """Rate M — Management Efficiency using Cost-to-Income."""
    cti = ratios.get('cost_to_income')
    if cti is None:
        return {"rating": None, "status": "Insufficient data", "ratios": {}}

    if cti < 0.40:
        r = 1
    elif cti < 0.55:
        r = 2
    elif cti < 0.70:
        r = 3
    elif cti < 0.85:
        r = 4
    else:
        r = 5

    return {
        "rating": r,
        "status": _rating_label(r),
        "ratios": {
            "cost_to_income": cti,
        },
    }


def rate_earnings(ratios: dict):
    """Rate E — Earnings using ROAE."""
    roae = ratios.get('roae')
    if roae is None:
        return {"rating": None, "status": "Insufficient data", "ratios": {}}

    if roae >= 0.15:
        r = 1
    elif roae >= 0.10:
        r = 2
    elif roae >= 0.05:
        r = 3
    elif roae >= 0:
        r = 4
    else:
        r = 5

    return {
        "rating": r,
        "status": _rating_label(r),
        "ratios": {
            "roaa": ratios.get('roaa'),
            "roae": roae,
            "net_interest_income_avg_assets": ratios.get('net_interest_income_avg_assets'),
            "non_interest_income_avg_assets": ratios.get('non_interest_income_avg_assets'),
            "opex_avg_assets": ratios.get('opex_avg_assets'),
            "tax_expenses_avg_assets": ratios.get('tax_expenses_avg_assets'),
            "other_income_avg_assets": ratios.get('other_income_avg_assets'),
        },
    }


def rate_liquidity(ratios: dict):
    """Rate L — Liquidity using Liquid Assets / Total Assets."""
    ratio = ratios.get('liquid_assets_total_assets')
    if ratio is None:
        return {"rating": None, "status": "Insufficient data", "ratios": {}}

    if ratio >= 0.35:
        r = 1
    elif ratio >= 0.25:
        r = 2
    elif ratio >= 0.15:
        r = 3
    elif ratio >= 0.10:
        r = 4
    else:
        r = 5

    return {
        "rating": r,
        "status": _rating_label(r),
        "ratios": {
            "liquid_assets_total_assets": ratio,
        },
    }


def get_composite_rating(capital, asset, management, earnings, liquidity):
    """Average the component ratings into a composite CAMELS rating."""
    valid = [
        d["rating"] for d in [capital, asset, management, earnings, liquidity]
        if d and d.get("rating") is not None
    ]
    if not valid:
        return {"composite_rating": None, "status": "Insufficient data"}

    avg = sum(valid) / len(valid)
    composite = round(avg)
    return {
        "composite_rating": composite,
        "average": round(avg, 2),
        "status": _rating_label(composite),
        "components_used": len(valid),
    }


# ---------------------------------------------------------------------------
# Paragraph analysis generation
# ---------------------------------------------------------------------------

def generate_analysis_paragraphs(statement: dict, ratios: dict, ratings: dict) -> dict:
    """
    Generate a short analyst-style paragraph for each CAMELS component
    and a composite summary.  Returns a dict of paragraphs — no mutation.
    """
    name = statement.get('bank_name') or statement.get('name', 'The bank')
    year = statement.get('fiscal_year', 'the period')

    paragraphs = {}

    # --- C: Capital Adequacy ---
    c = ratings.get("capital", {})
    eq_a = ratios.get('equity_assets')
    d_a = ratios.get('debt_assets')
    c_text = f"Capital Adequacy — Rating: {c.get('rating', 'N/A')} ({c.get('status', 'N/A')}). "
    if eq_a is not None:
        c_text += f"{name} reports an Equity-to-Assets ratio of {_pct(eq_a)}, "
        if eq_a >= 0.10:
            c_text += "indicating a well-capitalized position that provides a comfortable buffer to absorb potential losses. "
        elif eq_a >= 0.06:
            c_text += "suggesting an adequate capital base, though limited headroom exists to absorb unexpected shocks. "
        else:
            c_text += "which signals thin capitalization and vulnerability to asset-quality deterioration. "
    if d_a is not None:
        c_text += f"The Debt-to-Assets ratio stands at {_pct(d_a)}, "
        if d_a <= 0.30:
            c_text += "reflecting moderate leverage."
        else:
            c_text += "indicating relatively high leverage that warrants monitoring."
    else:
        c_text += "Debt-to-Assets data was not available for this period."
    paragraphs["capital"] = c_text

    # --- A: Asset Quality ---
    a = ratings.get("asset_quality", {})
    npl = ratios.get('npl_ratio')
    cov = ratios.get('coverage_ratio')
    cor = ratios.get('cost_of_risk_avg_assets')
    a_text = f"Asset Quality — Rating: {a.get('rating', 'N/A')} ({a.get('status', 'N/A')}). "
    if npl is not None:
        a_text += f"The NPL ratio is {_pct(npl)}, "
        if npl < 0.05:
            a_text += "demonstrating strong credit discipline and healthy loan book quality. "
        elif npl < 0.10:
            a_text += "which is within acceptable bounds but warrants closer monitoring of specific sector exposures. "
        else:
            a_text += "which is elevated and suggests material credit risk that requires remedial action. "
    if cov is not None:
        a_text += f"The coverage ratio is {_pct(cov)}, "
        if cov >= 1.0:
            a_text += "meaning provisions fully cover non-performing exposures. "
        else:
            a_text += f"leaving {_pct(1 - cov) if cov < 1 else 'N/A'} of NPLs uncovered by provisions. "
    if cor is not None:
        a_text += f"Cost of risk relative to average assets is {_pct(cor)}."
    paragraphs["asset_quality"] = a_text

    # --- M: Management ---
    m = ratings.get("management", {})
    cti = ratios.get('cost_to_income')
    m_text = f"Management (Efficiency) — Rating: {m.get('rating', 'N/A')} ({m.get('status', 'N/A')}). "
    if cti is not None:
        m_text += f"The Cost-to-Income ratio is {_pct(cti)}, "
        if cti < 0.50:
            m_text += "reflecting strong operational efficiency — the bank converts a high share of income into profit. "
        elif cti < 0.70:
            m_text += "indicating moderate efficiency. There may be room to optimize operating costs relative to revenue generation. "
        else:
            m_text += "highlighting operational inefficiency. A significant portion of income is consumed by costs, limiting profitability. "
    else:
        m_text += "Cost-to-Income data was not available; management efficiency could not be assessed quantitatively."
    paragraphs["management"] = m_text

    # --- E: Earnings ---
    e = ratings.get("earnings", {})
    roaa = ratios.get('roaa')
    roae = ratios.get('roae')
    nii_a = ratios.get('net_interest_income_avg_assets')
    nonii_a = ratios.get('non_interest_income_avg_assets')
    opex_a = ratios.get('opex_avg_assets')
    tax_a = ratios.get('tax_expenses_avg_assets')
    e_text = f"Earnings — Rating: {e.get('rating', 'N/A')} ({e.get('status', 'N/A')}). "
    if roaa is not None:
        e_text += f"ROAA stands at {_pct(roaa)} "
    if roae is not None:
        e_text += f"and ROAE at {_pct(roae)}, "
        if roae >= 0.15:
            e_text += "demonstrating strong profitability and efficient use of shareholders' capital. "
        elif roae >= 0.05:
            e_text += "suggesting adequate earnings generation, with potential for improvement. "
        else:
            e_text += "indicating weak profitability that may erode capital over time. "
    if nii_a is not None:
        e_text += f"Net interest income represents {_pct(nii_a)} of average assets. "
    if nonii_a is not None:
        e_text += f"Non-interest income contributes {_pct(nonii_a)} of average assets, "
        if nonii_a and nonii_a > 0.02:
            e_text += "showing meaningful revenue diversification. "
        else:
            e_text += "suggesting limited diversification beyond traditional lending. "
    if opex_a is not None:
        e_text += f"Operating expenses absorb {_pct(opex_a)} of average assets. "
    if tax_a is not None:
        e_text += f"Tax expense accounts for {_pct(tax_a)} of average assets."
    paragraphs["earnings"] = e_text

    # --- L: Liquidity ---
    l_r = ratings.get("liquidity", {})
    la_ta = ratios.get('liquid_assets_total_assets')
    l_text = f"Liquidity — Rating: {l_r.get('rating', 'N/A')} ({l_r.get('status', 'N/A')}). "
    if la_ta is not None:
        l_text += f"Liquid assets (cash, deposits with banks, and investment securities) represent {_pct(la_ta)} of total assets. "
        if la_ta >= 0.30:
            l_text += "This comfortable buffer ensures the bank can meet short-term obligations and withstand deposit volatility. "
        elif la_ta >= 0.15:
            l_text += "This is an adequate level, though a sudden deposit outflow or market stress event could tighten the position. "
        else:
            l_text += "This low level raises concerns about the bank's ability to handle stress scenarios or sudden liquidity demands. "
    ld = ratios.get('gross_loans_deposits')
    if ld is not None:
        l_text += f"The Loans-to-Deposits ratio is {_pct(ld)}."
    paragraphs["liquidity"] = l_text

    # --- Composite ---
    comp = ratings.get("composite", {})
    comp_r = comp.get("composite_rating")
    comp_text = f"Composite CAMELS Rating: {comp_r} ({comp.get('status', 'N/A')}). "
    comp_text += f"Based on the analysis of {name} for fiscal year {year}, "
    if comp_r and comp_r <= 2:
        comp_text += "the bank exhibits a fundamentally sound financial condition across the key pillars. Continued vigilance is recommended to maintain this strong position."
    elif comp_r and comp_r <= 3:
        comp_text += "the bank demonstrates an acceptable financial condition overall, but some areas require management attention and corrective measures to prevent further deterioration."
    elif comp_r and comp_r <= 4:
        comp_text += "the bank displays material weaknesses in several areas that, if left unaddressed, could impair its financial viability. Prompt corrective action is needed."
    elif comp_r and comp_r == 5:
        comp_text += "the bank is in a critically weak condition with an imminent risk of failure. Immediate and decisive supervisory intervention is warranted."
    else:
        comp_text += "insufficient data was available to draw a definitive conclusion. Additional financial disclosures are needed."
    paragraphs["composite"] = comp_text

    return paragraphs


# ---------------------------------------------------------------------------
# Multi-period helpers
# ---------------------------------------------------------------------------

def compute_cagr(first_value, last_value, n_years):
    """Compound annual growth rate.  Returns None when inputs are unusable."""
    if not first_value or first_value <= 0 or not last_value or last_value <= 0 or n_years <= 0:
        return None
    return (last_value / first_value) ** (1.0 / n_years) - 1


def _compute_yoy_growth(current, previous):
    if not previous or previous == 0 or current is None:
        return None
    return (current - previous) / abs(previous)


def _years_between(first_period: str, last_period: str) -> float:
    from datetime import date
    d1 = date.fromisoformat(first_period)
    d2 = date.fromisoformat(last_period)
    return (d2 - d1).days / 365.25


def run_multi_period_analysis(statements: list[dict], periods: list[str]) -> dict:
    """
    Run CAMELS analysis across *all* available periods.

    Returns a dict with:
      ratios_by_period  – list of ratio dicts (one per period)
      ratings           – ratings based on the latest period
      financial_summary – balance-sheet + income-statement rows
      ratio_tables      – grouped ratio evolution rows
      analysis          – deterministic paragraph per component
    """
    if not statements:
        raise ValueError("No statement data available")

    # 1. Ratios per period (using prior period for averaging)
    ratios_by_period: list[dict] = []
    for i, stmt in enumerate(statements):
        prev = statements[i - 1] if i > 0 else None
        ratios = calculate_all_ratios(stmt, prev)
        # Growth rates
        if prev:
            ratios["total_asset_growth"] = _compute_yoy_growth(
                _get(stmt, "total_assets"), _get(prev, "total_assets"))
            ratios["gross_loan_growth"] = _compute_yoy_growth(
                _get(stmt, "gross_loans"), _get(prev, "gross_loans"))
            ratios["deposit_growth"] = _compute_yoy_growth(
                _get(stmt, "deposits"), _get(prev, "deposits"))
            ratios["equity_growth"] = _compute_yoy_growth(
                _get(stmt, "total_equity"), _get(prev, "total_equity"))
        else:
            for k in ("total_asset_growth", "gross_loan_growth",
                       "deposit_growth", "equity_growth"):
                ratios[k] = None
        ratios_by_period.append(ratios)

    # 2. Ratings on latest period
    latest = ratios_by_period[-1]
    ratings = {
        "capital": rate_capital(latest),
        "asset_quality": rate_asset_quality(latest),
        "management": rate_management(latest),
        "earnings": rate_earnings(latest),
        "liquidity": rate_liquidity(latest),
    }
    ratings["composite"] = get_composite_rating(
        ratings["capital"], ratings["asset_quality"],
        ratings["management"], ratings["earnings"], ratings["liquidity"],
    )

    # 3. Financial summary tables  ──────────────────────────────────
    n_years = _years_between(periods[0], periods[-1]) if len(periods) > 1 else 0

    def _summary_row(label, key, use_abs=False):
        vals = []
        for s in statements:
            v = _get(s, key)
            if use_abs and v:
                v = abs(v)
            vals.append(v if v else None)
        first = abs(vals[0]) if vals[0] else 0
        last = abs(vals[-1]) if vals[-1] else 0
        cagr = compute_cagr(first, last, n_years) if n_years > 0 else None
        return {"label": label, "key": key, "values": vals, "cagr": cagr}

    # Compute non-interest income per period
    for s in statements:
        oi = _get(s, "operating_income")
        nii = _get(s, "net_interest_income")
        s["_non_interest_income"] = (oi - nii) if oi and nii else 0

    financial_summary = {
        "balance_sheet": [
            _summary_row("Total Assets", "total_assets"),
            _summary_row("Total Liabilities", "total_liabilities"),
            _summary_row("Shareholders' Equity", "total_equity"),
            _summary_row("Cash & Bank Deposits", "cash_reserves_requirements"),
            _summary_row("Investment Securities", "investment_securities"),
            _summary_row("Gross Loans", "gross_loans"),
            _summary_row("Loan Loss Provisions", "loan_loss_provisions", use_abs=True),
            _summary_row("Customer Deposits", "deposits"),
            _summary_row("Borrowings", "short_term_borrowings"),
            _summary_row("Subordinated Debt", "long_term_debt"),
        ],
        "income_statement": [
            _summary_row("Net Interest Income", "net_interest_income"),
            _summary_row("Non-Interest Income", "_non_interest_income"),
            _summary_row("Operating Expenses", "operating_expenses"),
            _summary_row("Cost of Risk", "provision_expenses"),
            _summary_row("Net Profit", "net_income"),
        ],
    }

    # 4. Ratio evolution tables  ──────────────────────────────────
    def _ratio_row(label, key):
        return {"label": label, "key": key,
                "values": [r.get(key) for r in ratios_by_period]}

    ratio_tables = {
        "growth": [
            _ratio_row("Total Asset Growth", "total_asset_growth"),
            _ratio_row("Gross Loan Growth", "gross_loan_growth"),
            _ratio_row("Deposit Growth", "deposit_growth"),
            _ratio_row("Equity Growth", "equity_growth"),
        ],
        "solvency": [
            _ratio_row("Equity / Assets", "equity_assets"),
            _ratio_row("Debt / Assets", "debt_assets"),
        ],
        "asset_quality": [
            _ratio_row("NPL Ratio", "npl_ratio"),
            _ratio_row("Coverage Ratio", "coverage_ratio"),
            _ratio_row("Cost of Risk / Avg Assets", "cost_of_risk_avg_assets"),
        ],
        "profitability": [
            _ratio_row("ROAA", "roaa"),
            _ratio_row("ROAE", "roae"),
            _ratio_row("Cost-to-Income", "cost_to_income"),
            _ratio_row("NII / Avg Assets", "net_interest_income_avg_assets"),
            _ratio_row("Non-II / Avg Assets", "non_interest_income_avg_assets"),
            _ratio_row("OpEx / Avg Assets", "opex_avg_assets"),
            _ratio_row("Net Interest Margin", "net_interest_margin"),
        ],
        "liquidity": [
            _ratio_row("Liquid Assets / Total Assets", "liquid_assets_total_assets"),
            _ratio_row("Gross Loans / Deposits", "gross_loans_deposits"),
        ],
    }

    # 5. Deterministic analysis (fallback — replaced by Claude narrative when available)
    analysis = generate_analysis_paragraphs(statements[-1], latest, ratings)

    return {
        "ratios_by_period": ratios_by_period,
        "ratings": ratings,
        "financial_summary": financial_summary,
        "ratio_tables": ratio_tables,
        "analysis": analysis,
    }


# ---------------------------------------------------------------------------
# Convenience: run the full analysis pipeline (single period – kept for compat)
# ---------------------------------------------------------------------------

def run_full_analysis(statement: dict, prev_statement: dict = None) -> dict:
    """
    Run the complete CAMELS analysis pipeline on a financial statement dict.
    Returns a dict with ratios, ratings, and analysis paragraphs.
    """
    ratios = calculate_all_ratios(statement, prev_statement)

    ratings = {
        "capital": rate_capital(ratios),
        "asset_quality": rate_asset_quality(ratios),
        "management": rate_management(ratios),
        "earnings": rate_earnings(ratios),
        "liquidity": rate_liquidity(ratios),
    }
    composite = get_composite_rating(
        ratings["capital"], ratings["asset_quality"],
        ratings["management"], ratings["earnings"], ratings["liquidity"],
    )
    ratings["composite"] = composite

    # Merge company name into statement for paragraph generation
    paragraphs = generate_analysis_paragraphs(statement, ratios, ratings)

    return {
        "ratios": ratios,
        "ratings": ratings,
        "analysis": paragraphs,
    }
