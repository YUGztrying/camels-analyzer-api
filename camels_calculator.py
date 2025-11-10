"""
CAMELS Calculator - Calcule automatiquement tous les ratios bancaires
Compatible avec les objets SQLAlchemy BankDB
"""

def calculate_all_ratios(bank, prev_bank=None):
    """
    Calcule TOUS les ratios CAMELS et met à jour l'objet bank directement
    
    Args:
        bank: Objet BankDB (SQLAlchemy)
        prev_bank: Objet BankDB de la période précédente (optionnel)
    
    Returns:
        L'objet bank avec tous les ratios calculés
    """
    
    # Fonction helper pour récupérer les valeurs
    def get_val(obj, attr, default=0):
        val = getattr(obj, attr, None)
        return val if val is not None else default
    
    # Calcul des moyennes
    avg_assets = _calculate_average(get_val(bank, 'total_assets'), 
                                     get_val(prev_bank, 'total_assets') if prev_bank else None)
    avg_equity = _calculate_average(get_val(bank, 'total_equity'), 
                                     get_val(prev_bank, 'total_equity') if prev_bank else None)
    avg_gross_loans = _calculate_average(get_val(bank, 'gross_loans'), 
                                         get_val(prev_bank, 'gross_loans') if prev_bank else None)
    
    # ========== SOLVENCY RATIOS ==========
    bank.equity_assets = _safe_divide(get_val(bank, 'total_equity'), 
                                      get_val(bank, 'total_assets'))
    
    # ========== LIQUIDITY RATIOS ==========
    bank.cash_reserves_assets = _safe_divide(get_val(bank, 'cash_reserves_requirements'), 
                                             get_val(bank, 'total_assets'))
    
    liquid_assets = sum([
        get_val(bank, 'cash_reserves_requirements'),
        get_val(bank, 'due_from_banks'),
        get_val(bank, 'investment_securities')
    ])
    bank.liquid_assets_assets = _safe_divide(liquid_assets, get_val(bank, 'total_assets'))
    
    bank.gross_loans_deposits = _safe_divide(get_val(bank, 'gross_loans'), 
                                             get_val(bank, 'deposits'))
    
    # ========== ASSET QUALITY ==========
    npls = get_val(bank, 'npls_mn')
    foreclosed_assets = get_val(bank, 'foreclosed_assets')
    problem_assets = npls + foreclosed_assets
    
    bank.problem_assets_mn = problem_assets
    
    # LLR (Loan Loss Reserves)
    llr = get_val(bank, 'llr_mn')
    if llr == 0 and get_val(bank, 'loan_loss_provisions') != 0:
        llr = -get_val(bank, 'loan_loss_provisions')
    
    # NPA Ratio = Problem Assets / (Gross Loans + Foreclosed Assets)
    npa_denominator = get_val(bank, 'gross_loans') + foreclosed_assets
    bank.npa_ratio = _safe_divide(problem_assets, npa_denominator)
    
    # NPL Ratio = NPLs / Gross Loans
    bank.npl_ratio = _safe_divide(npls, get_val(bank, 'gross_loans'))
    
    # LLR / Average Loan
    bank.llr_avg_loan = _safe_divide(llr, avg_gross_loans)
    
    # Coverage Ratio = LLR / NPLs
    bank.coverage_ratio = _safe_divide(llr, npls) if npls > 0 else None
    
    # OLER = (Problem Assets - LLR) / Equity
    bank.oler = _safe_divide(problem_assets - llr, get_val(bank, 'total_equity'))
    
    # ========== PROFITABILITY RATIOS ==========
    
    # Net Interest Margin = Net Interest Income / Avg Assets
    bank.net_interest_margin = _safe_divide(get_val(bank, 'net_interest_income'), avg_assets)
    
    # Net Interest Spread = Yield on Assets - Cost of Liabilities
    yield_on_assets = _safe_divide(get_val(bank, 'interest_income'), 
                                    get_val(bank, 'total_assets'))
    cost_of_liabilities = _safe_divide(get_val(bank, 'interest_expenses'), 
                                        get_val(bank, 'total_liabilities'))
    bank.net_interest_spread = (yield_on_assets or 0) - (cost_of_liabilities or 0)
    
    # Non-Interest Income
    non_interest_income = sum([
        get_val(bank, 'non_net_interest_income_commissions'),
        get_val(bank, 'net_income_from_investment'),
        get_val(bank, 'other_net_income')
    ])
    
    bank.non_interest_income_assets = _safe_divide(non_interest_income, avg_assets)
    
    # Interest Earning Assets Yield
    interest_earning_assets = get_val(bank, 'gross_loans') + get_val(bank, 'investment_securities')
    bank.interest_earning_assets_yield = _safe_divide(get_val(bank, 'interest_income'), 
                                                       interest_earning_assets)
    
    # Cost of Funds
    bank.cost_of_funds = _safe_divide(get_val(bank, 'interest_expenses'), 
                                       get_val(bank, 'total_liabilities'))
    
    # Opex / Avg Assets
    bank.opex_assets = _safe_divide(get_val(bank, 'operating_expenses'), avg_assets)
    
    # Cost to Income Ratio
    total_income = get_val(bank, 'net_interest_income') + non_interest_income
    bank.cost_to_income = _safe_divide(get_val(bank, 'operating_expenses'), total_income)
    
    # ========== DUPONT ANALYSIS ==========
    
    # (a) Net Interest Income / Avg Assets
    bank.net_interest_income_assets = _safe_divide(get_val(bank, 'net_interest_income'), avg_assets)
    
    # (b) Non Interest Income / Avg Assets
    bank.non_interest_income_assets_dupont = _safe_divide(non_interest_income, avg_assets)
    
    # (c) OPEX / Avg Assets
    bank.opex_assets_dupont = _safe_divide(get_val(bank, 'operating_expenses'), avg_assets)
    
    # (d) Provision Expenses / Avg Assets
    bank.provision_expenses_assets = _safe_divide(get_val(bank, 'provision_expenses'), avg_assets)
    
    # (e) Non Operating Profit (Loss) / Avg Assets
    bank.non_op_assets = _safe_divide(get_val(bank, 'non_operating_profit_loss'), avg_assets)
    
    # (f) Tax Expenses / Avg Assets
    bank.tax_expenses_assets = _safe_divide(get_val(bank, 'income_tax'), avg_assets)
    
    # (g) Avg Assets / Avg Equity
    bank.assets_equity = _safe_divide(avg_assets, avg_equity)
    
    # ROAA = a + b - c - d + e - f
    roaa = sum([
        bank.net_interest_income_assets or 0,
        bank.non_interest_income_assets_dupont or 0,
        -(bank.opex_assets_dupont or 0),
        -(bank.provision_expenses_assets or 0),
        bank.non_op_assets or 0,
        -(bank.tax_expenses_assets or 0)
    ])
    bank.roaa = roaa
    
    # ROAE = ROAA × (Assets / Equity)
    bank.roae = roaa * (bank.assets_equity or 0)
    
    return bank


