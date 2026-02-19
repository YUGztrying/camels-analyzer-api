import { useState, useEffect } from 'react';
import { listCompanies, analyzeCompany } from '../services/api';

export function useAnalyzer(userId) {
  const [companies, setCompanies] = useState([]);
  const [selectedCompany, setSelectedCompany] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadingCompanies, setLoadingCompanies] = useState(true);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!userId) return;
    setLoadingCompanies(true);
    listCompanies(userId)
      .then((data) => setCompanies(data.companies || []))
      .catch((err) => setError('Failed to load companies: ' + err.message))
      .finally(() => setLoadingCompanies(false));
  }, [userId]);

  const handleCompanyChange = (companyName) => {
    const company = companies.find((c) => c.company_name === companyName) || null;
    setSelectedCompany(company);
    setResult(null);
    setError(null);
  };

  const handleAnalyze = async () => {
    if (!selectedCompany) {
      setError('Please select a company');
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await analyzeCompany(selectedCompany.company_name, userId);
      setResult(data);
    } catch (err) {
      const detail = err.response?.data?.detail;
      const msg = Array.isArray(detail) ? detail.map(d => d.msg).join(', ') : (detail || err.message);
      setError('Analysis error: ' + msg);
    } finally {
      setLoading(false);
    }
  };

  return {
    companies,
    selectedCompany,
    loading,
    loadingCompanies,
    result,
    error,
    handleCompanyChange,
    handleAnalyze,
  };
}
