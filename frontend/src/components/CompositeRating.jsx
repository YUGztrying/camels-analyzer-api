export default function CompositeRating({ camelsRating, analysis }) {
  if (!camelsRating) return null;

  return (
    <>
      <div className="rating-box">
        <h3>Composite CAMELS Rating: {camelsRating.composite_rating || 'N/A'}</h3>
        <p className={`status status-${camelsRating.composite_rating || 'na'}`}>
          {camelsRating.status || 'Insufficient data'}
        </p>
        {camelsRating.average && (
          <p style={{ marginTop: '0.5rem', opacity: 0.9 }}>
            Average score: {camelsRating.average} ({camelsRating.components_used} components)
          </p>
        )}
      </div>
      {analysis?.composite && (
        <div className="analysis-box composite-analysis">
          <p>{analysis.composite}</p>
        </div>
      )}
    </>
  );
}
