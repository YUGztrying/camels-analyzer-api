export default function FileUpload({ onFileChange, onUpload, loading, file }) {
  return (
    <div className="upload-section">
      <input
        type="file"
        onChange={onFileChange}
        accept=".pdf,.png,.jpg,.jpeg"
      />
      <button onClick={onUpload} disabled={loading || !file}>
        {loading ? 'Analyzing...' : 'Analyze'}
      </button>
    </div>
  );
}
