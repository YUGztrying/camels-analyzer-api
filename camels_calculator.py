# camels_calculator.py
"""
Calculateur de ratios CAMELS et système de notation.
Basé sur les standards internationaux de supervision bancaire.
"""

def calculate_all_ratios(bank):
    """
    Calcule TOUS les ratios CAMELS à partir des données brutes.
    Met à jour l'objet bank avec les ratios calculés.
    """
    
    # === CAPITAL ADEQUACY ===
    if bank.total_equity and bank.total_assets:
        bank.equity_assets = bank.total_equity / bank.total_assets
    
    # === ASSET QUALITY ===
    if bank.npls_mn and bank.gross_loans:
        bank.npl_ratio = bank.npls_mn / bank.gross_loans
    
    if bank.llr_mn and bank.gross_loans:
        bank.llr_avg_loan = bank.llr_mn / bank.gross_loans
    
    if bank.llr_mn and bank.npls_mn and bank.npls_mn > 0:
        bank.coverage_ratio = bank.llr_mn / bank.npls_mn
    
    if bank.problem_assets_mn and bank.total_assets:
        bank.npa_ratio = bank.problem_assets_mn / bank.total_assets
    
    if bank.other_liabilities and bank.total_equity and bank.total_equity > 0:
        bank.oler = bank.other_liabilities / bank.total_equity
    
    # === EARNINGS (PROFITABILITY) ===
    if bank.net_interest_income and bank.total_assets:
        bank.net_interest_margin = bank.net_interest_income / bank.total_assets
    
    if bank.interest_income and bank.interest_expenses and bank.total_assets and bank.total_liabilities:
        yield_on_assets = bank.interest_income / bank.total_assets
        cost_of_liabilities = bank.interest_expenses / bank.total_liabilities
        bank.net_interest_spread = yield_on_assets - cost_of_liabilities
    
    if bank.operating_expenses and bank.total_assets:
        bank.opex_assets = bank.operating_expenses / bank.total_assets
    
    # Cost to Income Ratio
    if bank.operating_expenses:
        total_income = (bank.net_interest_income or 0) + \
                      (bank.non_interest_income_commissions or 0) + \
                      (bank.net_income_investment or 0) + \
                      (bank.other_net_income or 0)
        if total_income > 0:
            bank.cost_to_income = bank.operating_expenses / total_income
    
    # === LIQUIDITY ===
    if bank.cash_reserves_requirements and bank.total_assets:
        bank.cash_reserves_assets = bank.cash_reserves_requirements / bank.total_assets
    
    if bank.gross_loans and bank.deposits and bank.deposits > 0:
        bank.gross_loans_deposits = bank.gross_loans / bank.deposits
    
    # === DUPONT ANALYSIS ===
    if bank.net_income and bank.total_assets:
        bank.roaa = bank.net_income / bank.total_assets  # Return on Assets
    
    if bank.net_income and bank.total_equity and bank.total_equity > 0:
        bank.roae = bank.net_income / bank.total_equity  # Return on Equity
    
    if bank.total_assets and bank.total_equity and bank.total_equity > 0:
        bank.assets_equity = bank.total_assets / bank.total_equity  # Leverage
    
    return bank


def rate_capital(bank):
    """
    Note le pilier CAPITAL (C de CAMELS).
    Rating: 1 (Strong) à 5 (Critical)
    """
    car = bank.car_regulatory or bank.car_bank_reported
    
    if not car:
        return {"rating": None, "status": "Insufficient data"}
    
    # Seuils réglementaires
    if car >= 12:
        return {"rating": 1, "status": "Strong", "car": car, "benchmark": "12%+"}
    elif car >= 10:
        return {"rating": 2, "status": "Satisfactory", "car": car, "benchmark": "10-12%"}
    elif car >= 8:
        return {"rating": 3, "status": "Fair", "car": car, "benchmark": "8-10%"}
    elif car >= 6:
        return {"rating": 4, "status": "Marginal", "car": car, "benchmark": "6-8%"}
    else:
        return {"rating": 5, "status": "Critical", "car": car, "benchmark": "<6%"}


