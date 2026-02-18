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

        <FileUpload onFileChange={handleFileChange} onUpload={handleUpload} loading={loading} file={file} />

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

            {/* ── CAMELS Ratings ── */}
            <SectionBlock title="CAMELS Ratings" cls="ratings-section-header">
              <table className="evo-table">
                <thead><tr>
                  <th>Component</th>
                  {periods.map((p, i) => <th key={i} className="pc">{p.period_label || p.bank?.fiscal_year}</th>)}
                </tr></thead>
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

            {/* ── Balance Sheet ── */}
            <SectionBlock title="Balance Sheet" cls="financials-header">
              <FinancialTable periods={periods} rows={[
                { label: 'Total Assets', key: 'total_assets', bold: true },
                { label: 'Total Liabilities', key: 'total_liabilities', bold: true },
                { label: "Shareholder's Equity", key: 'total_equity', bold: true },
                { label: 'Cash & Cash Equivalent', key: 'cash_reserves_requirements' },
                { label: 'Investment Securities', key: 'investment_securities' },
                { label: 'Gross Loans', key: 'gross_loans' },
                { label: 'Loan Loss Provisions', key: 'loan_loss_provisions', neg: true },
                { label: 'Customer Deposits', key: 'deposits' },
                { label: 'Borrowings', key: 'short_term_borrowings' },
                { label: 'Long-Term Debt', key: 'long_term_debt' },
              ]} />
            </SectionBlock>

            {/* ── Income Statement ── */}
            <SectionBlock title="Income Statement" cls="financials-header">
              <FinancialTable periods={periods} rows={[
                { label: 'Net Interest Income', key: 'net_interest_income' },
                { label: 'Non-Interest Income', computed: (b) => {
                  const oi = b?.operating_income;
                  const nii = b?.net_interest_income;
                  return (oi != null && nii != null) ? oi - nii : null;
                }},
                { label: 'Operating Expenses', key: 'operating_expenses', neg: true },
                { label: 'Cost of Risk', key: 'provision_expenses', neg: true },
                { label: 'Net Profit', key: 'net_income', bold: true },
              ]} />
            </SectionBlock>

            {/* ── Growth ── */}
            {periods.length > 1 && (
              <SectionBlock title="Growth" cls="financials-header">
                <GrowthTable periods={periods} rows={[
                  { label: 'Assets Growth', key: 'total_assets' },
                  { label: 'Gross Loans', key: 'gross_loans' },
                  { label: 'Deposits', key: 'deposits' },
                  { label: "Shareholders' Equity", key: 'total_equity' },
                ]} />
              </SectionBlock>
            )}

            {/* ── Solvency Ratios ── */}
            <SectionBlock title="Solvency Ratios" cls="capital-header">
              <RatioTable periods={periods} rows={[
                { label: 'CAR - Regulatory', key: 'car', src: 'km' },
                { label: 'Equity / Assets', key: 'equity_assets', src: 'km' },
              ]} />
            </SectionBlock>

            {/* ── Asset Quality ── */}
            <SectionBlock title="Asset Quality" cls="asset-header">
              <RatioTable periods={periods} rows={[
                { label: 'NPL Ratio', key: 'npl_ratio', src: 'km' },
                { label: 'Coverage Ratio', key: 'coverage_ratio', src: 'km' },
              ]} />
            </SectionBlock>

            {/* ── Profitability ── */}
            <SectionBlock title="Profitability" cls="earnings-header">
              <RatioTable periods={periods} rows={[
                { label: 'ROAA', key: 'roaa', src: 'km' },
                { label: 'ROAE', key: 'roae', src: 'km' },
                { label: 'Cost to Income Ratio', key: 'cost_to_income', src: 'km' },
              ]} />
            </SectionBlock>

            {/* ── Liquidity ── */}
            <SectionBlock title="Liquidity" cls="liquidity-header">
              <RatioTable periods={periods} rows={[
                { label: 'Loans/Deposits', key: 'loans_deposits', src: 'km' },
                { label: 'Liquid Assets/Total Assets', key: 'liquid_assets_total_assets', src: 'km' },
              ]} />
            </SectionBlock>

            {/* ── Analysis ── */}
            {analysis && (
              <div className="analysis-section">
                <h3>Analysis</h3>
                <AnalysisBlock title="Capitalization" section="capital" analysis={analysis} ratings={latest?.detailed_ratings} />
                <AnalysisBlock title="Asset Quality" section="asset_quality" analysis={analysis} ratings={latest?.detailed_ratings} />
                <AnalysisBlock title="Management & Efficiency" section="management" analysis={analysis} ratings={latest?.detailed_ratings} />
                <AnalysisBlock title="Earnings & Profitability" section="earnings" analysis={analysis} ratings={latest?.detailed_ratings} />
                <AnalysisBlock title="Liquidity & Funding" section="liquidity" analysis={analysis} ratings={latest?.detailed_ratings} />
                <AnalysisBlock title="Composite Assessment" section="composite" analysis={analysis} ratings={{ composite: latest?.camels_rating }} isComposite />
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

function FinancialTable({ periods, rows }) {
  return (
    <table className="evo-table">
      <thead><tr>
        <th>Item</th>
        {periods.map((p, i) => <th key={i} className="pc">{p.period_label || p.bank?.fiscal_year}</th>)}
      </tr></thead>
      <tbody>
        {rows.map((r, ri) => (
          <tr key={ri} className={r.bold ? 'bold-row' : ''}>
            <td className="row-label">{r.label}</td>
            {periods.map((p, pi) => {
              const val = r.computed ? r.computed(p.bank) : p.bank?.[r.key];
              let display;
              if (val == null) {
                display = '-';
              } else if (r.neg) {
                display = `(${Math.abs(val).toLocaleString()})`;
              } else {
                display = val.toLocaleString();
              }
              return <td key={pi} className="pc num-cell">{display}</td>;
            })}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function GrowthTable({ periods, rows }) {
  return (
    <table className="evo-table">
      <thead><tr>
        <th>Metric</th>
        {periods.map((p, i) => <th key={i} className="pc">{p.period_label || p.bank?.fiscal_year}</th>)}
      </tr></thead>
      <tbody>
        {rows.map((r, ri) => (
          <tr key={ri}>
            <td className="row-label">{r.label}</td>
            {periods.map((p, pi) => {
              if (pi === 0) return <td key={pi} className="pc num-cell na">—</td>;
              const prev = periods[pi - 1].bank?.[r.key];
              const curr = p.bank?.[r.key];
              const growth = (curr != null && prev != null && prev !== 0)
                ? (curr - prev) / Math.abs(prev) : null;
              return <td key={pi} className="pc num-cell">{growth != null ? fmtPct(growth) : 'N/A'}</td>;
            })}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function RatioTable({ periods, rows }) {
  return (
    <table className="evo-table">
      <thead><tr>
        <th>Ratio</th>
        {periods.map((p, i) => <th key={i} className="pc">{p.period_label || p.bank?.fiscal_year}</th>)}
      </tr></thead>
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

function AnalysisBlock({ title, section, analysis, ratings, isComposite }) {
  const data = analysis?.[section];
  if (!data) return null;

  const r = isComposite ? ratings?.composite : ratings?.[section];
  const rating = r?.rating ?? r?.composite_rating;
  const status = r?.status;

  // Handle both old format (string) and new format (array of bullets)
  const bullets = Array.isArray(data) ? data : [data];

  return (
    <div className="analysis-block">
      <h4 className="analysis-title">
        <span className="analysis-title-text">{title}</span>
        {status && <span className="analysis-rating-tag"> ({status})</span>}
      </h4>
      <ul className="analysis-bullets">
        {bullets.map((bullet, i) => <li key={i}>{bullet}</li>)}
      </ul>
    </div>
  );
}

export default App;
