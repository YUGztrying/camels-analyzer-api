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
      setError('Veuillez sélectionner un fichier');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);
    setProgress('Upload en cours...');

    try {
      const data = await uploadAndAnalyze(file, (step) => {
        setProgress(step);
      });
      
      setProgress('');
      setResult(data);
    } catch (err) {
      setError('Erreur lors de l\'analyse : ' + err.message);
      setProgress('');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="App">
      <h1>🏦 CAMELS Analyzer</h1>
      <p>Analyse automatique des états financiers bancaires</p>

      <div className="upload-section">
        <input
          type="file"
          onChange={handleFileChange}
          accept=".pdf,.png,.jpg,.jpeg"
        />
        <button onClick={handleUpload} disabled={loading || !file}>
          {loading ? '⏳ Analyse en cours...' : '🚀 Analyser'}
        </button>
      </div>

      {loading && (
        <div className="loading-container">
          <div className="spinner"></div>
          <p className="loading-text">{progress || 'Initialisation...'}</p>
        </div>
      )}

      {error && (
        <div className="error">
          ❌ {error}
        </div>
      )}

      {result && (
        <div className="result">
          <h2>✅ Analyse terminée !</h2>
          
          <div className="bank-info">
            <h3>{result?.bank?.name || 'Banque inconnue'}</h3>
            <p>{result?.bank?.country || ''} - {result?.bank?.fiscal_year || ''}</p>
          </div>

          <div className="rating-box">
            <h3>Rating CAMELS Composite : {result?.camels_rating?.composite_rating || 'N/A'}</h3>
            <p className={`status status-${result?.camels_rating?.composite_rating || 'na'}`}>
              {result?.camels_rating?.status || 'Non disponible'}
            </p>
          </div>

          {/* BALANCE SHEET */}
          <div className="financial-statement">
            <h4 className="statement-header">📋 Balance Sheet - {result?.bank?.fiscal_year}</h4>
            <table className="statement-table">
              <thead>
                <tr>
                  <th>XOF mn</th>
                  <th>{result?.bank?.fiscal_year}</th>
                </tr>
              </thead>
              <tbody>
                <tr className="section-title">
                  <td colSpan="2"><strong>ASSETS</strong></td>
                </tr>
                <tr>
                  <td>Cash & Reserve Requirements</td>
                  <td>{result?.bank?.cash_reserves_requirements?.toLocaleString() || '-'}</td>
                </tr>
                <tr>
                  <td>Due from Banks</td>
                  <td>{result?.bank?.due_from_banks?.toLocaleString() || '-'}</td>
                </tr>
                <tr>
                  <td>Investment Securities</td>
                  <td>{result?.bank?.investment_securities?.toLocaleString() || '-'}</td>
                </tr>
                <tr>
                  <td>Gross Loans</td>
                  <td>{result?.bank?.gross_loans?.toLocaleString() || '-'}</td>
                </tr>
                <tr>
                  <td>Loan Loss Reserves</td>
                  <td>({result?.bank?.llr_mn?.toLocaleString() || '-'})</td>
                </tr>
                <tr>
                  <td>Foreclosed Assets</td>
                  <td>{result?.bank?.foreclosed_assets?.toLocaleString() || '-'}</td>
                </tr>
                <tr>
                  <td>Fixed Assets</td>
                  <td>{result?.bank?.fixed_assets?.toLocaleString() || '-'}</td>
                </tr>
                <tr>
                  <td>Other Assets</td>
                  <td>{result?.bank?.other_assets?.toLocaleString() || '-'}</td>
                </tr>
                <tr className="total-row">
                  <td><strong>Total Assets</strong></td>
                  <td><strong>{result?.bank?.total_assets?.toLocaleString() || '-'}</strong></td>
                </tr>
                
                <tr className="section-title">
                  <td colSpan="2"><strong>LIABILITIES</strong></td>
                </tr>
                <tr>
                  <td>Customer Deposits</td>
                  <td>{result?.bank?.deposits?.toLocaleString() || '-'}</td>
                </tr>
                <tr>
                  <td>Interbank Liabilities</td>
                  <td>{result?.bank?.interbank_liabilities?.toLocaleString() || '-'}</td>
                </tr>
                <tr>
                  <td>Other Liabilities</td>
                  <td>{result?.bank?.other_liabilities?.toLocaleString() || '-'}</td>
                </tr>
                <tr className="total-row">
                  <td><strong>Total Liabilities</strong></td>
                  <td><strong>{result?.bank?.total_liabilities?.toLocaleString() || '-'}</strong></td>
                </tr>
                
                <tr className="section-title">
                  <td colSpan="2"><strong>EQUITY</strong></td>
                </tr>
                <tr>
                  <td>Paid-in Capital</td>
                  <td>{result?.bank?.paid_capital?.toLocaleString() || '-'}</td>
                </tr>
                <tr>
                  <td>Reserves</td>
                  <td>{result?.bank?.reserves?.toLocaleString() || '-'}</td>
                </tr>
                <tr>
                  <td>Retained Earnings</td>
                  <td>{result?.bank?.retained_earnings?.toLocaleString() || '-'}</td>
                </tr>
                <tr>
                  <td>Net Profit</td>
                  <td>{result?.bank?.net_profit?.toLocaleString() || '-'}</td>
                </tr>
                <tr className="total-row">
                  <td><strong>Total Equity</strong></td>
                  <td><strong>{result?.bank?.total_equity?.toLocaleString() || '-'}</strong></td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* INCOME STATEMENT */}
          <div className="financial-statement">
            <h4 className="statement-header">💰 Income Statement - {result?.bank?.fiscal_year}</h4>
            <table className="statement-table">
              <thead>
                <tr>
                  <th>XOF mn</th>
                  <th>{result?.bank?.fiscal_year}</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>Interest Income</td>
                  <td>{result?.bank?.interest_income?.toLocaleString() || '-'}</td>
                </tr>
                <tr>
                  <td>Interest Expenses</td>
                  <td>({result?.bank?.interest_expenses?.toLocaleString() || '-'})</td>
                </tr>
                <tr className="subtotal-row">
                  <td><strong>Net Interest Income</strong></td>
                  <td><strong>{result?.bank?.net_interest_income?.toLocaleString() || '-'}</strong></td>
                </tr>
                
                <tr>
                  <td>Non-Interest Income (Commissions)</td>
                  <td>{result?.bank?.non_net_interest_income_commissions?.toLocaleString() || '-'}</td>
                </tr>
                <tr>
                  <td>Net Income from Investment</td>
                  <td>{result?.bank?.net_income_from_investment?.toLocaleString() || '-'}</td>
                </tr>
                <tr>
                  <td>Other Net Income</td>
                  <td>{result?.bank?.other_net_income?.toLocaleString() || '-'}</td>
                </tr>
                
                <tr>
                  <td>Operating Expenses</td>
                  <td>({result?.bank?.operating_expenses?.toLocaleString() || '-'})</td>
                </tr>
                <tr className="subtotal-row">
                  <td><strong>Operating Profit</strong></td>
                  <td><strong>{result?.bank?.operating_profit?.toLocaleString() || '-'}</strong></td>
                </tr>
                
                <tr>
                  <td>Provision Expenses</td>
                  <td>({result?.bank?.provision_expenses?.toLocaleString() || '-'})</td>
                </tr>
                <tr>
                  <td>Non-Operating Profit (Loss)</td>
                  <td>{result?.bank?.non_operating_profit_loss?.toLocaleString() || '-'}</td>
                </tr>
                <tr>
                  <td>Income Tax</td>
                  <td>({result?.bank?.income_tax?.toLocaleString() || '-'})</td>
                </tr>
                <tr className="total-row">
                  <td><strong>Net Income</strong></td>
                  <td><strong>{result?.bank?.net_income?.toLocaleString() || '-'}</strong></td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* TABLEAU 1: CAPITAL ADEQUACY (SOLVENCY) */}
          <div className="ratio-section">
            <h4 className="section-header solvency">💰 Capital Adequacy (Solvency Ratios)</h4>
            <table className="ratio-table">
              <thead>
                <tr>
                  <th>Ratio</th>
                  <th>Valeur</th>
                  <th>Rating</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>CAR - Regulatory</td>
                  <td>{result?.key_metrics?.car ? `${result.key_metrics.car}%` : 'N/A'}</td>
                  <td className={`rating-badge rating-${result?.detailed_ratings?.capital?.rating || 'na'}`}>
                    {result?.detailed_ratings?.capital?.status || 'N/A'}
                  </td>
                </tr>
                <tr>
                  <td>CAR - Bank Reported</td>
                  <td>{result?.bank?.car_bank_reported ? `${result.bank.car_bank_reported}%` : 'N/A'}</td>
                  <td>-</td>
                </tr>
                <tr>
                  <td>Equity / Assets</td>
                  <td>{result?.bank?.equity_assets ? `${(result.bank.equity_assets * 100).toFixed(2)}%` : 'N/A'}</td>
                  <td>-</td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* TABLEAU 2: LIQUIDITY */}
          <div className="ratio-section">
            <h4 className="section-header liquidity">💧 Liquidity Ratios</h4>
            <table className="ratio-table">
              <thead>
                <tr>
                  <th>Ratio</th>
                  <th>Valeur</th>
                  <th>Rating</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>Cash & Reserves / Assets</td>
                  <td>{result?.bank?.cash_reserves_assets ? `${(result.bank.cash_reserves_assets * 100).toFixed(1)}%` : 'N/A'}</td>
                  <td>-</td>
                </tr>
                <tr>
                  <td>Liquid Assets / Assets</td>
                  <td>{result?.bank?.liquid_assets_assets ? `${(result.bank.liquid_assets_assets * 100).toFixed(1)}%` : 'N/A'}</td>
                  <td>-</td>
                </tr>
                <tr>
                  <td>Gross Loans / Customer Deposits</td>
                  <td>{result?.key_metrics?.loans_deposits ? `${(result.key_metrics.loans_deposits * 100).toFixed(1)}%` : 'N/A'}</td>
                  <td className={`rating-badge rating-${result?.detailed_ratings?.liquidity?.rating || 'na'}`}>
                    {result?.detailed_ratings?.liquidity?.status || 'N/A'}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* TABLEAU 3: ASSET QUALITY */}
          <div className="ratio-section">
            <h4 className="section-header asset-quality">🏦 Asset Quality</h4>
            <table className="ratio-table">
              <thead>
                <tr>
                  <th>Ratio</th>
                  <th>Valeur</th>
                  <th>Rating</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>Problem Assets (XOF mn)</td>
                  <td>{result?.bank?.problem_assets_mn?.toLocaleString() || 'N/A'}</td>
                  <td>-</td>
                </tr>
                <tr>
                  <td>NPLs (XOF mn)</td>
                  <td>{result?.bank?.npls_mn?.toLocaleString() || 'N/A'}</td>
                  <td>-</td>
                </tr>
                <tr>
                  <td>LLR (XOF mn)</td>
                  <td>{result?.bank?.llr_mn?.toLocaleString() || 'N/A'}</td>
                  <td>-</td>
                </tr>
                <tr>
                  <td>NPA Ratio</td>
                  <td>{result?.bank?.npa_ratio ? `${(result.bank.npa_ratio * 100).toFixed(2)}%` : 'N/A'}</td>
                  <td>-</td>
                </tr>
                <tr>
                  <td>NPL Ratio</td>
                  <td>{result?.key_metrics?.npl_ratio ? `${(result.key_metrics.npl_ratio * 100).toFixed(2)}%` : '⚠️ Non trouvé'}</td>
                  <td className={`rating-badge rating-${result?.detailed_ratings?.asset_quality?.rating || 'na'}`}>
                    {result?.detailed_ratings?.asset_quality?.status || 'Données insuffisantes'}
                  </td>
                </tr>
                <tr>
                  <td>LLR / Average Loan</td>
                  <td>{result?.bank?.llr_avg_loan ? `${(result.bank.llr_avg_loan * 100).toFixed(1)}%` : 'N/A'}</td>
                  <td>-</td>
                </tr>
                <tr>
                  <td>Coverage Ratio</td>
                  <td>{result?.bank?.coverage_ratio ? `${(result.bank.coverage_ratio * 100).toFixed(1)}%` : 'N/A'}</td>
                  <td>-</td>
                </tr>
                <tr>
                  <td>OLER (% of Equity)</td>
                  <td>{result?.bank?.oler ? `${(result.bank.oler * 100).toFixed(1)}%` : 'N/A'}</td>
                  <td>-</td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* TABLEAU 4: PROFITABILITY RATIOS */}
          <div className="ratio-section">
            <h4 className="section-header earnings">📈 Profitability Ratios - LCY</h4>
            <table className="ratio-table">
              <thead>
                <tr>
                  <th>Ratio</th>
                  <th>Valeur</th>
                  <th>Rating</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>Net Interest Margin</td>
                  <td>{result?.bank?.net_interest_margin ? `${(result.bank.net_interest_margin * 100).toFixed(1)}%` : 'N/A'}</td>
                  <td>-</td>
                </tr>
                <tr>
                  <td>Net Interest Spread</td>
                  <td>{result?.bank?.net_interest_spread ? `${(result.bank.net_interest_spread * 100).toFixed(1)}%` : 'N/A'}</td>
                  <td>-</td>
                </tr>
                <tr>
                  <td>Non-Interest Income / Avg Assets</td>
                  <td>{result?.bank?.non_interest_income_assets ? `${(result.bank.non_interest_income_assets * 100).toFixed(1)}%` : 'N/A'}</td>
                  <td>-</td>
                </tr>
                <tr>
                  <td>Interest Earning Assets Yield</td>
                  <td>{result?.bank?.interest_earning_assets_yield ? `${(result.bank.interest_earning_assets_yield * 100).toFixed(1)}%` : 'N/A'}</td>
                  <td>-</td>
                </tr>
                <tr>
                  <td>Cost of Funds</td>
                  <td>{result?.bank?.cost_of_funds ? `${(result.bank.cost_of_funds * 100).toFixed(1)}%` : 'N/A'}</td>
                  <td>-</td>
                </tr>
                <tr>
                  <td>Opex / Avg Assets</td>
                  <td>{result?.bank?.opex_assets ? `${(result.bank.opex_assets * 100).toFixed(1)}%` : 'N/A'}</td>
                  <td>-</td>
                </tr>
                <tr>
                  <td>Cost to Income ratio</td>
                  <td>{result?.bank?.cost_to_income ? `${(result.bank.cost_to_income * 100).toFixed(1)}%` : 'N/A'}</td>
                  <td>-</td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* TABLEAU 5: DUPONT ANALYSIS */}
          <div className="ratio-section">
            <h4 className="section-header dupont">📊 Dupont Analysis - LCY</h4>
            <table className="ratio-table">
              <thead>
                <tr>
                  <th>Ratio</th>
                  <th>Valeur</th>
                  <th>Rating</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>(a) Net Interest Income / Avg Assets</td>
                  <td>{result?.bank?.net_interest_income_assets ? `${(result.bank.net_interest_income_assets * 100).toFixed(1)}%` : 'N/A'}</td>
                  <td>-</td>
                </tr>
                <tr>
                  <td>(b) Non Interest Income / Avg Assets</td>
                  <td>{result?.bank?.non_interest_income_assets_dupont ? `${(result.bank.non_interest_income_assets_dupont * 100).toFixed(1)}%` : 'N/A'}</td>
                  <td>-</td>
                </tr>
                <tr>
                  <td>(c) OPEX / Avg Assets</td>
                  <td>{result?.bank?.opex_assets_dupont ? `${(result.bank.opex_assets_dupont * 100).toFixed(1)}%` : 'N/A'}</td>
                  <td>-</td>
                </tr>
                <tr>
                  <td>(d) Provision Expenses / Avg Assets</td>
                  <td>{result?.bank?.provision_expenses_assets ? `${(result.bank.provision_expenses_assets * 100).toFixed(1)}%` : 'N/A'}</td>
                  <td>-</td>
                </tr>
                <tr>
                  <td>(e) Non Operating Profit (Loss) / Avg Assets</td>
                  <td>{result?.bank?.non_op_assets ? `${(result.bank.non_op_assets * 100).toFixed(1)}%` : 'N/A'}</td>
                  <td>-</td>
                </tr>
                <tr>
                  <td>(f) Tax Expenses / Avg Assets</td>
                  <td>{result?.bank?.tax_expenses_assets ? `${(result.bank.tax_expenses_assets * 100).toFixed(1)}%` : 'N/A'}</td>
                  <td>-</td>
                </tr>
                <tr>
                  <td>(g) Avg Assets / Avg Equity</td>
                  <td>{result?.bank?.assets_equity ? `${result.bank.assets_equity.toFixed(1)}` : 'N/A'}</td>
                  <td>-</td>
                </tr>
                <tr>
                  <td>ROAA</td>
                  <td>{result?.key_metrics?.roaa ? `${(result.key_metrics.roaa * 100).toFixed(2)}%` : 'N/A'}</td>
                  <td>-</td>
                </tr>
                <tr>
                  <td>ROAE (a+b+c+d+e+f) x g</td>
                  <td>{result?.key_metrics?.roae ? `${(result.key_metrics.roae * 100).toFixed(2)}%` : 'N/A'}</td>
                  <td className={`rating-badge rating-${result?.detailed_ratings?.earnings?.rating || 'na'}`}>
                    {result?.detailed_ratings?.earnings?.status || 'N/A'}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* RÉSUMÉ DES MÉTRIQUES */}
          <div className="metrics-summary">
            <h4>📊 Métriques Clés</h4>
            <div className="metrics-grid">
              <div className="metric-card">
                <span className="metric-label">Total Actifs</span>
                <span className="metric-value">{result?.key_metrics?.total_assets?.toLocaleString() || 'N/A'} M</span>
              </div>
              <div className="metric-card">
                <span className="metric-label">CAR</span>
                <span className="metric-value">{result?.key_metrics?.car || 'N/A'}%</span>
              </div>
              <div className="metric-card">
                <span className="metric-label">ROE</span>
                <span className="metric-value">
                  {result?.key_metrics?.roae ? `${(result.key_metrics.roae * 100).toFixed(2)}%` : 'N/A'}
                </span>
              </div>
              <div className="metric-card">
                <span className="metric-label">ROA</span>
                <span className="metric-value">
                  {result?.key_metrics?.roaa ? `${(result.key_metrics.roaa * 100).toFixed(2)}%` : 'N/A'}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;