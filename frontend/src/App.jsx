import './App.css';
import { useAnalyzer } from './hooks/useAnalyzer';
import { exportToExcel } from './utils/exportExcel';
import { fmtPct, fmtNum } from './utils/formatters';
import ErrorBoundary from './components/ErrorBoundary';
import FileUpload from './components/FileUpload';
import LoadingSpinner from './components/LoadingSpinner';

function App() {
  const { file, loading, progress, result, error, handleFileChange, handleUpload } = useAnalyzer();

  const periods = result?.all_periods || (result ? [result] : []);
  const latest = periods[periods.length - 1];
  const analysis = latest?.analysis;

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

        {result && periods.length > 0 && (
          <div className="result">
            <div className="bank-info">
              <h3>{latest?.bank?.bank_name || result?.file || 'Unknown Bank'}</h3>
              <p>
                {latest?.bank?.country ? `${latest.bank.country} — ` : ''}
                {periods.length} period{periods.length > 1 ? 's' : ''}: {periods.map(p => p.period_label || p.bank?.fiscal_year).join(', ')}
                {' — '}{latest?.bank?.currency || 'XOF'}
              </p>
            </div>

            <div className="export-bar">
              <button className="export-btn" onClick={() => exportToExcel(result)}>
                <svg className="export-icon" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                  <polyline points="7 10 12 15 17 10" />
                  <line x1="12" y1="15" x2="12" y2="3" />
                </svg>
                Export to Excel
              </button>
            </div>

            {/* CAMELS Ratings */}
            <SectionBlock title="CAMELS Ratings" cls="ratings-section-header">
              <table className="evo-table">
                <thead>
                  <tr>
                    <th>Component</th>
                    {periods.map((p, i) => <th key={i} className="pc">{p.period_label || p.bank?.fiscal_year}</th>)}
                  </tr>
                </thead>
                <tbody>
                  <RatingRow label="Composite" periods={periods} path="composite" composite />
                  <RatingRow label="C - Capital" periods={periods} path="capital" />
                  <RatingRow label="A - Asset Quality" periods={periods} path="asset_quality" />
                  <RatingRow label="M - Management" periods={periods} path="management" />
                  <RatingRow label="E - Earnings" periods={periods} path="earnings" />
                  <RatingRow label="L - Liquidity" periods={periods} path="liquidity" />
                </tbody>
              </table>
            </SectionBlock>

            {/* C - Capital */}
            <SectionBlock title="C — Capital Adequacy" cls="capital-header">
              <RatioTable periods={periods} rows={[
                { label: 'Equity / Assets', key: 'equity_assets', src: 'km' },
                { label: 'Debt / Assets', key: 'debt_assets', src: 'km' },
              ]} />
            </SectionBlock>

            {/* A - Asset Quality */}
            <SectionBlock title="A — Asset Quality" cls="asset-header">
              <RatioTable periods={periods} rows={[
                { label: 'NPL Ratio', key: 'npl_ratio', src: 'km' },
                { label: 'Coverage Ratio', key: 'coverage_ratio', src: 'km' },
                { label: 'Cost of Risk / Avg Assets', key: 'cost_of_risk_avg_assets', src: 'km' },
              ]} />
            </SectionBlock>

            {/* M - Management */}
            <SectionBlock title="M — Management (Efficiency)" cls="management-header">
              <RatioTable periods={periods} rows={[
                { label: 'Cost-to-Income', key: 'cost_to_income', src: 'km' },
              ]} />
            </SectionBlock>

            {/* E - Earnings */}
            <SectionBlock title="E — Earnings" cls="earnings-header">
              <RatioTable periods={periods} rows={[
                { label: 'ROAA', key: 'roaa', src: 'km' },
                { label: 'ROAE', key: 'roae', src: 'km' },
                { label: 'NII / Avg Assets', key: 'net_interest_income_avg_assets', src: 'bank' },
                { label: 'Non-Interest Inc / Avg Assets', key: 'non_interest_income_avg_assets', src: 'bank' },
                { label: 'OpEx / Avg Assets', key: 'opex_avg_assets', src: 'bank' },
                { label: 'Tax / Avg Assets', key: 'tax_expenses_avg_assets', src: 'bank' },
              ]} />
            </SectionBlock>

            {/* L - Liquidity */}
            <SectionBlock title="L — Liquidity" cls="liquidity-header">
              <RatioTable periods={periods} rows={[
                { label: 'Liquid Assets / Total Assets', key: 'liquid_assets_total_assets', src: 'km' },
                { label: 'Gross Loans / Deposits', key: 'loans_deposits', src: 'km' },
              ]} />
            </SectionBlock>

            {/* Key Financials */}
            <SectionBlock title="Key Financials" cls="financials-header">
              <table className="evo-table">
                <thead>
                  <tr>
                    <th>Item</th>
                    {periods.map((p, i) => <th key={i} className="pc">{p.period_label || p.bank?.fiscal_year}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {[
                    ['Total Assets', 'total_assets'],
                    ['Gross Loans', 'gross_loans'],
                    ['Total Deposits', 'deposits'],
                    ['Total Equity', 'total_equity'],
                    ['Interest Income', 'interest_income'],
                    ['Interest Expenses', 'interest_expenses'],
                    ['Net Interest Income', 'net_interest_income'],
                    ['Operating Income (PNB)', 'operating_income'],
                    ['Operating Expenses', 'operating_expenses'],
                    ['Provision Expenses', 'provision_expenses'],
                    ['Net Income', 'net_income'],
                  ].map(([label, key]) => (
                    <tr key={key}>
                      <td className="row-label">{label}</td>
                      {periods.map((p, i) => (
                        <td key={i} className="pc num-cell">{fmtNum(p.bank?.[key])}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </SectionBlock>

            {/* Analysis - latest period */}
            {analysis && (
              <div className="analysis-section">
                <h3>Analysis — {latest.period_label || latest.bank?.fiscal_year}</h3>
                {['composite', 'capital', 'asset_quality', 'management', 'earnings', 'liquidity'].map(key => (
                  analysis[key] ? (
                    <div key={key} className="analysis-block">
                      <h5>{key === 'asset_quality' ? 'Asset Quality' : key.charAt(0).toUpperCase() + key.slice(1)}</h5>
                      <p>{analysis[key]}</p>
                    </div>
                  ) : null
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </ErrorBoundary>
  );
}


/* ─── Sub-components ─────────────────────────────────────────────────── */

function SectionBlock({ title, cls, children }) {
  return (
    <div className="evo-section">
      <div className={`evo-header ${cls || ''}`}><h4>{title}</h4></div>
      {children}
    </div>
  );
}

function RatingRow({ label, periods, path, composite }) {
  return (
    <tr className={composite ? 'composite-row' : ''}>
      <td className="row-label">{label}</td>
      {periods.map((p, i) => {
        const r = composite ? p.camels_rating : p.detailed_ratings?.[path];
        const rating = r?.rating ?? r?.composite_rating;
        const status = r?.status;
        return (
          <td key={i} className="pc">
            {rating ? (
              <span className={`rpill r-${rating}`}>{rating} — {status}</span>
            ) : <span className="na">N/A</span>}
          </td>
        );
      })}
    </tr>
  );
}

function RatioTable({ periods, rows }) {
  return (
    <table className="evo-table">
      <thead>
        <tr>
          <th>Ratio</th>
          {periods.map((p, i) => <th key={i} className="pc">{p.period_label || p.bank?.fiscal_year}</th>)}
        </tr>
      </thead>
      <tbody>
        {rows.map((r, ri) => (
          <tr key={ri}>
            <td className="row-label">{r.label}</td>
            {periods.map((p, pi) => {
              const val = r.src === 'km' ? p.key_metrics?.[r.key] : p.bank?.[r.key];
              return <td key={pi} className="pc num-cell">{fmtPct(val)}</td>;
            })}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default App;
