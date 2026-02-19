import './App.css';
import { useAnalyzer } from './hooks/useAnalyzer';
import ErrorBoundary from './components/ErrorBoundary';
import StatementSelector from './components/FileUpload';
import LoadingSpinner from './components/LoadingSpinner';
import CompositeRating from './components/CompositeRating';
import CAMELSSection from './components/CAMELSSection';
import MetricsGrid from './components/MetricsGrid';

function App() {
  const {
    companies, selectedCompany, periods, selectedPeriod,
    loading, loadingCompanies, result, error,
    handleCompanyChange, handlePeriodChange, handleAnalyze,
  } = useAnalyzer();

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
          periods={periods}
          selectedPeriod={selectedPeriod}
          loadingCompanies={loadingCompanies}
          loading={loading}
          onCompanyChange={handleCompanyChange}
          onPeriodChange={handlePeriodChange}
          onAnalyze={handleAnalyze}
        />

        {loading && <LoadingSpinner progress="Running CAMELS analysis..." />}
        {error && <div className="error">{error}</div>}

        {result && (
          <div className="result">
            <div className="bank-info">
              <h3>{result.company_name || 'Unknown'}</h3>
              <p>{result.type_institution || ''} — Period {result.period || ''} — {result.currency || 'XOF'}</p>
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
                { name: 'NPL Ratio', formula: 'NPLs / Gross Loans', value: km?.npl_ratio },
                { name: 'Coverage Ratio', formula: 'Loan Loss Provisions / NPLs', value: km?.coverage_ratio },
                { name: 'Cost of Risk / Avg Assets', formula: 'Provision Expense / Average Total Assets', value: km?.cost_of_risk_avg_assets },
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
                { name: 'ROAA', formula: 'Net Income / Average Total Assets', value: km?.roaa },
                { name: 'ROAE', formula: "Net Income / Average Shareholders' Equity", value: km?.roae },
                { name: 'Net Interest Income / Avg Assets', formula: 'Net Interest Income / Avg Total Assets', value: result?.ratios?.net_interest_income_avg_assets },
                { name: 'Non-Interest Income / Avg Assets', formula: '(Fees & Commissions + ...) / Avg Total Assets', value: result?.ratios?.non_interest_income_avg_assets },
                { name: 'Operating Expenses / Avg Assets', formula: 'Operating Expenses / Avg Total Assets', value: result?.ratios?.opex_avg_assets },
                { name: 'Tax Expenses / Avg Assets', formula: 'Tax Expenses / Avg Total Assets', value: result?.ratios?.tax_expenses_avg_assets },
              ]}
            />

            <CAMELSSection
              letter="L"
              title="Liquidity"
              headerClass="liquidity-header"
              rating={ratings?.liquidity}
              analysis={analysis?.liquidity}
              ratios={[
                { name: 'Liquid Assets / Total Assets', formula: '(Cash + Due from Banks + Investment Securities) / Total Assets', value: km?.liquid_assets_total_assets },
                { name: 'Gross Loans / Deposits', formula: 'Gross Loans / Total Deposits', value: km?.gross_loans_deposits },
              ]}
            />

            <MetricsGrid metrics={km} />
          </div>
        )}
      </div>
    </ErrorBoundary>
  );
}

export default App;
