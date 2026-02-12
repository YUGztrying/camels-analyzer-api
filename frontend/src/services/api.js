import axios from 'axios';

// In production, VITE_API_URL points to the deployed backend (e.g. Railway).
// In development, the Vite proxy handles /api -> localhost:8000.
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  timeout: 300000,
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
    const delay = Math.min(2000 + attempt * 1000, 5000);
    await new Promise(resolve => setTimeout(resolve, delay));

    const response = await api.get(`/job/${jobId}`);
    const job = response.data;

    if (onProgress && job.step) {
      onProgress(job.step);
    }

    if (job.status === 'completed') {
      return job.result;
    }

    if (job.status === 'failed') {
      throw new Error(job.error || 'Analysis failed');
    }
  }

  throw new Error('Timeout: analysis took too long (> 3 min)');
};

export const listBanks = async () => {
  const response = await api.get('/banks');
  return response.data;
};

export default api;
