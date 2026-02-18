from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text
from sqlalchemy.sql import func
from database import Base


class BankDB(Base):
    """
    SQLAlchemy model for CAMELS bank financial analysis.
    Supports the full CAMELS cheat sheet ratios and paragraph analysis.
    """
    __tablename__ = "banks"

    # === IDENTIFIERS ===
    id = Column(Integer, primary_key=True, index=True)

    # === GENERAL INFO ===
    bank_name = Column(String, nullable=False, index=True)
    country = Column(String, nullable=False)
    fiscal_year = Column(String, default="N/A")
    period_end_date = Column(DateTime)
    currency = Column(String, default="XOF")
    file_urls = Column(Text)

    # === FX RATES ===
    fx_rate_period_end = Column(Float)
    fx_rate_period_avg = Column(Float)

    # === BALANCE SHEET - ASSETS ===
    cash_reserves_requirements = Column(Float)
    due_from_banks = Column(Float)
    investment_securities = Column(Float)
    gross_loans = Column(Float)
    loan_loss_provisions = Column(Float)
    foreclosed_assets = Column(Float)
    investment_in_subs_affiliates = Column(Float)
    other_assets = Column(Float)
    fixed_assets = Column(Float)
    total_assets = Column(Float, nullable=False)

    # === BALANCE SHEET - LIABILITIES ===
    deposits = Column(Float)
    short_term_borrowings = Column(Float)
    long_term_debt = Column(Float)
    interbank_liabilities = Column(Float)
    other_liabilities = Column(Float)
    total_liabilities = Column(Float)

    # === BALANCE SHEET - EQUITY ===
    paid_in_capital = Column(Float)
    reserves = Column(Float)
    retained_earnings = Column(Float)
    net_profit = Column(Float)
    total_equity = Column(Float)

    # === INCOME STATEMENT ===
    interest_income = Column(Float)
    interest_expenses = Column(Float)
    net_interest_income = Column(Float)
    # Non-interest income breakdown
    fees_commissions = Column(Float)
    net_sales = Column(Float)
    dividends = Column(Float)
    fvtpl_changes = Column(Float)
    securitization_gains = Column(Float)
    provisions_no_longer_required = Column(Float)
    share_profit_associates = Column(Float)
    other_revenues = Column(Float)
    gain_acquisition_subsidiaries = Column(Float)
    non_interest_income_commissions = Column(Float)  # legacy aggregate field
    net_income_investment = Column(Float)
    other_net_income = Column(Float)
    # Operating expenses breakdown
    wages_salaries = Column(Float)
    other_opex = Column(Float)
    intangible_amortization = Column(Float)
    fixed_asset_depreciation = Column(Float)
    operating_expenses = Column(Float)  # aggregate
    operating_income = Column(Float)
    operating_profit = Column(Float)
    # Other P&L
    provision_expenses = Column(Float)  # ECL / Expected Credit Losses
    provisions_formed = Column(Float)
    impairment_financial_assets = Column(Float)
    fx_exchange = Column(Float)
    non_operating_profit_loss = Column(Float)
    income_tax = Column(Float)
    net_income = Column(Float)

    # === RAW DATA FROM DOCUMENT ===
    npls_mn = Column(Float)
    llr_mn = Column(Float)
    car_regulatory = Column(Float)
    car_bank_reported = Column(Float)
    # Bank-reported ratios (used as fallback when calculated ratios are None)
    npl_ratio_reported = Column(Float)
    coverage_ratio_reported = Column(Float)
    roe_reported = Column(Float)
    roa_reported = Column(Float)
    cost_income_reported = Column(Float)

    # === CALCULATED RATIOS - C (Capital Adequacy) ===
    equity_assets = Column(Float)       # Equity / Assets
    debt_assets = Column(Float)         # Total Debt / Assets

    # === CALCULATED RATIOS - A (Asset Quality) ===
    problem_assets_mn = Column(Float)
    npl_ratio = Column(Float)           # NPLs / Gross Loans
    npa_ratio = Column(Float)
    coverage_ratio = Column(Float)      # LLP (ECL) / NPLs
    cost_of_risk_avg_assets = Column(Float)  # ECL / Avg Assets
    llr_avg_loan = Column(Float)
    oler = Column(Float)

    # === CALCULATED RATIOS - M (Management) ===
    cost_to_income = Column(Float)      # OpEx / Operating Income

    # === CALCULATED RATIOS - E (Earnings) ===
    roaa = Column(Float)
    roae = Column(Float)
    net_interest_income_avg_assets = Column(Float)
    non_interest_income_avg_assets = Column(Float)
    opex_avg_assets = Column(Float)
    tax_expenses_avg_assets = Column(Float)
    other_income_avg_assets = Column(Float)
    # Legacy / DuPont fields kept for backward compat
    net_interest_margin = Column(Float)
    net_interest_spread = Column(Float)
    non_interest_income_assets = Column(Float)
    interest_earning_assets_yield = Column(Float)
    cost_of_funds = Column(Float)
    opex_assets = Column(Float)
    net_interest_income_assets = Column(Float)
    non_interest_income_assets_dupont = Column(Float)
    opex_assets_dupont = Column(Float)
    provision_expenses_assets = Column(Float)
    non_op_assets = Column(Float)
    tax_expenses_assets = Column(Float)
    assets_equity = Column(Float)
    cash_reserves_assets = Column(Float)

    # === CALCULATED RATIOS - L (Liquidity) ===
    liquid_assets_total_assets = Column(Float)  # (Cash + Investment Securities) / Total Assets
    liquid_assets_assets = Column(Float)  # legacy
    gross_loans_deposits = Column(Float)

    # === CAMELS ANALYSIS PARAGRAPHS ===
    analysis_capital = Column(Text)
    analysis_asset_quality = Column(Text)
    analysis_management = Column(Text)
    analysis_earnings = Column(Text)
    analysis_liquidity = Column(Text)
    analysis_composite = Column(Text)

    # === METADATA ===
    analysis_complete = Column(Boolean, default=False)
    created_date = Column(DateTime, server_default=func.now())
    updated_date = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Bank {self.bank_name} - {self.fiscal_year}>"
