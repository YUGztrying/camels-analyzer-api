import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  timeout: 30000,
});

export const listCompanies = async (userId) => {
  const response = await api.get('/companies', { params: { user_id: userId } });
  return response.data;
};

export const listPeriods = async (companyName, userId) => {
  const response = await api.get(`/companies/${encodeURIComponent(companyName)}/periods`, {
    params: { user_id: userId },
  });
  return response.data;
};

export const analyzeCompany = async (companyName, period, userId) => {
  const response = await api.post('/analyze', null, {
    params: { company_name: companyName, period, user_id: userId },
  });
  return response.data;
};

export const listAnalyses = async (userId) => {
  const response = await api.get('/analyses', { params: { user_id: userId } });
  return response.data;
};

export default api;
