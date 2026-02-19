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
    if current is not None and previous is not None and previous != 0:
        return (current + previous) / 2
    if current is not None and current != 0:
        return current
    if previous is not None and previous != 0:
        return previous
    return None


def _get(obj, attr, default=None):
    """Safely read an attribute, returning *default* when None."""
    if obj is None:
        return default
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

    # Helper to sum only non-None values; returns None if all are None
    def _sum(*vals):
        non_none = [v for v in vals if v is not None]
        return sum(non_none) if non_none else None

    # Always recalculate NII from components when both are available —
    # the LLM sometimes maps PNB (which includes commissions) to net_interest_income.
    ii = _get(bank, 'interest_income')
    ie = _get(bank, 'interest_expenses')
    if ii is not None and ie is not None:
        bank.net_interest_income = ii - ie  # interest_expenses stored as positive

    # Averages (current + previous period)
    avg_assets = _calculate_average(_get(bank, 'total_assets'), _get(prev_bank, 'total_assets') if prev_bank else None)
    avg_equity = _calculate_average(_get(bank, 'total_equity'), _get(prev_bank, 'total_equity') if prev_bank else None)
    avg_gross_loans = _calculate_average(_get(bank, 'gross_loans'), _get(prev_bank, 'gross_loans') if prev_bank else None)

    # ===== C — CAPITAL ADEQUACY =====
    bank.equity_assets = _safe_divide(_get(bank, 'total_equity'), _get(bank, 'total_assets'))

    total_debt = _sum(_get(bank, 'short_term_borrowings'), _get(bank, 'long_term_debt'))
    bank.debt_assets = _safe_divide(total_debt, _get(bank, 'total_assets'))

    # ===== A — ASSET QUALITY =====
    npls = _get(bank, 'npls_mn')
    llp_raw = _get(bank, 'loan_loss_provisions')
    llp = abs(llp_raw) if llp_raw is not None else None
    ecl = _get(bank, 'provision_expenses')

    bank.npl_ratio = _safe_divide(npls, _get(bank, 'gross_loans'))
    # Fallback to bank-reported NPL ratio (stored as percentage, e.g. 5.2 -> 0.052)
    if bank.npl_ratio is None:
        reported = _get(bank, 'npl_ratio_reported')
        if reported is not None:
            bank.npl_ratio = reported / 100.0

    bank.coverage_ratio = _safe_divide(llp, npls)
    if bank.coverage_ratio is None:
        reported = _get(bank, 'coverage_ratio_reported')
        if reported is not None:
            bank.coverage_ratio = reported / 100.0

    bank.cost_of_risk_avg_assets = _safe_divide(ecl, avg_assets)

    # Extra legacy ratios
    foreclosed = _get(bank, 'foreclosed_assets')
    problem_assets = _sum(npls, foreclosed)
    bank.problem_assets_mn = problem_assets

    llr = _get(bank, 'llr_mn')
    if llr is None and llp is not None:
        llr = llp

    npa_denom = _sum(_get(bank, 'gross_loans'), foreclosed)
    bank.npa_ratio = _safe_divide(problem_assets, npa_denom)
    bank.llr_avg_loan = _safe_divide(llr, avg_gross_loans)
    oler_num = _sum(problem_assets, -llr if llr is not None else None) if problem_assets is not None and llr is not None else None
    bank.oler = _safe_divide(oler_num, _get(bank, 'total_equity'))

    # ===== M — MANAGEMENT (Efficiency) =====
    op_income = _get(bank, 'operating_income')
    if op_income is None:
        # Derive operating income = net interest income + non-interest income
        nii = _get(bank, 'net_interest_income')
        non_ii = _sum(
            _get(bank, 'non_interest_income_commissions'),
            _get(bank, 'net_income_investment'),
            _get(bank, 'other_net_income'),
        )
        # Also try granular non-interest income
        granular_non_ii = _sum(
            _get(bank, 'fees_commissions'),
            _get(bank, 'net_sales'),
            _get(bank, 'dividends'),
            _get(bank, 'fvtpl_changes'),
            _get(bank, 'securitization_gains'),
            _get(bank, 'provisions_no_longer_required'),
            _get(bank, 'share_profit_associates'),
            _get(bank, 'other_revenues'),
            _get(bank, 'gain_acquisition_subsidiaries'),
        )
        if granular_non_ii is not None:
            non_ii = granular_non_ii
        op_income = _sum(nii, non_ii)

    bank.cost_to_income = _safe_divide(_get(bank, 'operating_expenses'), op_income)
    if bank.cost_to_income is None:
        reported = _get(bank, 'cost_income_reported')
        if reported is not None:
            bank.cost_to_income = reported / 100.0

    # ===== E — EARNINGS =====
    net_profit = _get(bank, 'net_income')
    if net_profit is None:
        net_profit = _get(bank, 'net_profit')

    # ROAA & ROAE — direct formula, with reported fallback
    # Cap at ±100% to prevent misleading values from tiny denominators
    # (e.g. equity swinging from negative to positive creates near-zero average)
    bank.roaa = _safe_divide(net_profit, avg_assets)
    if bank.roaa is not None and abs(bank.roaa) > 1.0:
        bank.roaa = None  # discard implausible value
    if bank.roaa is None:
        reported = _get(bank, 'roa_reported')
        if reported is not None:
            bank.roaa = reported / 100.0

    bank.roae = _safe_divide(net_profit, avg_equity)
    if bank.roae is not None and abs(bank.roae) > 1.0:
        bank.roae = None  # discard implausible value
    if bank.roae is None:
        reported = _get(bank, 'roe_reported')
        if reported is not None:
            bank.roae = reported / 100.0

    # Net Interest Income / Avg Assets
    nii_val = _get(bank, 'net_interest_income')
    if nii_val is None:
        ii = _get(bank, 'interest_income')
        ie = _get(bank, 'interest_expenses')
        if ii is not None or ie is not None:
            nii_val = (ii or 0) - (ie or 0)
    bank.net_interest_income_avg_assets = _safe_divide(nii_val, avg_assets)

    # Non-Interest Income / Avg Assets (granular)
    non_ii_total = _sum(
        _get(bank, 'fees_commissions'),
        _get(bank, 'net_sales'),
        _get(bank, 'dividends'),
        _get(bank, 'fvtpl_changes'),
        _get(bank, 'securitization_gains'),
        _get(bank, 'provisions_no_longer_required'),
        _get(bank, 'share_profit_associates'),
        _get(bank, 'other_revenues'),
        _get(bank, 'gain_acquisition_subsidiaries'),
    )
    if non_ii_total is None:
        # Fallback to aggregate fields
        non_ii_total = _sum(
            _get(bank, 'non_interest_income_commissions'),
            _get(bank, 'net_income_investment'),
            _get(bank, 'other_net_income'),
        )
    bank.non_interest_income_avg_assets = _safe_divide(non_ii_total, avg_assets)

    # Operating Expenses / Avg Assets (granular)
    opex_granular = _sum(
        _get(bank, 'wages_salaries'),
        _get(bank, 'other_opex'),
        _get(bank, 'intangible_amortization'),
        _get(bank, 'fixed_asset_depreciation'),
    )
    opex_val = opex_granular if opex_granular is not None else _get(bank, 'operating_expenses')
    bank.opex_avg_assets = _safe_divide(opex_val, avg_assets)

    # Tax Expenses / Avg Assets
    bank.tax_expenses_avg_assets = _safe_divide(_get(bank, 'income_tax'), avg_assets)

    # Other Income / Avg Assets
    other_income = _sum(
        _get(bank, 'provisions_formed'),
        _get(bank, 'impairment_financial_assets'),
        _get(bank, 'fx_exchange'),
    )
    bank.other_income_avg_assets = _safe_divide(other_income, avg_assets)

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
    if yield_on_assets is not None and cost_of_liabs is not None:
        bank.net_interest_spread = yield_on_assets - cost_of_liabs
    else:
        bank.net_interest_spread = None
    earning_assets = _sum(_get(bank, 'gross_loans'), _get(bank, 'investment_securities'))
    bank.interest_earning_assets_yield = _safe_divide(_get(bank, 'interest_income'), earning_assets)
    bank.cost_of_funds = _safe_divide(_get(bank, 'interest_expenses'), _get(bank, 'total_liabilities'))

    # ===== L — LIQUIDITY =====
    liquid_assets = _sum(_get(bank, 'cash_reserves_requirements'), _get(bank, 'due_from_banks'), _get(bank, 'investment_securities'))
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

