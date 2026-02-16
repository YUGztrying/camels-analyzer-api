export const fmtPct = (val) => {
  if (val === null || val === undefined) return 'N/A';
  return `${(val * 100).toFixed(2)}%`;
};

export const fmtNum = (val) => {
  if (val === null || val === undefined) return '-';
  return val.toLocaleString();
};

export const ratingColor = (rating) => {
  const colors = { 1: '#2E7D32', 2: '#558B2F', 3: '#F57F17', 4: '#E65100', 5: '#C62828' };
  return colors[rating] || '#757575';
};
