export default function StatementSelector({
  companies,
  selectedCompany,
  periods,
  selectedPeriod,
  loadingCompanies,
  loading,
  onCompanyChange,
  onPeriodChange,
  onAnalyze,
}) {
  return (
    <div className="upload-section">
      {/* Company selector */}
      <div style={{ marginBottom: '1rem' }}>
        <label htmlFor="company-select" style={{ fontWeight: 600, display: 'block', marginBottom: '0.4rem', textAlign: 'left' }}>
          Company
        </label>
        <select
          id="company-select"
          value={selectedCompany?.company_name || ''}
          onChange={(e) => onCompanyChange(e.target.value)}
          disabled={loadingCompanies}
          style={{ width: '100%', padding: '0.6rem', fontSize: '1rem', borderRadius: '6px', border: '1px solid #ccc' }}
        >
          <option value="">{loadingCompanies ? 'Loading companies...' : '-- Select a company --'}</option>
          {companies.map((c) => (
            <option key={c.company_name} value={c.company_name}>
              {c.company_name} ({c.type_institution})
            </option>
          ))}
        </select>
      </div>

      {/* Period selector */}
      {selectedCompany && (
        <div style={{ marginBottom: '1rem' }}>
          <label htmlFor="period-select" style={{ fontWeight: 600, display: 'block', marginBottom: '0.4rem', textAlign: 'left' }}>
            Period
          </label>
          <select
            id="period-select"
            value={selectedPeriod || ''}
            onChange={(e) => onPeriodChange(e.target.value)}
            style={{ width: '100%', padding: '0.6rem', fontSize: '1rem', borderRadius: '6px', border: '1px solid #ccc' }}
          >
            <option value="">
              {periods.length === 0 ? 'No periods available' : '-- Select a period --'}
            </option>
            {periods.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </div>
      )}

      <button onClick={onAnalyze} disabled={loading || !selectedPeriod}>
        {loading ? 'Analyzing...' : 'Run CAMELS Analysis'}
      </button>
    </div>
  );
}