def rate_asset_quality(bank):
    """
    Note le pilier ASSET QUALITY (A de CAMELS).
    """
    npl_ratio = bank.npl_ratio
    
    if not npl_ratio:
        return {"rating": None, "status": "Insufficient data"}
    
    # Seuils internationaux
    if npl_ratio <= 0.03:  # 3%
        return {"rating": 1, "status": "Strong", "npl_ratio": npl_ratio, "benchmark": "≤3%"}
    elif npl_ratio <= 0.05:  # 5%
        return {"rating": 2, "status": "Satisfactory", "npl_ratio": npl_ratio, "benchmark": "3-5%"}
    elif npl_ratio <= 0.08:  # 8%
        return {"rating": 3, "status": "Fair", "npl_ratio": npl_ratio, "benchmark": "5-8%"}
    elif npl_ratio <= 0.12:  # 12%
        return {"rating": 4, "status": "Marginal", "npl_ratio": npl_ratio, "benchmark": "8-12%"}
    else:
        return {"rating": 5, "status": "Critical", "npl_ratio": npl_ratio, "benchmark": ">12%"}


def rate_earnings(bank):
    """
    Note le pilier EARNINGS (E de CAMELS).
    """
    roae = bank.roae  # Return on Equity
    
    if not roae:
        return {"rating": None, "status": "Insufficient data"}
    
    # Seuils internationaux
    if roae >= 0.15:  # 15%+
        return {"rating": 1, "status": "Strong", "roae": roae, "benchmark": "≥15%"}
    elif roae >= 0.10:  # 10-15%
        return {"rating": 2, "status": "Satisfactory", "roae": roae, "benchmark": "10-15%"}
    elif roae >= 0.05:  # 5-10%
        return {"rating": 3, "status": "Fair", "roae": roae, "benchmark": "5-10%"}
    elif roae >= 0:  # 0-5%
        return {"rating": 4, "status": "Marginal", "roae": roae, "benchmark": "0-5%"}
    else:
        return {"rating": 5, "status": "Critical", "roae": roae, "benchmark": "<0%"}


def rate_liquidity(bank):
    """
    Note le pilier LIQUIDITY (L de CAMELS).
    """
    loans_deposits = bank.gross_loans_deposits
    
    if not loans_deposits:
        return {"rating": None, "status": "Insufficient data"}
    
    # Seuils : ratio prêts/dépôts optimal entre 70-90%
    if 0.70 <= loans_deposits <= 0.90:
        return {"rating": 1, "status": "Strong", "ratio": loans_deposits, "benchmark": "70-90%"}
    elif 0.60 <= loans_deposits < 0.70 or 0.90 < loans_deposits <= 1.0:
        return {"rating": 2, "status": "Satisfactory", "ratio": loans_deposits, "benchmark": "60-70% or 90-100%"}
    elif 0.50 <= loans_deposits < 0.60 or 1.0 < loans_deposits <= 1.10:
        return {"rating": 3, "status": "Fair", "ratio": loans_deposits, "benchmark": "50-60% or 100-110%"}
    elif 0.40 <= loans_deposits < 0.50 or 1.10 < loans_deposits <= 1.20:
        return {"rating": 4, "status": "Marginal", "ratio": loans_deposits, "benchmark": "40-50% or 110-120%"}
    else:
        return {"rating": 5, "status": "Critical", "ratio": loans_deposits, "benchmark": "<40% or >120%"}


def get_composite_rating(ratings):
    """
    Calcule le rating CAMELS composite (moyenne pondérée).
    C et A ont plus de poids car plus critiques.
    """
    weights = {
        'capital': 0.25,
        'asset_quality': 0.25,
        'management': 0.15,  # Pas calculé automatiquement
        'earnings': 0.20,
        'liquidity': 0.15
    }
    
    # Calculer la moyenne pondérée
    total_weight = 0
    weighted_sum = 0
    
    for key, weight in weights.items():
        rating_obj = ratings.get(key)
        if rating_obj and rating_obj.get('rating'):
            weighted_sum += rating_obj['rating'] * weight
            total_weight += weight
    
    if total_weight == 0:
        return None
    
    composite = weighted_sum / total_weight
    
    # Arrondir au rating le plus proche
    final_rating = round(composite)
    
    status_map = {
        1: "Strong",
        2: "Satisfactory",
        3: "Fair",
        4: "Marginal",
        5: "Critical"
    }
    
    return {
        "composite_rating": final_rating,
        "status": status_map.get(final_rating, "Unknown"),
        "score": round(composite, 2)
    }