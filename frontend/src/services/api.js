import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  timeout: 120000,
});

export const listCompanies = async (userId) => {
  const response = await api.get('/companies', { params: { user_id: userId } });
  return response.data;
};

export const analyzeCompany = async (companyName, userId) => {
  const response = await api.post('/analyze', null, {
    params: { company_name: companyName, user_id: userId },
  });
  return response.data;
};

export const listAnalyses = async (userId) => {
  const response = await api.get('/analyses', { params: { user_id: userId } });
  return response.data;
};

export default api;
