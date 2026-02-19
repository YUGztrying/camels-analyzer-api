import './App.css';
import { useAuth } from './contexts/AuthContext';
import { useAnalyzer } from './hooks/useAnalyzer';
import Auth from './components/Auth';
import ErrorBoundary from './components/ErrorBoundary';
import StatementSelector from './components/FileUpload';
import LoadingSpinner from './components/LoadingSpinner';

function App() {
  const { user, loading: authLoading, signOut } = useAuth();
  if (authLoading) return <LoadingSpinner progress="Loading..." />;
  if (!user) return <Auth />;
  return <Dashboard user={user} signOut={signOut} />;
}

/* ─── helpers ──────────────────────────────────────────────── */

const fmtNum = (v) => {
  if (v == null) return '—';
  if (Math.abs(v) >= 1e9) return `${(v / 1e9).toFixed(1)}B`;
  if (Math.abs(v) >= 1e6) return `${(v / 1e6).toFixed(1)}M`;
  if (Math.abs(v) >= 1e3) return `${(v / 1e3).toFixed(1)}K`;
  return v.toFixed(0);
};

const fmtPct = (v) => (v == null ? '—' : `${(v * 100).toFixed(2)}%`);

const ratingClass = (r) => (r >= 1 && r <= 5 ? `r-${r}` : '');

/* ─── Dashboard ────────────────────────────────────────────── */

function Dashboard({ user, signOut }) {
  const {
    companies, selectedCompany,
    loading, loadingCompanies, result, error,
    handleCompanyChange, handleAnalyze,
  } = useAnalyzer(user.id);

  return (
    <ErrorBoundary>
      <div className="App">
        {/* Header */}
        <div className="app-header">
          <div>
            <h1>CAMELS Analyzer</h1>
            <p className="subtitle">Automated bank financial statement analysis</p>
          </div>
          <div className="user-bar">
            <span className="user-email">{user.email}</span>
            <button className="sign-out-btn" onClick={signOut}>Sign Out</button>
          </div>
        </div>

        {/* Company selector (no period selector) */}
        <StatementSelector
          companies={companies}
          selectedCompany={selectedCompany}
          loadingCompanies={loadingCompanies}
          loading={loading}
          onCompanyChange={handleCompanyChange}
          onAnalyze={handleAnalyze}
        />

        {loading && <LoadingSpinner progress="Running multi-period CAMELS analysis..." />}
        {error && <div className="error">{error}</div>}

        {result && <AnalysisResults result={result} />}
      </div>
    </ErrorBoundary>
  );
}

/* ═══════════════════════════════════════════════════════════════
   ANALYSIS RESULTS
   ═══════════════════════════════════════════════════════════════ */

function AnalysisResults({ result }) {
  const {
    company_name, type_institution, currency,
    periods, period_labels,
    financial_summary, ratio_tables,
    ratings, analysis,
  } = result;

  return (
    <div className="result">
      {/* Bank info */}
      <div className="bank-info">
        <h3>{company_name}</h3>
        <p>{type_institution} — {periods.length} periods ({period_labels[0]} to {period_labels[period_labels.length - 1]}) — {currency}</p>
      </div>

      {/* Composite rating */}
      <CompositeRating ratings={ratings} />

      {/* CAMELS rating summary table */}
      <RatingEvolutionTable ratings={ratings} />

      {/* Financial summary tables */}
      <FinancialSummaryTable
        title="Balance Sheet"
        headerClass="financials-header"
        rows={financial_summary.balance_sheet}
        periodLabels={period_labels}
        currency={currency}
      />
      <FinancialSummaryTable
        title="Income Statement"
        headerClass="earnings-header"
        rows={financial_summary.income_statement}
        periodLabels={period_labels}
        currency={currency}
      />

      {/* Ratio evolution tables */}
      <RatioEvoTable title="Growth" headerClass="capital-header" rows={ratio_tables.growth} periodLabels={period_labels} />
      <RatioEvoTable title="Solvency" headerClass="capital-header" rows={ratio_tables.solvency} periodLabels={period_labels} />
      <RatioEvoTable title="Asset Quality" headerClass="asset-header" rows={ratio_tables.asset_quality} periodLabels={period_labels} />
      <RatioEvoTable title="Profitability" headerClass="earnings-header" rows={ratio_tables.profitability} periodLabels={period_labels} />
      <RatioEvoTable title="Liquidity" headerClass="liquidity-header" rows={ratio_tables.liquidity} periodLabels={period_labels} />

      {/* Detailed analysis */}
      <AnalysisNarrative analysis={analysis} ratings={ratings} />
    </div>
  );
}

/* ─── Composite Rating ─────────────────────────────────────── */

function CompositeRating({ ratings }) {
  const comp = ratings?.composite;
  const r = comp?.composite_rating;
  return (
    <div className="rating-box">
      <h3>Composite CAMELS Rating</h3>
      <span className={`status status-${r || 'na'}`}>
        {r || '?'} — {comp?.status || 'N/A'}
      </span>
    </div>
  );
}

