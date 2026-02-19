export default function StatementSelector({
  companies,
  selectedCompany,
  statements,
  selectedStatement,
  loadingCompanies,
  loading,
  onCompanyChange,
  onStatementChange,
  onAnalyze,
}) {
  const fmtAssets = (v) => (v != null ? Number(v).toLocaleString() : '');

  return (
    <div className="upload-section">
      {/* Company selector */}
      <div style={{ marginBottom: '1rem' }}>
        <label htmlFor="company-select" style={{ fontWeight: 600, display: 'block', marginBottom: '0.4rem', textAlign: 'left' }}>
          Company
        </label>
        <select
          id="company-select"
          value={selectedCompany?.id || ''}
          onChange={(e) => onCompanyChange(e.target.value)}
          disabled={loadingCompanies}
          style={{ width: '100%', padding: '0.6rem', fontSize: '1rem', borderRadius: '6px', border: '1px solid #ccc' }}
        >
          <option value="">{loadingCompanies ? 'Loading companies...' : '-- Select a company --'}</option>
          {companies.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name} ({c.country})
            </option>
          ))}
        </select>
      </div>

      {/* Statement selector */}
      {selectedCompany && (
        <div style={{ marginBottom: '1rem' }}>
          <label htmlFor="statement-select" style={{ fontWeight: 600, display: 'block', marginBottom: '0.4rem', textAlign: 'left' }}>
            Financial Statement
          </label>
          <select
            id="statement-select"
            value={selectedStatement?.id || ''}
            onChange={(e) => onStatementChange(e.target.value)}
            style={{ width: '100%', padding: '0.6rem', fontSize: '1rem', borderRadius: '6px', border: '1px solid #ccc' }}
          >
            <option value="">
              {statements.length === 0 ? 'No statements available' : '-- Select a period --'}
            </option>
            {statements.map((s) => (
              <option key={s.id} value={s.id}>
                {s.fiscal_year} ({s.statement_type}) — Assets: {fmtAssets(s.total_assets)} {s.currency}
              </option>
            ))}
          </select>
        </div>
      )}

      <button onClick={onAnalyze} disabled={loading || !selectedStatement}>
        {loading ? 'Analyzing...' : 'Run CAMELS Analysis'}
      </button>
    </div>
  );
}
