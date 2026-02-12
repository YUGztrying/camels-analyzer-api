"""
CAMELS Calculator — computes all ratios per the analyst cheat sheet
and generates a short paragraph analysis for each CAMELS component.

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
  Net Interest Income / Avg Assets  = (Interest Income + Interest Expenses) / Avg Total Assets
  Non-Interest Income / Avg Assets  = (Fees & Commissions + Net Sales + Dividends + FVTPL Changes
                                       + Securitization Gains + Provisions No Longer Required
                                       + Share in Profit of Associates + Other Revenues
                                       + Gain on Acquisition of Subsidiaries) / Avg Total Assets
  Operating Expenses / Avg Assets   = (Wages & Salaries + Other OpEx + Intangible Amortization
                                       + Fixed Asset Depreciation) / Avg Total Assets
  Tax Expenses / Avg Assets         = Tax Expenses / Avg Total Assets
  Other Income / Avg Assets         = (Provisions Formed + Impairment in Financial Assets
                                       + Foreign Currency Exchange) / Avg Total Assets

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


def _get(obj, attr, default=0):
    """Safely read an attribute, returning *default* when None."""
    val = getattr(obj, attr, None)
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

def calculate_all_ratios(bank, prev_bank=None):
    """
    Compute every CAMELS ratio on *bank* (a BankDB instance) and write the
    results back onto the same object.  Optionally uses *prev_bank* for
    averages.  Returns the mutated bank.
    """

    # Averages (current + previous period)
    avg_assets = _calculate_average(_get(bank, 'total_assets'), _get(prev_bank, 'total_assets') if prev_bank else None)
    avg_equity = _calculate_average(_get(bank, 'total_equity'), _get(prev_bank, 'total_equity') if prev_bank else None)
    avg_gross_loans = _calculate_average(_get(bank, 'gross_loans'), _get(prev_bank, 'gross_loans') if prev_bank else None)

    # ===== C — CAPITAL ADEQUACY =====
    bank.equity_assets = _safe_divide(_get(bank, 'total_equity'), _get(bank, 'total_assets'))

    total_debt = _get(bank, 'short_term_borrowings') + _get(bank, 'long_term_debt')
    bank.debt_assets = _safe_divide(total_debt, _get(bank, 'total_assets')) if total_debt else None

    # ===== A — ASSET QUALITY =====
    npls = _get(bank, 'npls_mn')
    llp = abs(_get(bank, 'loan_loss_provisions'))  # ECL — stored negative sometimes
    ecl = _get(bank, 'provision_expenses')  # income-statement ECL charge

    bank.npl_ratio = _safe_divide(npls, _get(bank, 'gross_loans'))
    bank.coverage_ratio = _safe_divide(llp, npls) if npls else None
    bank.cost_of_risk_avg_assets = _safe_divide(ecl, avg_assets) if ecl else None

    # Extra legacy ratios
    foreclosed = _get(bank, 'foreclosed_assets')
    problem_assets = npls + foreclosed
    bank.problem_assets_mn = problem_assets if problem_assets else None

    llr = _get(bank, 'llr_mn')
    if llr == 0 and llp != 0:
        llr = llp

    npa_denom = _get(bank, 'gross_loans') + foreclosed
    bank.npa_ratio = _safe_divide(problem_assets, npa_denom)
    bank.llr_avg_loan = _safe_divide(llr, avg_gross_loans)
    bank.oler = _safe_divide(problem_assets - llr, _get(bank, 'total_equity'))

    # ===== M — MANAGEMENT (Efficiency) =====
    op_income = _get(bank, 'operating_income')
    if not op_income:
        # Derive operating income = net interest income + non-interest income
        nii = _get(bank, 'net_interest_income')
        non_ii = _get(bank, 'non_interest_income_commissions') + _get(bank, 'net_income_investment') + _get(bank, 'other_net_income')
        # Also try granular non-interest income
        granular_non_ii = sum([
            _get(bank, 'fees_commissions'),
            _get(bank, 'net_sales'),
            _get(bank, 'dividends'),
            _get(bank, 'fvtpl_changes'),
            _get(bank, 'securitization_gains'),
            _get(bank, 'provisions_no_longer_required'),
            _get(bank, 'share_profit_associates'),
            _get(bank, 'other_revenues'),
            _get(bank, 'gain_acquisition_subsidiaries'),
        ])
        if granular_non_ii:
            non_ii = granular_non_ii
        op_income = nii + non_ii if (nii or non_ii) else 0

    bank.cost_to_income = _safe_divide(_get(bank, 'operating_expenses'), op_income) if op_income else None

    # ===== E — EARNINGS =====
    net_profit = _get(bank, 'net_income') or _get(bank, 'net_profit')

    # ROAA & ROAE — direct formula
    bank.roaa = _safe_divide(net_profit, avg_assets)
    bank.roae = _safe_divide(net_profit, avg_equity)

    # Net Interest Income / Avg Assets
    # Note: interest_expenses is extracted as a positive number, so we subtract
    # to get net interest income. Falls back to net_interest_income if available.
    nii_val = _get(bank, 'net_interest_income')
    if not nii_val:
        ii = _get(bank, 'interest_income')
        ie = _get(bank, 'interest_expenses')
        nii_val = ii - ie if (ii or ie) else 0
    bank.net_interest_income_avg_assets = _safe_divide(nii_val, avg_assets) if nii_val else None

    # Non-Interest Income / Avg Assets (granular)
    non_ii_total = sum([
        _get(bank, 'fees_commissions'),
        _get(bank, 'net_sales'),
        _get(bank, 'dividends'),
        _get(bank, 'fvtpl_changes'),
        _get(bank, 'securitization_gains'),
        _get(bank, 'provisions_no_longer_required'),
        _get(bank, 'share_profit_associates'),
        _get(bank, 'other_revenues'),
        _get(bank, 'gain_acquisition_subsidiaries'),
    ])
    if not non_ii_total:
        # Fallback to aggregate fields
        non_ii_total = _get(bank, 'non_interest_income_commissions') + _get(bank, 'net_income_investment') + _get(bank, 'other_net_income')
    bank.non_interest_income_avg_assets = _safe_divide(non_ii_total, avg_assets) if non_ii_total else None

    # Operating Expenses / Avg Assets (granular)
    opex_granular = sum([
        _get(bank, 'wages_salaries'),
        _get(bank, 'other_opex'),
        _get(bank, 'intangible_amortization'),
        _get(bank, 'fixed_asset_depreciation'),
    ])
    opex_val = opex_granular if opex_granular else _get(bank, 'operating_expenses')
    bank.opex_avg_assets = _safe_divide(opex_val, avg_assets)

    # Tax Expenses / Avg Assets
    bank.tax_expenses_avg_assets = _safe_divide(_get(bank, 'income_tax'), avg_assets)

    # Other Income / Avg Assets
    other_income = sum([
        _get(bank, 'provisions_formed'),
        _get(bank, 'impairment_financial_assets'),
        _get(bank, 'fx_exchange'),
    ])
    bank.other_income_avg_assets = _safe_divide(other_income, avg_assets) if other_income else None

    # Legacy DuPont fields (kept for backward compatibility)
    bank.net_interest_margin = _safe_divide(_get(bank, 'net_interest_income'), avg_assets)
    bank.net_interest_income_assets = bank.net_interest_margin
    bank.non_interest_income_assets = bank.non_interest_income_avg_assets
    bank.non_interest_income_assets_dupont = bank.non_interest_income_avg_assets
    bank.opex_assets = bank.opex_avg_assets
    bank.opex_assets_dupont = bank.opex_avg_assets
    bank.provision_expenses_assets = _safe_divide(_get(bank, 'provision_expenses'), avg_assets)
    bank.non_op_assets = _safe_divide(_get(bank, 'non_operating_profit_loss'), avg_assets)
    bank.tax_expenses_assets = bank.tax_expenses_avg_assets
    bank.assets_equity = _safe_divide(avg_assets, avg_equity)

    yield_on_assets = _safe_divide(_get(bank, 'interest_income'), _get(bank, 'total_assets'))
    cost_of_liabs = _safe_divide(_get(bank, 'interest_expenses'), _get(bank, 'total_liabilities'))
    spread = (yield_on_assets or 0) - (cost_of_liabs or 0)
    bank.net_interest_spread = spread if (yield_on_assets is not None or cost_of_liabs is not None) else None
    bank.interest_earning_assets_yield = _safe_divide(
        _get(bank, 'interest_income'),
        _get(bank, 'gross_loans') + _get(bank, 'investment_securities'))
    bank.cost_of_funds = _safe_divide(_get(bank, 'interest_expenses'), _get(bank, 'total_liabilities'))

    # ===== L — LIQUIDITY =====
    liquid_assets = _get(bank, 'cash_reserves_requirements') + _get(bank, 'due_from_banks') + _get(bank, 'investment_securities')
    bank.liquid_assets_total_assets = _safe_divide(liquid_assets, _get(bank, 'total_assets'))
    bank.liquid_assets_assets = bank.liquid_assets_total_assets  # legacy alias
    bank.cash_reserves_assets = _safe_divide(_get(bank, 'cash_reserves_requirements'), _get(bank, 'total_assets'))
    bank.gross_loans_deposits = _safe_divide(_get(bank, 'gross_loans'), _get(bank, 'deposits'))

    return bank


# ---------------------------------------------------------------------------
# Rating functions (1 = Strong … 5 = Unsatisfactory)
# ---------------------------------------------------------------------------

def rate_capital(bank):
    """Rate C — Capital Adequacy using Equity/Assets."""
    ratio = getattr(bank, 'equity_assets', None)
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
            "debt_assets": getattr(bank, 'debt_assets', None),
        },
    }


def rate_asset_quality(bank):
    """Rate A — Asset Quality using NPL ratio."""
    npl = getattr(bank, 'npl_ratio', None)
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
            "coverage_ratio": getattr(bank, 'coverage_ratio', None),
            "cost_of_risk_avg_assets": getattr(bank, 'cost_of_risk_avg_assets', None),
        },
    }


def rate_management(bank):
    """Rate M — Management Efficiency using Cost-to-Income."""
    cti = getattr(bank, 'cost_to_income', None)
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


def rate_earnings(bank):
    """Rate E — Earnings using ROAE."""
    roae = getattr(bank, 'roae', None)
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
            "roaa": getattr(bank, 'roaa', None),
            "roae": roae,
            "net_interest_income_avg_assets": getattr(bank, 'net_interest_income_avg_assets', None),
            "non_interest_income_avg_assets": getattr(bank, 'non_interest_income_avg_assets', None),
            "opex_avg_assets": getattr(bank, 'opex_avg_assets', None),
            "tax_expenses_avg_assets": getattr(bank, 'tax_expenses_avg_assets', None),
            "other_income_avg_assets": getattr(bank, 'other_income_avg_assets', None),
        },
    }


def rate_liquidity(bank):
    """Rate L — Liquidity using Liquid Assets / Total Assets."""
    ratio = getattr(bank, 'liquid_assets_total_assets', None)
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

def generate_analysis_paragraphs(bank, ratings):
    """
    Generate a short analyst-style paragraph for each CAMELS component
    and a composite summary.  Writes directly onto *bank* object and
    returns a dict of the paragraphs.
    """
    name = getattr(bank, 'bank_name', 'The bank')
    year = getattr(bank, 'fiscal_year', 'the period')

    paragraphs = {}

    # --- C: Capital Adequacy ---
    c = ratings.get("capital", {})
    eq_a = getattr(bank, 'equity_assets', None)
    d_a = getattr(bank, 'debt_assets', None)
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
    bank.analysis_capital = c_text

    # --- A: Asset Quality ---
    a = ratings.get("asset_quality", {})
    npl = getattr(bank, 'npl_ratio', None)
    cov = getattr(bank, 'coverage_ratio', None)
    cor = getattr(bank, 'cost_of_risk_avg_assets', None)
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
    bank.analysis_asset_quality = a_text

    # --- M: Management ---
    m = ratings.get("management", {})
    cti = getattr(bank, 'cost_to_income', None)
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
    bank.analysis_management = m_text

    # --- E: Earnings ---
    e = ratings.get("earnings", {})
    roaa = getattr(bank, 'roaa', None)
    roae = getattr(bank, 'roae', None)
    nii_a = getattr(bank, 'net_interest_income_avg_assets', None)
    nonii_a = getattr(bank, 'non_interest_income_avg_assets', None)
    opex_a = getattr(bank, 'opex_avg_assets', None)
    tax_a = getattr(bank, 'tax_expenses_avg_assets', None)
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
    bank.analysis_earnings = e_text

    # --- L: Liquidity ---
    l = ratings.get("liquidity", {})
    la_ta = getattr(bank, 'liquid_assets_total_assets', None)
    l_text = f"Liquidity — Rating: {l.get('rating', 'N/A')} ({l.get('status', 'N/A')}). "
    if la_ta is not None:
        l_text += f"Liquid assets (cash, deposits with banks, and investment securities) represent {_pct(la_ta)} of total assets. "
        if la_ta >= 0.30:
            l_text += "This comfortable buffer ensures the bank can meet short-term obligations and withstand deposit volatility. "
        elif la_ta >= 0.15:
            l_text += "This is an adequate level, though a sudden deposit outflow or market stress event could tighten the position. "
        else:
            l_text += "This low level raises concerns about the bank's ability to handle stress scenarios or sudden liquidity demands. "
    ld = getattr(bank, 'gross_loans_deposits', None)
    if ld is not None:
        l_text += f"The Loans-to-Deposits ratio is {_pct(ld)}."
    paragraphs["liquidity"] = l_text
    bank.analysis_liquidity = l_text

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
    bank.analysis_composite = comp_text

    return paragraphs
