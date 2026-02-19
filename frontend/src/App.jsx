import './App.css';
import { useAnalyzer } from './hooks/useAnalyzer';
import ErrorBoundary from './components/ErrorBoundary';
import StatementSelector from './components/FileUpload';
import LoadingSpinner from './components/LoadingSpinner';
import CompositeRating from './components/CompositeRating';
import CAMELSSection from './components/CAMELSSection';
import { BalanceSheet, IncomeStatement } from './components/FinancialStatement';
import MetricsGrid from './components/MetricsGrid';

function App() {
  const {
    companies, selectedCompany, statements, selectedStatement,
    loading, loadingCompanies, result, error,
    handleCompanyChange, handleStatementChange, handleAnalyze,
  } = useAnalyzer();

  const stmt = result?.statement;
  const ratings = result?.ratings;
  const analysis = result?.analysis;
  const km = result?.key_metrics;

  return (
    <ErrorBoundary>
      <div className="App">
        <h1>CAMELS Analyzer</h1>
        <p className="subtitle">Automated bank financial statement analysis</p>

        <StatementSelector
          companies={companies}
          selectedCompany={selectedCompany}
          statements={statements}
          selectedStatement={selectedStatement}
          loadingCompanies={loadingCompanies}
          loading={loading}
          onCompanyChange={handleCompanyChange}
          onStatementChange={handleStatementChange}
          onAnalyze={handleAnalyze}
        />

        {loading && <LoadingSpinner progress="Running CAMELS analysis..." />}
        {error && <div className="error">{error}</div>}

        {result && (
          <div className="result">
            <div className="bank-info">
              <h3>{result.bank_name || 'Unknown Bank'}</h3>
              <p>{result.country || ''} — Fiscal Year {result.fiscal_year || ''} — {result.currency || 'XOF'}</p>
            </div>

            <CompositeRating camelsRating={ratings?.composite} analysis={analysis} />

            <CAMELSSection
              letter="C"
              title="Capital Adequacy"
              headerClass="capital-header"
              rating={ratings?.capital}
              analysis={analysis?.capital}
              ratios={[
                { name: 'Equity / Assets', formula: "Shareholders' Equity / Total Assets", value: km?.equity_assets },
                { name: 'Debt / Assets', formula: '(Short-Term Borrowings + Long-Term Debt) / Total Assets', value: km?.debt_assets },
              ]}
            />

            <CAMELSSection
              letter="A"
              title="Asset Quality"
              headerClass="asset-header"
              rating={ratings?.asset_quality}
              analysis={analysis?.asset_quality}
              ratios={[
                { name: 'NPL Ratio', formula: 'NPLs (Stage 3) / Gross Loans', value: km?.npl_ratio },
                { name: 'Coverage Ratio', formula: 'Loan Loss Provisions (ECL) / NPLs', value: km?.coverage_ratio },
                { name: 'Cost of Risk / Avg Assets', formula: 'ECL / Average Total Assets', value: km?.cost_of_risk_avg_assets },
              ]}
            />

            <CAMELSSection
              letter="M"
              title="Management (Efficiency)"
              headerClass="management-header"
              rating={ratings?.management}
              analysis={analysis?.management}
              ratios={[
                { name: 'Cost-to-Income Ratio', formula: 'Operating Expenses / Operating Income', value: km?.cost_to_income },
              ]}
            />

            <CAMELSSection
              letter="E"
              title="Earnings"
              headerClass="earnings-header"
              rating={ratings?.earnings}
              analysis={analysis?.earnings}
              ratios={[
                { name: 'ROAA', formula: 'Net Profit / Average Total Assets', value: km?.roaa },
                { name: 'ROAE', formula: "Net Profit / Average Shareholders' Equity", value: km?.roae },
                { name: 'Net Interest Income / Avg Assets', formula: 'Net Interest Income / Avg Total Assets', value: result?.ratios?.net_interest_income_avg_assets },
                { name: 'Non-Interest Income / Avg Assets', formula: '(Fees & Commissions + ...) / Avg Total Assets', value: result?.ratios?.non_interest_income_avg_assets },
                { name: 'Operating Expenses / Avg Assets', formula: '(Wages + Other OpEx + ...) / Avg Total Assets', value: result?.ratios?.opex_avg_assets },
                { name: 'Tax Expenses / Avg Assets', formula: 'Tax Expenses / Avg Total Assets', value: result?.ratios?.tax_expenses_avg_assets },
                { name: 'Other Income / Avg Assets', formula: '(Provisions Formed + Impairment + FX) / Avg Total Assets', value: result?.ratios?.other_income_avg_assets },
              ]}
            />

            <CAMELSSection
              letter="L"
              title="Liquidity"
              headerClass="liquidity-header"
              rating={ratings?.liquidity}
              analysis={analysis?.liquidity}
              ratios={[
                { name: 'Liquid Assets / Total Assets', formula: '(Cash & Deposits with Banks + Investment Securities) / Total Assets', value: km?.liquid_assets_total_assets },
              ]}
            />

            <BalanceSheet bank={stmt} />
            <IncomeStatement bank={stmt} />
            <MetricsGrid metrics={km} />
          </div>
        )}
      </div>
    </ErrorBoundary>
  );
}

export default App;
