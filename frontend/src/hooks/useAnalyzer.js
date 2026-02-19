import { useState, useEffect } from 'react';
import { listCompanies, listStatements, analyzeStatement } from '../services/api';

export function useAnalyzer() {
  const [companies, setCompanies] = useState([]);
  const [selectedCompany, setSelectedCompany] = useState(null);
  const [statements, setStatements] = useState([]);
  const [selectedStatement, setSelectedStatement] = useState(null);
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

  // Fetch statements when company changes
  useEffect(() => {
    if (!selectedCompany) {
      setStatements([]);
      setSelectedStatement(null);
      return;
    }
    setStatements([]);
    setSelectedStatement(null);
    setResult(null);
    setError(null);

    listStatements(selectedCompany.id)
      .then((data) => setStatements(data.statements || []))
      .catch((err) => setError('Failed to load statements: ' + err.message));
  }, [selectedCompany]);

  const handleCompanyChange = (companyId) => {
    const company = companies.find((c) => c.id === companyId) || null;
    setSelectedCompany(company);
  };

  const handleStatementChange = (statementId) => {
    const stmt = statements.find((s) => s.id === statementId) || null;
    setSelectedStatement(stmt);
    setResult(null);
    setError(null);
  };

  const handleAnalyze = async () => {
    if (!selectedStatement) {
      setError('Please select a financial statement');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const data = await analyzeStatement(selectedStatement.id);
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
    statements,
    selectedStatement,
    loading,
    loadingCompanies,
    result,
    error,
    handleCompanyChange,
    handleStatementChange,
    handleAnalyze,
  };
}
