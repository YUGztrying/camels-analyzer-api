import './App.css';
import { useAnalyzer } from './hooks/useAnalyzer';
import ErrorBoundary from './components/ErrorBoundary';
import FileUpload from './components/FileUpload';
import LoadingSpinner from './components/LoadingSpinner';
import CompositeRating from './components/CompositeRating';
import CAMELSSection from './components/CAMELSSection';
import { BalanceSheet, IncomeStatement } from './components/FinancialStatement';
import MetricsGrid from './components/MetricsGrid';

function App() {
  const { file, loading, progress, result, error, handleFileChange, handleUpload } = useAnalyzer();

  const bank = result?.bank;
  const ratings = result?.detailed_ratings;
  const analysis = result?.analysis;
  const km = result?.key_metrics;
  const warnings = result?.bank?._validation_warnings;

  return (
    <ErrorBoundary>
      <div className="App">
        <h1>CAMELS Analyzer</h1>
        <p className="subtitle">Automated bank financial statement analysis</p>

        <FileUpload
          onFileChange={handleFileChange}
          onUpload={handleUpload}
          loading={loading}
          file={file}
        />

        {loading && <LoadingSpinner progress={progress} />}
        {error && <div className="error">{error}</div>}

        {warnings && warnings.length > 0 && (
          <div className="warning">
            <strong>Data quality warnings:</strong>
            <ul>
              {warnings.map((w, i) => <li key={i}>{w}</li>)}
            </ul>
          </div>
        )}

        {result && (
          <div className="result">
            <div className="bank-info">
              <h3>{bank?.bank_name || 'Unknown Bank'}</h3>
              <p>{bank?.country || ''} — Fiscal Year {bank?.fiscal_year || ''} — {bank?.currency || 'XOF'}</p>
            </div>

            <CompositeRating camelsRating={result?.camels_rating} analysis={analysis} />

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
                { name: 'Net Interest Income / Avg Assets', formula: 'Net Interest Income / Avg Total Assets', value: bank?.net_interest_income_avg_assets },
                { name: 'Non-Interest Income / Avg Assets', formula: '(Fees & Commissions + Net Sales + Dividends + ...) / Avg Total Assets', value: bank?.non_interest_income_avg_assets },
                { name: 'Operating Expenses / Avg Assets', formula: '(Wages + Other OpEx + Amortization + Depreciation) / Avg Total Assets', value: bank?.opex_avg_assets },
                { name: 'Tax Expenses / Avg Assets', formula: 'Tax Expenses / Avg Total Assets', value: bank?.tax_expenses_avg_assets },
                { name: 'Other Income / Avg Assets', formula: '(Provisions Formed + Impairment + FX Exchange) / Avg Total Assets', value: bank?.other_income_avg_assets },
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

            <BalanceSheet bank={bank} />
            <IncomeStatement bank={bank} />
            <MetricsGrid metrics={km} />
          </div>
        )}
      </div>
    </ErrorBoundary>
  );
}

export default App;