def _calculate_average(current_value, previous_value=None):
    """Calcule la moyenne entre la valeur actuelle et précédente"""
    if previous_value is not None and previous_value != 0:
        return (current_value + previous_value) / 2 if current_value else previous_value / 2
    return current_value if current_value else 0


def _safe_divide(numerator, denominator):
    """Division sécurisée qui retourne None si dénominateur est 0"""
    if denominator is None or denominator == 0:
        return None
    if numerator is None or numerator == 0:
        return None
    return numerator / denominator


# ========== RATINGS (CAMELS 1-5) ==========

def rate_capital(bank):
    """Rating Capital Adequacy (C)"""
    car = getattr(bank, 'car_regulatory', None)
    
    if car is None:
        return {"rating": None, "status": "Insufficient data"}
    
    if car >= 15:
        return {"rating": 1, "status": "Strong", "car": car}
    elif car >= 12:
        return {"rating": 2, "status": "Satisfactory", "car": car}
    elif car >= 10:
        return {"rating": 3, "status": "Fair", "car": car}
    elif car >= 8:
        return {"rating": 4, "status": "Marginal", "car": car}
    else:
        return {"rating": 5, "status": "Unsatisfactory", "car": car}


def rate_asset_quality(bank):
    """Rating Asset Quality (A)"""
    npl_ratio = getattr(bank, 'npl_ratio', None)
    
    if npl_ratio is None:
        return {"rating": None, "status": "Insufficient data"}
    
    if npl_ratio < 0.02:  # < 2%
        return {"rating": 1, "status": "Strong", "npl_ratio": npl_ratio}
    elif npl_ratio < 0.05:  # < 5%
        return {"rating": 2, "status": "Satisfactory", "npl_ratio": npl_ratio}
    elif npl_ratio < 0.08:  # < 8%
        return {"rating": 3, "status": "Fair", "npl_ratio": npl_ratio}
    elif npl_ratio < 0.12:  # < 12%
        return {"rating": 4, "status": "Marginal", "npl_ratio": npl_ratio}
    else:
        return {"rating": 5, "status": "Unsatisfactory", "npl_ratio": npl_ratio}


