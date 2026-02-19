-- =============================================================================
-- CAMELS Analyzer — Supabase Schema
-- Shared between the Spreading App (writes financial data) and the CAMELS App
-- (reads financial data, writes analyses).
-- =============================================================================

-- --------------------------------------------------------
-- 1. COMPANIES
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS companies (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    country     TEXT NOT NULL,
    entity_type TEXT NOT NULL DEFAULT 'bank',  -- 'bank' | 'mfi'
    created_at  TIMESTAMPTZ DEFAULT now(),
    updated_at  TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_companies_user ON companies(user_id);

-- --------------------------------------------------------
-- 2. FINANCIAL STATEMENTS
-- Written by the Spreading App after LLM extraction + IFC normalization.
-- Read by the CAMELS App to compute ratings.
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS financial_statements (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id  UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    user_id     UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    fiscal_year TEXT NOT NULL,
    statement_type TEXT DEFAULT 'annual',  -- 'annual' | 'interim'
    currency    TEXT DEFAULT 'XOF',

    -- Balance Sheet — Assets
    cash_reserves_requirements   FLOAT8,
    due_from_banks               FLOAT8,
    investment_securities        FLOAT8,
    gross_loans                  FLOAT8,
    loan_loss_provisions         FLOAT8,
    foreclosed_assets            FLOAT8,
    investment_in_subs_affiliates FLOAT8,
    other_assets                 FLOAT8,
    fixed_assets                 FLOAT8,
    total_assets                 FLOAT8 NOT NULL,

    -- Balance Sheet — Liabilities
    deposits              FLOAT8,
    short_term_borrowings FLOAT8,
    long_term_debt        FLOAT8,
    interbank_liabilities FLOAT8,
    other_liabilities     FLOAT8,
    total_liabilities     FLOAT8,

    -- Balance Sheet — Equity
    paid_in_capital   FLOAT8,
    reserves          FLOAT8,
    retained_earnings FLOAT8,
    net_profit        FLOAT8,
    total_equity      FLOAT8,

    -- Income Statement
    interest_income    FLOAT8,
    interest_expenses  FLOAT8,
    net_interest_income FLOAT8,

    -- Non-interest income breakdown
    fees_commissions                FLOAT8,
    net_sales                       FLOAT8,
    dividends                       FLOAT8,
    fvtpl_changes                   FLOAT8,
    securitization_gains            FLOAT8,
    provisions_no_longer_required   FLOAT8,
    share_profit_associates         FLOAT8,
    other_revenues                  FLOAT8,
    gain_acquisition_subsidiaries   FLOAT8,
    non_interest_income_commissions FLOAT8,
    net_income_investment           FLOAT8,
    other_net_income                FLOAT8,

    -- Operating expenses breakdown
    wages_salaries          FLOAT8,
    other_opex              FLOAT8,
    intangible_amortization FLOAT8,
    fixed_asset_depreciation FLOAT8,
    operating_expenses      FLOAT8,
    operating_income        FLOAT8,
    operating_profit        FLOAT8,

    -- Other P&L
    provision_expenses          FLOAT8,
    provisions_formed           FLOAT8,
    impairment_financial_assets FLOAT8,
    fx_exchange                 FLOAT8,
    non_operating_profit_loss   FLOAT8,
    income_tax                  FLOAT8,
    net_income                  FLOAT8,

    -- Prudential ratios (as reported in the document)
    npls_mn            FLOAT8,
    llr_mn             FLOAT8,
    car_regulatory     FLOAT8,
    car_bank_reported  FLOAT8,

    -- FX rates
    fx_rate_period_end FLOAT8,
    fx_rate_period_avg FLOAT8,

    -- Source tracking
    source_file_url TEXT,

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),

    UNIQUE(company_id, fiscal_year, statement_type)
);

CREATE INDEX IF NOT EXISTS idx_statements_company ON financial_statements(company_id);
CREATE INDEX IF NOT EXISTS idx_statements_user    ON financial_statements(user_id);

