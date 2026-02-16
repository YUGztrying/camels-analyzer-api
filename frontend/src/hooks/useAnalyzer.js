import { useState } from 'react';
import { uploadAndAnalyze } from '../services/api';

export function useAnalyzer() {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState('');
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
    setError(null);
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a file');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);
    setProgress('Uploading...');

    try {
      const data = await uploadAndAnalyze(file, (step) => {
        setProgress(step);
      });
      setProgress('');
      setResult(data);
    } catch (err) {
      setError('Analysis error: ' + err.message);
      setProgress('');
    } finally {
      setLoading(false);
    }
  };

  return { file, loading, progress, result, error, handleFileChange, handleUpload };
}
