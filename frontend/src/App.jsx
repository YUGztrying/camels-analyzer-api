import { useState } from 'react';
import './App.css';
import { uploadAndAnalyze } from './services/api';

function App() {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
    setError(null);
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Veuillez sélectionner un fichier');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const data = await uploadAndAnalyze(file);
      setResult(data);
    } catch (err) {
      setError('Erreur lors de l\'analyse : ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="App">
      <h1>🏦 CAMELS Analyzer</h1>
      <p>Analyse automatique des états financiers bancaires</p>

      <div className="upload-section">
        <input
          type="file"
          onChange={handleFileChange}
          accept=".pdf,.png,.jpg,.jpeg"
        />
        <button onClick={handleUpload} disabled={loading || !file}>
          {loading ? '⏳ Analyse en cours...' : '🚀 Analyser'}
        </button>
      </div>

      {error && (
        <div className="error">
          ❌ {error}
        </div>
      )}

      {result && (
        <div className="result">
          <h2>✅ Analyse terminée !</h2>
          
          <div className="bank-info">
            <h3>{result.bank.name}</h3>
            <p>{result.bank.country} - {result.bank.fiscal_year}</p>
          </div>

          <div className="rating">
            <h3>Rating CAMELS : {result.camels_rating.composite_rating}</h3>
            <p className={`status status-${result.camels_rating.composite_rating}`}>
              {result.camels_rating.status}
            </p>
          </div>

          <div className="details">
            <h4>Détails par pilier :</h4>
            
            {result.detailed_ratings.capital && (
              <div className="pillar">
                <strong>💰 Capital :</strong> 
                {result.detailed_ratings.capital.status} 
                (CAR: {result.detailed_ratings.capital.car}%)
              </div>
            )}

            {result.detailed_ratings.earnings && (
              <div className="pillar">
                <strong>📈 Rentabilité :</strong> 
                {result.detailed_ratings.earnings.status} 
                (ROE: {(result.detailed_ratings.earnings.roae * 100).toFixed(1)}%)
              </div>
            )}

            {result.detailed_ratings.liquidity && (
              <div className="pillar">
                <strong>💧 Liquidité :</strong> 
                {result.detailed_ratings.liquidity.status} 
                (Ratio: {(result.detailed_ratings.liquidity.ratio * 100).toFixed(1)}%)
              </div>
            )}
          </div>

          <div className="metrics">
            <h4>Métriques clés :</h4>
            <p>Total Actifs : {result.key_metrics.total_assets?.toLocaleString()} M</p>
            <p>ROE : {(result.key_metrics.roae * 100).toFixed(2)}%</p>
            <p>ROA : {(result.key_metrics.roaa * 100).toFixed(2)}%</p>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;