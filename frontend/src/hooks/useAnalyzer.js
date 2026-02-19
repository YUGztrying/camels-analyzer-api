import { useState, useEffect } from 'react';
import { listCompanies, listPeriods, analyzeCompany } from '../services/api';

export function useAnalyzer() {
  const [companies, setCompanies] = useState([]);
  const [selectedCompany, setSelectedCompany] = useState(null);
  const [periods, setPeriods] = useState([]);
  const [selectedPeriod, setSelectedPeriod] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadingCompanies, setLoadingCompanies] = useState(true);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  // Fetch companies on mount
  useEffect(() => {
    setLoadingCompanies(true);
    listCompanies()
      .then((data) => setCompanies(data.companies || []))
      .catch((err) => setError('Failed to load companies: ' + err.message))
      .finally(() => setLoadingCompanies(false));
  }, []);

  // Fetch periods when company changes
  useEffect(() => {
    if (!selectedCompany) {
      setPeriods([]);
      setSelectedPeriod(null);
      return;
    }
    setPeriods([]);
    setSelectedPeriod(null);
    setResult(null);
    setError(null);

    listPeriods(selectedCompany.company_name)
      .then((data) => setPeriods(data.periods || []))
      .catch((err) => setError('Failed to load periods: ' + err.message));
  }, [selectedCompany]);

  const handleCompanyChange = (companyName) => {
    const company = companies.find((c) => c.company_name === companyName) || null;
    setSelectedCompany(company);
  };

  const handlePeriodChange = (period) => {
    setSelectedPeriod(period);
    setResult(null);
    setError(null);
  };

  const handleAnalyze = async () => {
    if (!selectedCompany || !selectedPeriod) {
      setError('Please select a company and period');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const data = await analyzeCompany(selectedCompany.company_name, selectedPeriod);
      setResult(data);
    } catch (err) {
      const msg = err.response?.data?.detail || err.message;
      setError('Analysis error: ' + msg);
    } finally {
      setLoading(false);
    }
  };

  return {
    companies,
    selectedCompany,
    periods,
    selectedPeriod,
    loading,
    loadingCompanies,
    result,
    error,
    handleCompanyChange,
    handlePeriodChange,
    handleAnalyze,
  };
}