/* ─── Rating Summary Table ─────────────────────────────────── */

function RatingEvolutionTable({ ratings }) {
  const components = [
    { key: 'capital', label: 'Capital Adequacy' },
    { key: 'asset_quality', label: 'Asset Quality' },
    { key: 'management', label: 'Management' },
    { key: 'earnings', label: 'Earnings' },
    { key: 'liquidity', label: 'Liquidity' },
  ];
  const comp = ratings.composite;

  return (
    <div className="evo-section">
      <div className="evo-header ratings-section-header"><h4>CAMELS Ratings</h4></div>
      <table className="evo-table">
        <thead>
          <tr>
            <th>Component</th>
            <th className="pc">Rating</th>
            <th className="pc">Status</th>
          </tr>
        </thead>
        <tbody>
          {components.map(({ key, label }) => {
            const r = ratings[key];
            return (
              <tr key={key}>
                <td className="row-label">{label}</td>
                <td className="pc">
                  {r?.rating != null
                    ? <span className={`rpill ${ratingClass(r.rating)}`}>{r.rating}</span>
                    : <span className="na">N/A</span>}
                </td>
                <td className="pc">{r?.status || 'N/A'}</td>
              </tr>
            );
          })}
          <tr className="composite-row">
            <td className="row-label">Composite</td>
            <td className="pc">
              {comp?.composite_rating != null
                ? <span className={`rpill ${ratingClass(comp.composite_rating)}`}>{comp.composite_rating}</span>
                : <span className="na">N/A</span>}
            </td>
            <td className="pc">{comp?.status || 'N/A'}</td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}

/* ─── Financial Summary Table ──────────────────────────────── */

function FinancialSummaryTable({ title, headerClass, rows, periodLabels, currency }) {
  return (
    <div className="evo-section">
      <div className={`evo-header ${headerClass}`}><h4>{title} ({currency})</h4></div>
      <table className="evo-table">
        <thead>
          <tr>
            <th></th>
            {periodLabels.map((l) => <th key={l} className="pc">{l}</th>)}
            <th className="pc">CAGR</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const isBold = ['Total Assets', 'Total Liabilities', "Shareholders' Equity", 'Net Profit'].includes(row.label);
            return (
              <tr key={row.key} className={isBold ? 'bold-row' : ''}>
                <td className="row-label">{row.label}</td>
                {row.values.map((v, i) => (
                  <td key={i} className="num-cell">{fmtNum(v)}</td>
                ))}
                <td className="num-cell">{row.cagr != null ? fmtPct(row.cagr) : '—'}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

/* ─── Ratio Evolution Table ────────────────────────────────── */

function RatioEvoTable({ title, headerClass, rows, periodLabels }) {
  return (
    <div className="evo-section">
      <div className={`evo-header ${headerClass}`}><h4>{title}</h4></div>
      <table className="evo-table">
        <thead>
          <tr>
            <th></th>
            {periodLabels.map((l) => <th key={l} className="pc">{l}</th>)}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.key}>
              <td className="row-label">{row.label}</td>
              {row.values.map((v, i) => (
                <td key={i} className="num-cell">{fmtPct(v)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ─── Analysis Narrative ───────────────────────────────────── */

function AnalysisNarrative({ analysis, ratings }) {
  const sections = [
    { key: 'capital', title: 'Capitalization', rating: ratings.capital },
    { key: 'asset_quality', title: 'Asset Quality', rating: ratings.asset_quality },
    { key: 'management', title: 'Management & Efficiency', rating: ratings.management },
    { key: 'earnings', title: 'Earnings', rating: ratings.earnings },
    { key: 'liquidity', title: 'Liquidity', rating: ratings.liquidity },
    { key: 'composite', title: 'Composite Assessment', rating: ratings.composite },
  ];

  return (
    <div className="analysis-section">
      <h3>Detailed Analysis</h3>
      {sections.map(({ key, title, rating }) => {
        const text = analysis?.[key];
        if (!text) return null;

        // Split on bullet markers (•, -, *) at start of line
        const lines = text.split('\n').filter((l) => l.trim());
        const bullets = lines.filter((l) => /^[\s]*[•\-*]/.test(l));
        const hasStructuredBullets = bullets.length > 0;

        return (
          <div key={key} className="analysis-block">
            <h4 className="analysis-title">
              <span className="analysis-title-text">{title}</span>
              {' '}
              <span className="analysis-rating-tag">
                (Rating: {rating?.status || rating?.composite_rating || 'N/A'})
              </span>
            </h4>
            {hasStructuredBullets ? (
              <ul className="analysis-bullets">
                {bullets.map((b, i) => (
                  <li key={i}>{b.replace(/^[\s]*[•\-*]\s*/, '').replace(/\*\*/g, '')}</li>
                ))}
              </ul>
            ) : (
              <div className="analysis-paragraph"><p>{text}</p></div>
            )}
          </div>
        );
      })}
    </div>
  );
}

export default App;
