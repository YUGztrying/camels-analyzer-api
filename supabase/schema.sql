-- =============================================================================
-- CAMELS Analyzer — Supabase Schema
-- Only the camels_analyses table is created by this app.
-- The financial_statements table already exists (created by the Spreading App).
-- Both apps share the same Supabase project.
-- =============================================================================

-- --------------------------------------------------------
-- CAMELS ANALYSES
-- Keyed by (user_id, company_name, period) to match
-- the Spreading App's data model (no companies table).
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS camels_analyses (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    company_name TEXT NOT NULL,
    period       TEXT NOT NULL,                -- ISO date, e.g. "2023-12-31"
    type_institution TEXT NOT NULL DEFAULT 'banque',  -- 'banque' | 'microfinance'

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
    updated_at TIMESTAMPTZ DEFAULT now(),

    -- One analysis per (user, company, period)
    UNIQUE(user_id, company_name, period)
);

CREATE INDEX IF NOT EXISTS idx_analyses_user      ON camels_analyses(user_id);
CREATE INDEX IF NOT EXISTS idx_analyses_company   ON camels_analyses(company_name);
CREATE INDEX IF NOT EXISTS idx_analyses_period    ON camels_analyses(period);

-- --------------------------------------------------------
-- ROW LEVEL SECURITY
-- --------------------------------------------------------
ALTER TABLE camels_analyses ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own analyses"
    ON camels_analyses FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own analyses"
    ON camels_analyses FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own analyses"
    ON camels_analyses FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own analyses"
    ON camels_analyses FOR DELETE USING (auth.uid() = user_id);

-- --------------------------------------------------------
-- AUTO-UPDATE updated_at TRIGGER
-- --------------------------------------------------------
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER analyses_updated_at
    BEFORE UPDATE ON camels_analyses
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
