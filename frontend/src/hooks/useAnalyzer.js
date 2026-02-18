import { useState } from 'react';
import { uploadAndAnalyze } from '../services/api';

export function useAnalyzer() {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState('');
  const [result, setResult] = useState(null);
  const [pendingResult, setPendingResult] = useState(null);
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
    setPendingResult(null);
    setProgress('Uploading...');

    try {
      const data = await uploadAndAnalyze(file, (step) => {
        setProgress(step);
      });
      setProgress('');
      setPendingResult(data);
    } catch (err) {
      setError('Analysis error: ' + err.message);
      setProgress('');
    } finally {
      setLoading(false);
    }
  };

  const confirmResult = () => {
    setResult(pendingResult);
    setPendingResult(null);
  };

  return {
    file, loading, progress, result, pendingResult, error,
    handleFileChange, handleUpload, confirmResult,
  };
}
