import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  timeout: 30000,
});

// Pass user_id as query param for development.
// In production, the Supabase JWT in Authorization header handles auth.
const getUserId = () => {
  // Try to get from Supabase session or localStorage
  return localStorage.getItem('camels_user_id') || '';
};

export const listCompanies = async (userId) => {
  const uid = userId || getUserId();
  const response = await api.get('/companies', { params: { user_id: uid } });
  return response.data;
};

export const listPeriods = async (companyName, userId) => {
  const uid = userId || getUserId();
  const response = await api.get(`/companies/${encodeURIComponent(companyName)}/periods`, {
    params: { user_id: uid },
  });
  return response.data;
};

export const analyzeCompany = async (companyName, period, userId) => {
  const uid = userId || getUserId();
  const response = await api.post('/analyze', null, {
    params: { company_name: companyName, period, user_id: uid },
  });
  return response.data;
};

export const listAnalyses = async (userId) => {
  const uid = userId || getUserId();
  const response = await api.get('/analyses', { params: { user_id: uid } });
  return response.data;
};

export default api;
