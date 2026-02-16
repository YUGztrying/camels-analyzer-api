export default function LoadingSpinner({ progress }) {
  return (
    <div className="loading-container">
      <div className="spinner"></div>
      <p className="loading-text">{progress || 'Initializing...'}</p>
    </div>
  );
}
