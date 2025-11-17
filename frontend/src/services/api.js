import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  timeout: 300000  // 5 minutes au lieu de 10 secondes
});

export const uploadAndAnalyze = async (file, onProgress) => {
  const formData = new FormData();
  formData.append('file', file);
  
  const uploadResponse = await api.post('/upload-and-analyze', formData);
  const jobId = uploadResponse.data.job_id;
  
  return await pollJobStatus(jobId, onProgress);
};

const pollJobStatus = async (jobId, onProgress, maxAttempts = 60) => {
  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    await new Promise(resolve => setTimeout(resolve, 3000));
    
    const response = await api.get(`/job/${jobId}`);
    const job = response.data;
    
    if (onProgress && job.step) {
      onProgress(job.step);
    }
    
    if (job.status === 'completed') {
      return job.result;
    }
    
    if (job.status === 'failed') {
      throw new Error(job.error || 'Analyse échouée');
    }
  }
  
  throw new Error('Timeout: analyse trop longue (> 3 min)');
};

export const listBanks = async () => {
  const response = await api.get('/banks');
  return response.data;
};

export default api;