import { fmtPct } from '../utils/formatters';

function MetricCard({ label, value, format }) {
  const display = format === 'pct' ? fmtPct(value) : (value?.toLocaleString() || 'N/A');
  return (
    <div className="metric-card">
      <span className="metric-label">{label}</span>
      <span className="metric-value">{display}</span>
    </div>
  );
}

export default function MetricsGrid({ metrics }) {
  if (!metrics) return null;
  return (
    <div className="metrics-summary">
      <h4>Key Metrics</h4>
      <div className="metrics-grid">
        <MetricCard label="Total Assets" value={metrics.total_assets} format="num" />
        <MetricCard label="Equity / Assets" value={metrics.equity_assets} format="pct" />
        <MetricCard label="ROAE" value={metrics.roae} format="pct" />
        <MetricCard label="ROAA" value={metrics.roaa} format="pct" />
        <MetricCard label="NPL Ratio" value={metrics.npl_ratio} format="pct" />
        <MetricCard label="Cost-to-Income" value={metrics.cost_to_income} format="pct" />
      </div>
    </div>
  );
}
