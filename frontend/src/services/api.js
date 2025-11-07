import axios from 'axios';

const api = axios.create({
  baseURL: 'https://zany-funicular-pjp7qqg49j5g3rg5r-8001.app.github.dev',
});

export const uploadAndAnalyze = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post('/upload-and-analyze', formData);
  return response.data;
};

export const listBanks = async () => {
  const response = await api.get('/banks');
  return response.data;
};

export default api;