def _fmt_abs(value):
    """Format an absolute number with thousand separators, or 'N/A'."""
    if value is None:
        return "N/A"
    return f"{abs(value):,.0f}"


def _cagr(start, end, n_years):
    """Compound annual growth rate."""
    if start is None or end is None or n_years is None or n_years <= 0:
        return None
    if start <= 0 or end <= 0:
        return None
    return (end / start) ** (1 / n_years) - 1


def _trend_word(first_val, last_val):
    """Return a trend verb comparing two values."""
    if first_val is None or last_val is None:
        return "changed"
    if last_val > first_val * 1.005:
        return "improved" if last_val > first_val else "increased"
    elif last_val < first_val * 0.995:
        return "declined"
    return "remained stable"


def _ratio_trend(first_val, last_val, higher_is_better=True):
    """Return a trend verb for a ratio, taking direction into account."""
    if first_val is None or last_val is None:
        return "changed"
    diff = last_val - first_val
    if abs(diff) < 0.001:
        return "remained stable"
    if higher_is_better:
        return "improved" if diff > 0 else "deteriorated"
    else:
        return "improved" if diff < 0 else "deteriorated"


def generate_analysis_paragraphs(bank, ratings, all_banks=None):
    """
    Generate bullet-point analyst-style analysis for each CAMELS component.
    Returns a dict mapping component keys to *lists* of bullet strings.
    Also stores a joined text version on the bank object for DB persistence.

    If *all_banks* is provided (list of BankDB objects, oldest→newest),
    evolution bullets are added showing trends across periods.
    """
    name = getattr(bank, 'bank_name', 'The bank')
    year = getattr(bank, 'fiscal_year', 'the period')
    ccy = getattr(bank, 'currency', None) or 'XOF'

    # Evolution helpers — only when we have multiple periods
    has_evo = all_banks is not None and len(all_banks) > 1
    first_bank = all_banks[0] if has_evo else None
    first_yr = getattr(first_bank, 'fiscal_year', '?') if first_bank else '?'
    last_yr = year
    n_years = len(all_banks) - 1 if has_evo else 0

    paragraphs = {}

    # --- C: Capital Adequacy ---
    c_bullets = []
    eq_a = getattr(bank, 'equity_assets', None)
    d_a = getattr(bank, 'debt_assets', None)
    te = getattr(bank, 'total_equity', None)
    ta = getattr(bank, 'total_assets', None)
    car = getattr(bank, 'car_regulatory', None)

    if eq_a is not None:
        b = f"The Equity-to-Assets ratio stands at {_pct(eq_a)}"
        if te is not None:
            b += f" ({ccy} {_fmt_abs(te)} in equity on {ccy} {_fmt_abs(ta)} total assets)"
        if eq_a >= 0.10:
            b += ", indicating a well-capitalized position that provides a comfortable buffer to absorb potential losses."
        elif eq_a >= 0.06:
            b += ", suggesting an adequate capital base, though limited headroom exists to absorb unexpected shocks."
        else:
            b += ", which signals thin capitalization and vulnerability to asset-quality deterioration."
        c_bullets.append(b)
    if d_a is not None:
        b = f"The Debt-to-Assets ratio stands at {_pct(d_a)}, "
        b += "reflecting moderate leverage." if d_a <= 0.30 else "indicating relatively high leverage that warrants monitoring."
        c_bullets.append(b)
    if car is not None:
        c_bullets.append(f"The bank-reported Capital Adequacy Ratio (CAR) is {car:.1f}%.")
    # Evolution: Equity/Assets trend
    if has_evo:
        first_ea = getattr(first_bank, 'equity_assets', None)
        if first_ea is not None and eq_a is not None:
            trend = _ratio_trend(first_ea, eq_a, higher_is_better=True)
            c_bullets.append(
                f"Over the review period, the equity-to-assets ratio {trend} from "
                f"{_pct(first_ea)} ({first_yr}) to {_pct(eq_a)} ({last_yr})."
            )
        # Total equity CAGR
        first_te = getattr(first_bank, 'total_equity', None)
        if first_te is not None and te is not None:
            cagr = _cagr(first_te, te, n_years)
            if cagr is not None:
                c_bullets.append(
                    f"Shareholders' equity grew from {ccy} {_fmt_abs(first_te)} to "
                    f"{ccy} {_fmt_abs(te)}, a CAGR of {_pct(cagr)}."
                )
    if not c_bullets:
        c_bullets.append("Insufficient data to assess capital adequacy for this period.")
    paragraphs["capital"] = c_bullets
    bank.analysis_capital = "\n".join(c_bullets)

    # --- A: Asset Quality ---
    a_bullets = []
    npl = getattr(bank, 'npl_ratio', None)
    cov = getattr(bank, 'coverage_ratio', None)
    cor = getattr(bank, 'cost_of_risk_avg_assets', None)
    gl = getattr(bank, 'gross_loans', None)

    if npl is not None:
        b = f"The NPL ratio is {_pct(npl)}"
        if gl is not None:
            b += f" (on a gross loan book of {ccy} {_fmt_abs(gl)})"
        if npl < 0.05:
            b += ", demonstrating strong credit discipline and healthy loan book quality."
        elif npl < 0.10:
            b += ", within acceptable bounds but warranting closer monitoring of sector exposures."
        else:
            b += ", which is elevated and suggests material credit risk requiring remedial action."
        a_bullets.append(b)
    if cov is not None:
        b = f"The coverage ratio is {_pct(cov)}, "
        if cov >= 1.0:
            b += "meaning provisions fully cover non-performing exposures."
        else:
            b += f"leaving {_pct(1 - cov)} of NPLs uncovered by provisions."
        a_bullets.append(b)
    if cor is not None:
        a_bullets.append(f"Cost of risk relative to average assets is {_pct(cor)}.")
    # Evolution: NPL ratio + coverage trend
    if has_evo:
        first_npl = getattr(first_bank, 'npl_ratio', None)
        if first_npl is not None and npl is not None:
            trend = _ratio_trend(first_npl, npl, higher_is_better=False)
            a_bullets.append(
                f"The NPL ratio {trend} from {_pct(first_npl)} ({first_yr}) to {_pct(npl)} ({last_yr})."
            )
        first_cov = getattr(first_bank, 'coverage_ratio', None)
        if first_cov is not None and cov is not None:
            trend = _ratio_trend(first_cov, cov, higher_is_better=True)
            a_bullets.append(
                f"The coverage ratio {trend} from {_pct(first_cov)} ({first_yr}) to {_pct(cov)} ({last_yr})."
            )
    if not a_bullets:
        a_bullets.append("Insufficient data to assess asset quality for this period.")
    paragraphs["asset_quality"] = a_bullets
    bank.analysis_asset_quality = "\n".join(a_bullets)

    # --- M: Management ---
    m_bullets = []
    cti = getattr(bank, 'cost_to_income', None)
    opex = getattr(bank, 'operating_expenses', None)
    oi = getattr(bank, 'operating_income', None)

    if cti is not None:
        b = f"The Cost-to-Income ratio is {_pct(cti)}"
        if opex is not None and oi is not None:
            b += f" ({ccy} {_fmt_abs(opex)} expenses on {ccy} {_fmt_abs(oi)} operating income)"
        if cti < 0.50:
            b += ", reflecting strong operational efficiency — the bank converts a high share of income into profit."
        elif cti < 0.70:
            b += ", indicating moderate efficiency. There may be room to optimize operating costs relative to revenue."
        else:
            b += ", highlighting operational inefficiency. A significant portion of income is consumed by costs."
        m_bullets.append(b)
    else:
        m_bullets.append("Cost-to-Income data was not available; management efficiency could not be assessed.")
    # Evolution: Cost-to-Income trend
    if has_evo:
        first_cti = getattr(first_bank, 'cost_to_income', None)
        if first_cti is not None and cti is not None:
            trend = _ratio_trend(first_cti, cti, higher_is_better=False)
            m_bullets.append(
                f"The cost-to-income ratio {trend} from {_pct(first_cti)} ({first_yr}) to {_pct(cti)} ({last_yr})."
            )
    paragraphs["management"] = m_bullets
    bank.analysis_management = "\n".join(m_bullets)

    # --- E: Earnings ---
    e_bullets = []
    roaa = getattr(bank, 'roaa', None)
    roae = getattr(bank, 'roae', None)
    nii_a = getattr(bank, 'net_interest_income_avg_assets', None)
    nonii_a = getattr(bank, 'non_interest_income_avg_assets', None)
    opex_a = getattr(bank, 'opex_avg_assets', None)
    ni = getattr(bank, 'net_income', None)

    if roaa is not None or roae is not None:
        parts = []
        if roaa is not None:
            parts.append(f"ROAA of {_pct(roaa)}")
        if roae is not None:
            parts.append(f"ROAE of {_pct(roae)}")
        b = f"Profitability metrics show {' and '.join(parts)}"
        if ni is not None:
            b += f" (net income of {ccy} {_fmt_abs(ni)})"
        if roae is not None and roae >= 0.15:
            b += ", demonstrating strong profitability and efficient use of shareholders' capital."
        elif roae is not None and roae >= 0.05:
            b += ", suggesting adequate earnings generation with potential for improvement."
        elif roae is not None:
            b += ", indicating weak profitability that may erode capital over time."
        else:
            b += "."
        e_bullets.append(b)
    if nii_a is not None:
        b = f"Net interest income represents {_pct(nii_a)} of average assets"
        if nonii_a is not None:
            b += f", while non-interest income contributes {_pct(nonii_a)}"
            b += " — showing meaningful revenue diversification." if (nonii_a and nonii_a > 0.02) else " — suggesting limited diversification beyond traditional lending."
        else:
            b += "."
        e_bullets.append(b)
    if opex_a is not None:
        e_bullets.append(f"Operating expenses absorb {_pct(opex_a)} of average assets.")
    # Evolution: ROAE + ROAA trend
    if has_evo:
        first_roae = getattr(first_bank, 'roae', None)
        first_roaa = getattr(first_bank, 'roaa', None)
        evo_parts = []
        if first_roae is not None and roae is not None:
            trend = _ratio_trend(first_roae, roae, higher_is_better=True)
            evo_parts.append(f"ROAE {trend} from {_pct(first_roae)} to {_pct(roae)}")
        if first_roaa is not None and roaa is not None:
            trend = _ratio_trend(first_roaa, roaa, higher_is_better=True)
            evo_parts.append(f"ROAA {trend} from {_pct(first_roaa)} to {_pct(roaa)}")
        if evo_parts:
            e_bullets.append(
                f"Over the review period ({first_yr}–{last_yr}), {' and '.join(evo_parts)}."
            )
        # Net income CAGR
        first_ni = getattr(first_bank, 'net_income', None)
        if first_ni is not None and ni is not None and first_ni > 0 and ni > 0:
            cagr = _cagr(first_ni, ni, n_years)
            if cagr is not None:
                e_bullets.append(f"Net income grew at a CAGR of {_pct(cagr)} over the period.")
    if not e_bullets:
        e_bullets.append("Insufficient data to assess earnings for this period.")
    paragraphs["earnings"] = e_bullets
    bank.analysis_earnings = "\n".join(e_bullets)

    # --- L: Liquidity ---
    l_bullets = []
    la_ta = getattr(bank, 'liquid_assets_total_assets', None)
    ld = getattr(bank, 'gross_loans_deposits', None)
    deps = getattr(bank, 'deposits', None)

    if la_ta is not None:
        b = f"Liquid assets (cash, bank deposits, and investment securities) represent {_pct(la_ta)} of total assets. "
        if la_ta >= 0.30:
            b += "This comfortable buffer ensures the bank can meet short-term obligations and withstand deposit volatility."
        elif la_ta >= 0.15:
            b += "This is an adequate level, though a sudden deposit outflow could tighten the position."
        else:
            b += "This low level raises concerns about the bank's ability to handle stress scenarios."
        l_bullets.append(b)
    if ld is not None:
        b = f"The Loans-to-Deposits ratio is {_pct(ld)}"
        if deps is not None:
            b += f" (deposits of {ccy} {_fmt_abs(deps)})"
        if ld > 0.90:
            b += ". This high ratio suggests aggressive lending relative to the deposit base, increasing liquidity risk."
        elif ld > 0.75:
            b += ". The bank maintains a reasonable balance between lending and deposit funding."
        else:
            b += ". The bank has ample deposit funding relative to its loan book."
        l_bullets.append(b)
    # Evolution: Liquidity ratio trend
    if has_evo:
        first_la = getattr(first_bank, 'liquid_assets_total_assets', None)
        if first_la is not None and la_ta is not None:
            trend = _ratio_trend(first_la, la_ta, higher_is_better=True)
            l_bullets.append(
                f"The liquid-assets-to-total-assets ratio {trend} from "
                f"{_pct(first_la)} ({first_yr}) to {_pct(la_ta)} ({last_yr})."
            )
        first_ld = getattr(first_bank, 'gross_loans_deposits', None)
        if first_ld is not None and ld is not None:
            trend = _ratio_trend(first_ld, ld, higher_is_better=False)
            l_bullets.append(
                f"The loans-to-deposits ratio {trend} from "
                f"{_pct(first_ld)} ({first_yr}) to {_pct(ld)} ({last_yr})."
            )
    if not l_bullets:
        l_bullets.append("Insufficient data to assess liquidity for this period.")
    paragraphs["liquidity"] = l_bullets
    bank.analysis_liquidity = "\n".join(l_bullets)

    # --- Composite ---
    comp = ratings.get("composite", {})
    comp_r = comp.get("composite_rating")
    c_bullets_comp = []
    b = f"Based on the analysis of {name} for fiscal year {year}, "
    if comp_r and comp_r <= 2:
        b += "the bank exhibits a fundamentally sound financial condition across the key pillars. Continued vigilance is recommended to maintain this strong position."
    elif comp_r and comp_r <= 3:
        b += "the bank demonstrates an acceptable financial condition overall, but some areas require management attention to prevent further deterioration."
    elif comp_r and comp_r <= 4:
        b += "the bank displays material weaknesses in several areas that, if left unaddressed, could impair its financial viability."
    elif comp_r and comp_r == 5:
        b += "the bank is in a critically weak condition. Immediate supervisory intervention is warranted."
    else:
        b += "insufficient data was available to draw a definitive conclusion."
    c_bullets_comp.append(b)
    # Evolution: key aggregates summary
    if has_evo:
        first_ta = getattr(first_bank, 'total_assets', None)
        if first_ta is not None and ta is not None:
            cagr = _cagr(first_ta, ta, n_years)
            if cagr is not None:
                c_bullets_comp.append(
                    f"Total assets grew from {ccy} {_fmt_abs(first_ta)} ({first_yr}) to "
                    f"{ccy} {_fmt_abs(ta)} ({last_yr}), a CAGR of {_pct(cagr)}."
                )
        first_gl = getattr(first_bank, 'gross_loans', None)
        if first_gl is not None and gl is not None:
            cagr = _cagr(first_gl, gl, n_years)
            if cagr is not None:
                c_bullets_comp.append(
                    f"The gross loan book expanded from {ccy} {_fmt_abs(first_gl)} to "
                    f"{ccy} {_fmt_abs(gl)}, a CAGR of {_pct(cagr)}."
                )
        first_deps = getattr(first_bank, 'deposits', None)
        if first_deps is not None and deps is not None:
            cagr = _cagr(first_deps, deps, n_years)
            if cagr is not None:
                c_bullets_comp.append(
                    f"Customer deposits grew from {ccy} {_fmt_abs(first_deps)} to "
                    f"{ccy} {_fmt_abs(deps)}, a CAGR of {_pct(cagr)}."
                )
    paragraphs["composite"] = c_bullets_comp
    bank.analysis_composite = "\n".join(c_bullets_comp)

    return paragraphs