-- --------------------------------------------------------
-- 3. CAMELS ANALYSES
-- Written and read by the CAMELS App.
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS camels_analyses (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    statement_id UUID NOT NULL REFERENCES financial_statements(id) ON DELETE CASCADE UNIQUE,
    company_id   UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    user_id      UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Computed ratios — Capital
    equity_assets FLOAT8,
    debt_assets   FLOAT8,

    -- Computed ratios — Asset Quality
    npl_ratio              FLOAT8,
    npa_ratio              FLOAT8,
    coverage_ratio         FLOAT8,
    cost_of_risk_avg_assets FLOAT8,
    problem_assets_mn      FLOAT8,
    llr_avg_loan           FLOAT8,
    oler                   FLOAT8,

    -- Computed ratios — Management
    cost_to_income FLOAT8,

    -- Computed ratios — Earnings
    roaa                          FLOAT8,
    roae                          FLOAT8,
    net_interest_income_avg_assets FLOAT8,
    non_interest_income_avg_assets FLOAT8,
    opex_avg_assets               FLOAT8,
    tax_expenses_avg_assets       FLOAT8,
    other_income_avg_assets       FLOAT8,
    net_interest_margin           FLOAT8,
    net_interest_spread           FLOAT8,
    interest_earning_assets_yield FLOAT8,
    cost_of_funds                 FLOAT8,
    assets_equity                 FLOAT8,

    -- Computed ratios — Liquidity
    liquid_assets_total_assets FLOAT8,
    gross_loans_deposits       FLOAT8,
    cash_reserves_assets       FLOAT8,

    -- Ratings (JSONB with rating, status, ratios)
    capital_rating       JSONB,
    asset_quality_rating JSONB,
    management_rating    JSONB,
    earnings_rating      JSONB,
    liquidity_rating     JSONB,
    composite_rating     JSONB,

    -- Analysis paragraphs
    analysis_capital       TEXT,
    analysis_asset_quality TEXT,
    analysis_management    TEXT,
    analysis_earnings      TEXT,
    analysis_liquidity     TEXT,
    analysis_composite     TEXT,

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_analyses_statement ON camels_analyses(statement_id);
CREATE INDEX IF NOT EXISTS idx_analyses_company   ON camels_analyses(company_id);
CREATE INDEX IF NOT EXISTS idx_analyses_user      ON camels_analyses(user_id);

-- --------------------------------------------------------
-- 4. ROW LEVEL SECURITY
-- --------------------------------------------------------
ALTER TABLE companies ENABLE ROW LEVEL SECURITY;
ALTER TABLE financial_statements ENABLE ROW LEVEL SECURITY;
ALTER TABLE camels_analyses ENABLE ROW LEVEL SECURITY;

-- Companies
CREATE POLICY "Users can view own companies"
    ON companies FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own companies"
    ON companies FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own companies"
    ON companies FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own companies"
    ON companies FOR DELETE USING (auth.uid() = user_id);

-- Financial statements
CREATE POLICY "Users can view own statements"
    ON financial_statements FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own statements"
    ON financial_statements FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own statements"
    ON financial_statements FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own statements"
    ON financial_statements FOR DELETE USING (auth.uid() = user_id);

-- CAMELS analyses
CREATE POLICY "Users can view own analyses"
    ON camels_analyses FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own analyses"
    ON camels_analyses FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own analyses"
    ON camels_analyses FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own analyses"
    ON camels_analyses FOR DELETE USING (auth.uid() = user_id);

-- --------------------------------------------------------
-- 5. AUTO-UPDATE updated_at TRIGGER
-- --------------------------------------------------------
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER companies_updated_at
    BEFORE UPDATE ON companies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER statements_updated_at
    BEFORE UPDATE ON financial_statements
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER analyses_updated_at
    BEFORE UPDATE ON camels_analyses
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
