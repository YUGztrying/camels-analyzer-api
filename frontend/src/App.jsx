import { useState } from 'react';
import './App.css';
import { uploadAndAnalyze } from './services/api';

function App() {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState('');
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
    setError(null);
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a file');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);
    setProgress('Uploading...');

    try {
      const data = await uploadAndAnalyze(file, (step) => {
        setProgress(step);
      });
      setProgress('');
      setResult(data);
    } catch (err) {
      setError('Analysis error: ' + err.message);
      setProgress('');
    } finally {
      setLoading(false);
    }
  };

  const fmtPct = (val) => {
    if (val === null || val === undefined) return 'N/A';
    return `${(val * 100).toFixed(2)}%`;
  };

  const fmtNum = (val) => {
    if (val === null || val === undefined) return '-';
    return val.toLocaleString();
  };

  const ratingColor = (rating) => {
    const colors = { 1: '#2E7D32', 2: '#558B2F', 3: '#F57F17', 4: '#E65100', 5: '#C62828' };
    return colors[rating] || '#757575';
  };

  const bank = result?.bank;
  const ratings = result?.detailed_ratings;
  const analysis = result?.analysis;
  const km = result?.key_metrics;

  return (
    <div className="App">
      <h1>CAMELS Analyzer</h1>
      <p className="subtitle">Automated bank financial statement analysis</p>

      <div className="upload-section">
        <input
          type="file"
          onChange={handleFileChange}
          accept=".pdf,.png,.jpg,.jpeg"
        />
        <button onClick={handleUpload} disabled={loading || !file}>
          {loading ? 'Analyzing...' : 'Analyze'}
        </button>
      </div>

      {loading && (
        <div className="loading-container">
          <div className="spinner"></div>
          <p className="loading-text">{progress || 'Initializing...'}</p>
        </div>
      )}

      {error && <div className="error">{error}</div>}

      {result && (
        <div className="result">
          {/* Bank header */}
          <div className="bank-info">
            <h3>{bank?.bank_name || 'Unknown Bank'}</h3>
            <p>{bank?.country || ''} — Fiscal Year {bank?.fiscal_year || ''} — {bank?.currency || 'XOF'}</p>
          </div>

          {/* Composite rating */}
          <div className="rating-box">
            <h3>Composite CAMELS Rating: {result?.camels_rating?.composite_rating || 'N/A'}</h3>
            <p className={`status status-${result?.camels_rating?.composite_rating || 'na'}`}>
              {result?.camels_rating?.status || 'Insufficient data'}
            </p>
            {result?.camels_rating?.average && (
              <p style={{ marginTop: '0.5rem', opacity: 0.9 }}>Average score: {result.camels_rating.average} ({result.camels_rating.components_used} components)</p>
            )}
          </div>

          {/* Composite analysis */}
          {analysis?.composite && (
            <div className="analysis-box composite-analysis">
              <p>{analysis.composite}</p>
            </div>
          )}

          {/* ===== C — CAPITAL ADEQUACY ===== */}
          <div className="camels-section">
            <div className="camels-header capital-header">
              <span className="camels-letter">C</span>
              <div>
                <h4>Capital Adequacy</h4>
                <span className={`rating-badge rating-${ratings?.capital?.rating || 'na'}`}>
                  {ratings?.capital?.rating || '?'} — {ratings?.capital?.status || 'N/A'}
                </span>
              </div>
            </div>
            <table className="ratio-table">
              <thead>
                <tr><th>Ratio</th><th>Formula</th><th>Value</th></tr>
              </thead>
              <tbody>
                <tr>
                  <td>Equity / Assets</td>
                  <td className="formula">Shareholders' Equity / Total Assets</td>
                  <td className="value">{fmtPct(km?.equity_assets)}</td>
                </tr>
                <tr>
                  <td>Debt / Assets</td>
                  <td className="formula">(Short-Term Borrowings + Long-Term Debt) / Total Assets</td>
                  <td className="value">{fmtPct(km?.debt_assets)}</td>
                </tr>
              </tbody>
            </table>
            {analysis?.capital && <div className="analysis-paragraph"><p>{analysis.capital}</p></div>}
          </div>

          {/* ===== A — ASSET QUALITY ===== */}
          <div className="camels-section">
            <div className="camels-header asset-header">
              <span className="camels-letter">A</span>
              <div>
                <h4>Asset Quality</h4>
                <span className={`rating-badge rating-${ratings?.asset_quality?.rating || 'na'}`}>
                  {ratings?.asset_quality?.rating || '?'} — {ratings?.asset_quality?.status || 'N/A'}
                </span>
              </div>
            </div>
            <table className="ratio-table">
              <thead>
                <tr><th>Ratio</th><th>Formula</th><th>Value</th></tr>
              </thead>
              <tbody>
                <tr>
                  <td>NPL Ratio</td>
                  <td className="formula">NPLs (Stage 3) / Gross Loans</td>
                  <td className="value">{fmtPct(km?.npl_ratio)}</td>
                </tr>
                <tr>
                  <td>Coverage Ratio</td>
                  <td className="formula">Loan Loss Provisions (ECL) / NPLs</td>
                  <td className="value">{fmtPct(km?.coverage_ratio)}</td>
                </tr>
                <tr>
                  <td>Cost of Risk / Avg Assets</td>
                  <td className="formula">ECL / Average Total Assets</td>
                  <td className="value">{fmtPct(km?.cost_of_risk_avg_assets)}</td>
                </tr>
              </tbody>
            </table>
            {analysis?.asset_quality && <div className="analysis-paragraph"><p>{analysis.asset_quality}</p></div>}
          </div>

          {/* ===== M — MANAGEMENT ===== */}
          <div className="camels-section">
            <div className="camels-header management-header">
              <span className="camels-letter">M</span>
              <div>
                <h4>Management (Efficiency)</h4>
                <span className={`rating-badge rating-${ratings?.management?.rating || 'na'}`}>
                  {ratings?.management?.rating || '?'} — {ratings?.management?.status || 'N/A'}
                </span>
              </div>
            </div>
            <table className="ratio-table">
              <thead>
                <tr><th>Ratio</th><th>Formula</th><th>Value</th></tr>
              </thead>
              <tbody>
                <tr>
                  <td>Cost-to-Income Ratio</td>
                  <td className="formula">Operating Expenses / Operating Income</td>
                  <td className="value">{fmtPct(km?.cost_to_income)}</td>
                </tr>
              </tbody>
            </table>
            {analysis?.management && <div className="analysis-paragraph"><p>{analysis.management}</p></div>}
          </div>

          {/* ===== E — EARNINGS ===== */}
          <div className="camels-section">
            <div className="camels-header earnings-header">
              <span className="camels-letter">E</span>
              <div>
                <h4>Earnings</h4>
                <span className={`rating-badge rating-${ratings?.earnings?.rating || 'na'}`}>
                  {ratings?.earnings?.rating || '?'} — {ratings?.earnings?.status || 'N/A'}
                </span>
              </div>
            </div>
            <table className="ratio-table">
              <thead>
                <tr><th>Ratio</th><th>Formula</th><th>Value</th></tr>
              </thead>
              <tbody>
                <tr>
                  <td>ROAA</td>
                  <td className="formula">Net Profit / Average Total Assets</td>
                  <td className="value">{fmtPct(km?.roaa)}</td>
                </tr>
                <tr>
                  <td>ROAE</td>
                  <td className="formula">Net Profit / Average Shareholders' Equity</td>
                  <td className="value">{fmtPct(km?.roae)}</td>
                </tr>
                <tr>
                  <td>Net Interest Income / Avg Assets</td>
                  <td className="formula">(Interest Income + Interest Expenses) / Avg Total Assets</td>
                  <td className="value">{fmtPct(bank?.net_interest_income_avg_assets)}</td>
                </tr>
                <tr>
                  <td>Non-Interest Income / Avg Assets</td>
                  <td className="formula">(Fees & Commissions + Net Sales + Dividends + ...) / Avg Total Assets</td>
                  <td className="value">{fmtPct(bank?.non_interest_income_avg_assets)}</td>
                </tr>
                <tr>
                  <td>Operating Expenses / Avg Assets</td>
                  <td className="formula">(Wages + Other OpEx + Amortization + Depreciation) / Avg Total Assets</td>
                  <td className="value">{fmtPct(bank?.opex_avg_assets)}</td>
                </tr>
                <tr>
                  <td>Tax Expenses / Avg Assets</td>
                  <td className="formula">Tax Expenses / Avg Total Assets</td>
                  <td className="value">{fmtPct(bank?.tax_expenses_avg_assets)}</td>
                </tr>
                <tr>
                  <td>Other Income / Avg Assets</td>
                  <td className="formula">(Provisions Formed + Impairment + FX Exchange) / Avg Total Assets</td>
                  <td className="value">{fmtPct(bank?.other_income_avg_assets)}</td>
                </tr>
              </tbody>
            </table>
            {analysis?.earnings && <div className="analysis-paragraph"><p>{analysis.earnings}</p></div>}
          </div>

          {/* ===== L — LIQUIDITY ===== */}
          <div className="camels-section">
            <div className="camels-header liquidity-header">
              <span className="camels-letter">L</span>
              <div>
                <h4>Liquidity</h4>
                <span className={`rating-badge rating-${ratings?.liquidity?.rating || 'na'}`}>
                  {ratings?.liquidity?.rating || '?'} — {ratings?.liquidity?.status || 'N/A'}
                </span>
              </div>
            </div>
            <table className="ratio-table">
              <thead>
                <tr><th>Ratio</th><th>Formula</th><th>Value</th></tr>
              </thead>
              <tbody>
                <tr>
                  <td>Liquid Assets / Total Assets</td>
                  <td className="formula">(Cash & Deposits with Banks + Investment Securities) / Total Assets</td>
                  <td className="value">{fmtPct(km?.liquid_assets_total_assets)}</td>
                </tr>
              </tbody>
            </table>
            {analysis?.liquidity && <div className="analysis-paragraph"><p>{analysis.liquidity}</p></div>}
          </div>

          {/* ===== FINANCIAL STATEMENTS ===== */}
          <div className="financial-statement">
            <h4 className="statement-header">Balance Sheet — {bank?.fiscal_year}</h4>
            <table className="statement-table">
              <thead>
                <tr><th>{bank?.currency || 'XOF'} mn</th><th>{bank?.fiscal_year}</th></tr>
              </thead>
              <tbody>
                <tr className="section-title"><td colSpan="2"><strong>ASSETS</strong></td></tr>
                <tr><td>Cash & Reserve Requirements</td><td>{fmtNum(bank?.cash_reserves_requirements)}</td></tr>
                <tr><td>Due from Banks</td><td>{fmtNum(bank?.due_from_banks)}</td></tr>
                <tr><td>Investment Securities</td><td>{fmtNum(bank?.investment_securities)}</td></tr>
                <tr><td>Gross Loans</td><td>{fmtNum(bank?.gross_loans)}</td></tr>
                <tr><td>Loan Loss Provisions</td><td>{bank?.loan_loss_provisions != null ? `(${fmtNum(Math.abs(bank.loan_loss_provisions))})` : '-'}</td></tr>
                <tr><td>Foreclosed Assets</td><td>{fmtNum(bank?.foreclosed_assets)}</td></tr>
                <tr><td>Fixed Assets</td><td>{fmtNum(bank?.fixed_assets)}</td></tr>
                <tr><td>Other Assets</td><td>{fmtNum(bank?.other_assets)}</td></tr>
                <tr className="total-row"><td><strong>Total Assets</strong></td><td><strong>{fmtNum(bank?.total_assets)}</strong></td></tr>

                <tr className="section-title"><td colSpan="2"><strong>LIABILITIES</strong></td></tr>
                <tr><td>Customer Deposits</td><td>{fmtNum(bank?.deposits)}</td></tr>
                <tr><td>Short-Term Borrowings</td><td>{fmtNum(bank?.short_term_borrowings)}</td></tr>
                <tr><td>Long-Term Debt</td><td>{fmtNum(bank?.long_term_debt)}</td></tr>
                <tr><td>Interbank Liabilities</td><td>{fmtNum(bank?.interbank_liabilities)}</td></tr>
                <tr><td>Other Liabilities</td><td>{fmtNum(bank?.other_liabilities)}</td></tr>
                <tr className="total-row"><td><strong>Total Liabilities</strong></td><td><strong>{fmtNum(bank?.total_liabilities)}</strong></td></tr>

                <tr className="section-title"><td colSpan="2"><strong>EQUITY</strong></td></tr>
                <tr><td>Paid-in Capital</td><td>{fmtNum(bank?.paid_in_capital)}</td></tr>
                <tr><td>Reserves</td><td>{fmtNum(bank?.reserves)}</td></tr>
                <tr><td>Retained Earnings</td><td>{fmtNum(bank?.retained_earnings)}</td></tr>
                <tr><td>Net Profit</td><td>{fmtNum(bank?.net_profit)}</td></tr>
                <tr className="total-row"><td><strong>Total Equity</strong></td><td><strong>{fmtNum(bank?.total_equity)}</strong></td></tr>
              </tbody>
            </table>
          </div>

          <div className="financial-statement">
            <h4 className="statement-header">Income Statement — {bank?.fiscal_year}</h4>
            <table className="statement-table">
              <thead>
                <tr><th>{bank?.currency || 'XOF'} mn</th><th>{bank?.fiscal_year}</th></tr>
              </thead>
              <tbody>
                <tr><td>Interest Income</td><td>{fmtNum(bank?.interest_income)}</td></tr>
                <tr><td>Interest Expenses</td><td>{bank?.interest_expenses != null ? `(${fmtNum(bank.interest_expenses)})` : '-'}</td></tr>
                <tr className="subtotal-row"><td><strong>Net Interest Income</strong></td><td><strong>{fmtNum(bank?.net_interest_income)}</strong></td></tr>

                <tr><td>Fees & Commissions</td><td>{fmtNum(bank?.fees_commissions || bank?.non_interest_income_commissions)}</td></tr>
                <tr><td>Other Revenues</td><td>{fmtNum(bank?.other_revenues || bank?.other_net_income)}</td></tr>
                {bank?.operating_income && <tr className="subtotal-row"><td><strong>Operating Income</strong></td><td><strong>{fmtNum(bank.operating_income)}</strong></td></tr>}

                <tr><td>Operating Expenses</td><td>{bank?.operating_expenses != null ? `(${fmtNum(bank.operating_expenses)})` : '-'}</td></tr>
                {bank?.operating_profit && <tr className="subtotal-row"><td><strong>Operating Profit</strong></td><td><strong>{fmtNum(bank.operating_profit)}</strong></td></tr>}

                <tr><td>Provision Expenses (ECL)</td><td>{bank?.provision_expenses != null ? `(${fmtNum(bank.provision_expenses)})` : '-'}</td></tr>
                <tr><td>Income Tax</td><td>{bank?.income_tax != null ? `(${fmtNum(bank.income_tax)})` : '-'}</td></tr>
                <tr className="total-row"><td><strong>Net Income</strong></td><td><strong>{fmtNum(bank?.net_income)}</strong></td></tr>
              </tbody>
            </table>
          </div>

          {/* Key metrics cards */}
          <div className="metrics-summary">
            <h4>Key Metrics</h4>
            <div className="metrics-grid">
              <div className="metric-card">
                <span className="metric-label">Total Assets</span>
                <span className="metric-value">{km?.total_assets?.toLocaleString() || 'N/A'}</span>
              </div>
              <div className="metric-card">
                <span className="metric-label">Equity / Assets</span>
                <span className="metric-value">{fmtPct(km?.equity_assets)}</span>
              </div>
              <div className="metric-card">
                <span className="metric-label">ROAE</span>
                <span className="metric-value">{fmtPct(km?.roae)}</span>
              </div>
              <div className="metric-card">
                <span className="metric-label">ROAA</span>
                <span className="metric-value">{fmtPct(km?.roaa)}</span>
              </div>
              <div className="metric-card">
                <span className="metric-label">NPL Ratio</span>
                <span className="metric-value">{fmtPct(km?.npl_ratio)}</span>
              </div>
              <div className="metric-card">
                <span className="metric-label">Cost-to-Income</span>
                <span className="metric-value">{fmtPct(km?.cost_to_income)}</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
