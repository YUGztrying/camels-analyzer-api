import axios from 'axios';

// In production, VITE_API_URL points to the deployed backend.
// In development, the Vite proxy handles /api -> localhost:8000.
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  timeout: 30000,
});

export const listCompanies = async () => {
  const response = await api.get('/companies');
  return response.data;
};

export const listStatements = async (companyId) => {
  const response = await api.get(`/companies/${companyId}/statements`);
  return response.data;
};

export const getStatement = async (statementId) => {
  const response = await api.get(`/statements/${statementId}`);
  return response.data;
};

export const analyzeStatement = async (statementId) => {
  const response = await api.post(`/statements/${statementId}/analyze`);
  return response.data;
};

export default api;
