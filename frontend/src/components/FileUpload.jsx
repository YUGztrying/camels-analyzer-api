export default function StatementSelector({
  companies,
  selectedCompany,
  loadingCompanies,
  loading,
  onCompanyChange,
  onAnalyze,
}) {
  return (
    <div className="upload-section">
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

      <button onClick={onAnalyze} disabled={loading || !selectedCompany}>
        {loading ? 'Analyzing...' : 'Run CAMELS Analysis'}
      </button>
    </div>
  );
}
