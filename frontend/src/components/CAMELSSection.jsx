import { fmtPct } from '../utils/formatters';

export default function CAMELSSection({ letter, title, headerClass, rating, ratios, analysis }) {
  return (
    <div className="camels-section">
      <div className={`camels-header ${headerClass}`}>
        <span className="camels-letter">{letter}</span>
        <div>
          <h4>{title}</h4>
          <span className={`rating-badge rating-${rating?.rating || 'na'}`}>
            {rating?.rating || '?'} — {rating?.status || 'N/A'}
          </span>
        </div>
      </div>
      <table className="ratio-table">
        <thead>
          <tr><th>Ratio</th><th>Formula</th><th>Value</th></tr>
        </thead>
        <tbody>
          {ratios.map((r, i) => (
            <tr key={i}>
              <td>{r.name}</td>
              <td className="formula">{r.formula}</td>
              <td className="value">{fmtPct(r.value)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {analysis && (
        <div className="analysis-paragraph">
          <p>{analysis}</p>
        </div>
      )}
    </div>
  );
}
