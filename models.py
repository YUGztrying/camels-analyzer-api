from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text
from sqlalchemy.sql import func
from database import Base


class BankDB(Base):
    """
    Modèle SQLAlchemy COMPLET pour l'analyse CAMELS.
    Basé sur ton app Base44 avec ~50 champs financiers.
    """
    __tablename__ = "banks"
    
    # === IDENTIFIANTS ===
    id = Column(Integer, primary_key=True, index=True)
    
    # === INFORMATIONS GÉNÉRALES ===
    bank_name = Column(String, nullable=False, index=True)
    country = Column(String, nullable=False)
    fiscal_year = Column(String, nullable=False)
    period_end_date = Column(DateTime)
    currency = Column(String, default="XOF")
    file_urls = Column(Text)  # URLs séparées par virgules
    
    # === TAUX DE CHANGE ===
    fx_rate_period_end = Column(Float)
    fx_rate_period_avg = Column(Float)
    
    # === BILAN - ACTIFS (Balance Sheet - Assets) ===
    cash_reserves_requirements = Column(Float)
    due_from_banks = Column(Float)
    investment_securities = Column(Float)
    gross_loans = Column(Float)
    loan_loss_provisions = Column(Float)
    foreclosed_assets = Column(Float)
    investment_in_subs_affiliates = Column(Float)
    other_assets = Column(Float)
    fixed_assets = Column(Float)
    total_assets = Column(Float, nullable=False)  # OBLIGATOIRE
    
    # === BILAN - PASSIFS (Balance Sheet - Liabilities) ===
    deposits = Column(Float)
    interbank_liabilities = Column(Float)
    other_liabilities = Column(Float)
    total_liabilities = Column(Float)
    
    # === BILAN - CAPITAUX PROPRES (Balance Sheet - Equity) ===
    paid_in_capital = Column(Float)
    reserves = Column(Float)
    retained_earnings = Column(Float)
    net_profit = Column(Float)
    total_equity = Column(Float)
    
    # === COMPTE DE RÉSULTAT (Income Statement) ===
    interest_income = Column(Float)
    interest_expenses = Column(Float)
    net_interest_income = Column(Float)
    non_interest_income_commissions = Column(Float)
    net_income_investment = Column(Float)
    other_net_income = Column(Float)
    operating_expenses = Column(Float)
    operating_profit = Column(Float)
    provision_expenses = Column(Float)
    non_operating_profit_loss = Column(Float)
    income_tax = Column(Float)
    net_income = Column(Float)
    
    # === RATIOS CAMELS - CAPITAL ADEQUACY ===
    car_regulatory = Column(Float)  # CAR réglementaire
    car_bank_reported = Column(Float)  # CAR reporté par la banque
    equity_assets = Column(Float)  # Equity / Assets
    
    # === RATIOS CAMELS - ASSET QUALITY ===
    problem_assets_mn = Column(Float)  # Actifs problématiques (millions)
    npls_mn = Column(Float)  # Non-Performing Loans (millions)
    llr_mn = Column(Float)  # Loan Loss Reserves (millions)
    npa_ratio = Column(Float)  # NPA / Total Assets
    npl_ratio = Column(Float)  # NPLs / Gross Loans
    llr_avg_loan = Column(Float)  # LLR / Gross Loans
    coverage_ratio = Column(Float)  # LLR / NPLs
    oler = Column(Float)  # Other Liabilities / Equity
    
    # === RATIOS CAMELS - EARNINGS (Profitability) ===
    net_interest_margin = Column(Float)
    net_interest_spread = Column(Float)
    non_interest_income_assets = Column(Float)
    interest_earning_assets_yield = Column(Float)
    cost_of_funds = Column(Float)
    opex_assets = Column(Float)
    cost_to_income = Column(Float)
    
    # === RATIOS CAMELS - LIQUIDITY ===
    cash_reserves_assets = Column(Float)
    liquid_assets_assets = Column(Float)
    gross_loans_deposits = Column(Float)
    
    # === DUPONT ANALYSIS ===
    net_interest_income_assets = Column(Float)
    non_interest_income_assets_dupont = Column(Float)
    opex_assets_dupont = Column(Float)
    provision_expenses_assets = Column(Float)
    non_op_assets = Column(Float)
    tax_expenses_assets = Column(Float)
    assets_equity = Column(Float)  # Leverage multiplier
    roae = Column(Float)  # Return on Average Equity
    roaa = Column(Float)  # Return on Average Assets
    
    # === MÉTADONNÉES ===
    analysis_complete = Column(Boolean, default=False)
    created_date = Column(DateTime, server_default=func.now())
    updated_date = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Bank {self.bank_name} - {self.fiscal_year}>"