def rate_earnings(bank):
    """Rating Earnings (E)"""
    roae = getattr(bank, 'roae', None)
    
    if roae is None:
        return {"rating": None, "status": "Insufficient data"}
    
    if roae >= 0.15:  # >= 15%
        return {"rating": 1, "status": "Strong", "roae": roae}
    elif roae >= 0.10:  # >= 10%
        return {"rating": 2, "status": "Satisfactory", "roae": roae}
    elif roae >= 0.05:  # >= 5%
        return {"rating": 3, "status": "Fair", "roae": roae}
    elif roae >= 0:
        return {"rating": 4, "status": "Marginal", "roae": roae}
    else:
        return {"rating": 5, "status": "Unsatisfactory", "roae": roae}


def rate_liquidity(bank):
    """Rating Liquidity (L)"""
    loans_deposits = getattr(bank, 'gross_loans_deposits', None)
    
    if loans_deposits is None:
        return {"rating": None, "status": "Insufficient data"}
    
    if loans_deposits < 0.70:  # < 70%
        return {"rating": 1, "status": "Strong", "ratio": loans_deposits}
    elif loans_deposits < 0.85:  # < 85%
        return {"rating": 2, "status": "Satisfactory", "ratio": loans_deposits}
    elif loans_deposits < 0.95:  # < 95%
        return {"rating": 3, "status": "Fair", "ratio": loans_deposits}
    elif loans_deposits < 1.05:  # < 105%
        return {"rating": 4, "status": "Marginal", "ratio": loans_deposits}
    else:
        return {"rating": 5, "status": "Unsatisfactory", "ratio": loans_deposits}


def get_composite_rating(capital_rating, asset_rating, earnings_rating, liquidity_rating):
    """Calcule le rating CAMELS composite"""
    valid_ratings = []
    
    if capital_rating and capital_rating.get("rating"):
        valid_ratings.append(capital_rating["rating"])
    if asset_rating and asset_rating.get("rating"):
        valid_ratings.append(asset_rating["rating"])
    if earnings_rating and earnings_rating.get("rating"):
        valid_ratings.append(earnings_rating["rating"])
    if liquidity_rating and liquidity_rating.get("rating"):
        valid_ratings.append(liquidity_rating["rating"])
    
    if not valid_ratings:
        return {"composite_rating": None, "status": "Insufficient data"}
    
    avg = sum(valid_ratings) / len(valid_ratings)
    composite = round(avg)
    
    status_map = {
        1: "Strong",
        2: "Satisfactory",
        3: "Fair",
        4: "Marginal",
        5: "Unsatisfactory"
    }
    
    return {
        "composite_rating": composite,
        "status": status_map.get(composite, "Unknown")
    }
