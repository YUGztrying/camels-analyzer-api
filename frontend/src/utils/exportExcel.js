import * as XLSX from 'xlsx';

/**
 * Format a ratio value as a percentage string for the Excel export.
 * Returns 'N/A' when the value is null/undefined.
 */
function pct(val) {
  if (val === null || val === undefined) return 'N/A';
  return `${(val * 100).toFixed(2)}%`;
}

/**
 * Convert a rating number to its descriptive label.
 */
function ratingLabel(rating) {
  const labels = {
    1: 'Strong',
    2: 'Satisfactory',
    3: 'Fair',
    4: 'Marginal',
    5: 'Unsatisfactory',
  };
  return labels[rating] || 'N/A';
}

/**
 * Auto-size columns by scanning data widths.
 * Returns an array of { wch: number } objects suitable for ws['!cols'].
 */
function autoWidth(data) {
  if (!data || data.length === 0) return [];
  const colCount = Math.max(...data.map((row) => row.length));
  const widths = [];
  for (let col = 0; col < colCount; col++) {
    let max = 10; // minimum width
    for (const row of data) {
      const cell = row[col];
      const len = cell != null ? String(cell).length : 0;
      if (len > max) max = len;
    }
    widths.push({ wch: Math.min(max + 2, 60) }); // cap at 60
  }
  return widths;
}

/**
 * Build the "CAMELS Ratings" sheet data as a 2D array.
 */
function buildRatingsSheet(result) {
  const camels = result.camels_rating || {};
  const ratings = result.detailed_ratings || {};

  const rows = [
    ['CAMELS Ratings Summary'],
    [],
    ['Component', 'Rating', 'Label'],
    ['Composite', camels.composite_rating ?? 'N/A', camels.status || 'N/A'],
    [],
    ['Individual Component Ratings'],
    ['Component', 'Rating', 'Label'],
    [
      'C - Capital Adequacy',
      ratings.capital?.rating ?? 'N/A',
      ratings.capital?.status || 'N/A',
    ],
    [
      'A - Asset Quality',
      ratings.asset_quality?.rating ?? 'N/A',
      ratings.asset_quality?.status || 'N/A',
    ],
    [
      'M - Management (Efficiency)',
      ratings.management?.rating ?? 'N/A',
      ratings.management?.status || 'N/A',
    ],
    [
      'E - Earnings',
      ratings.earnings?.rating ?? 'N/A',
      ratings.earnings?.status || 'N/A',
    ],
    [
      'L - Liquidity',
      ratings.liquidity?.rating ?? 'N/A',
      ratings.liquidity?.status || 'N/A',
    ],
    [],
    ['Average Score', camels.average ?? 'N/A'],
    ['Components Used', camels.components_used ?? 'N/A'],
  ];

  // Add bank info and date if available
  const bank = result.bank || {};
  if (bank.bank_name || bank.fiscal_year) {
    rows.push([]);
    rows.push(['Bank', bank.bank_name || 'Unknown']);
    rows.push(['Country', bank.country || 'N/A']);
    rows.push(['Fiscal Year', bank.fiscal_year || 'N/A']);
    rows.push(['Currency', bank.currency || 'XOF']);
  }

  return rows;
}

/**
 * Build the "Key Ratios" sheet data as a 2D array.
 */
function buildRatiosSheet(result) {
  const km = result.key_metrics || {};
  const bank = result.bank || {};

  const rows = [
    ['Key Ratios by CAMELS Category'],
    [],
    ['Category', 'Ratio', 'Value'],
    [],
    ['CAPITAL ADEQUACY'],
    ['Capital', 'Equity / Assets', pct(km.equity_assets)],
    ['Capital', 'Debt / Assets', pct(km.debt_assets)],
    [],
    ['ASSET QUALITY'],
    ['Asset Quality', 'NPL Ratio', pct(km.npl_ratio)],
    ['Asset Quality', 'Coverage Ratio', pct(km.coverage_ratio)],
    [
      'Asset Quality',
      'Cost of Risk / Avg Assets',
      pct(km.cost_of_risk_avg_assets),
    ],
    [],
    ['MANAGEMENT (EFFICIENCY)'],
    ['Management', 'Cost-to-Income Ratio', pct(km.cost_to_income)],
    [],
    ['EARNINGS'],
    ['Earnings', 'ROAA', pct(km.roaa)],
    ['Earnings', 'ROAE', pct(km.roae)],
    [
      'Earnings',
      'Net Interest Income / Avg Assets',
      pct(bank.net_interest_income_avg_assets),
    ],
    [
      'Earnings',
      'Non-Interest Income / Avg Assets',
      pct(bank.non_interest_income_avg_assets),
    ],
    [
      'Earnings',
      'Operating Expenses / Avg Assets',
      pct(bank.opex_avg_assets),
    ],
    ['Earnings', 'Tax Expenses / Avg Assets', pct(bank.tax_expenses_avg_assets)],
    [
      'Earnings',
      'Other Income / Avg Assets',
      pct(bank.other_income_avg_assets),
    ],
    [],
    ['LIQUIDITY'],
    [
      'Liquidity',
      'Liquid Assets / Total Assets',
      pct(km.liquid_assets_total_assets),
    ],
  ];

  return rows;
}

/**
 * Build the "Analysis" sheet data as a 2D array.
 */
function buildAnalysisSheet(result) {
  const analysis = result.analysis || {};

  const rows = [
    ['CAMELS Analysis'],
    [],
    ['Component', 'Analysis'],
  ];

  const sections = [
    ['Composite', analysis.composite],
    ['C - Capital Adequacy', analysis.capital],
    ['A - Asset Quality', analysis.asset_quality],
    ['M - Management (Efficiency)', analysis.management],
    ['E - Earnings', analysis.earnings],
    ['L - Liquidity', analysis.liquidity],
  ];

  for (const [label, text] of sections) {
    rows.push([label, text || 'No analysis available']);
  }

  return rows;
}

/**
 * Export analysis results to an Excel (.xlsx) file and trigger a download.
 *
 * @param {Object} result - The full analysis result object from the API.
 */
export function exportToExcel(result) {
  if (!result) return;

  const wb = XLSX.utils.book_new();

  // --- Sheet 1: CAMELS Ratings ---
  const ratingsData = buildRatingsSheet(result);
  const wsRatings = XLSX.utils.aoa_to_sheet(ratingsData);
  wsRatings['!cols'] = autoWidth(ratingsData);
  XLSX.utils.book_append_sheet(wb, wsRatings, 'CAMELS Ratings');

  // --- Sheet 2: Key Ratios ---
  const ratiosData = buildRatiosSheet(result);
  const wsRatios = XLSX.utils.aoa_to_sheet(ratiosData);
  wsRatios['!cols'] = autoWidth(ratiosData);
  XLSX.utils.book_append_sheet(wb, wsRatios, 'Key Ratios');

  // --- Sheet 3: Analysis ---
  const analysisData = buildAnalysisSheet(result);
  const wsAnalysis = XLSX.utils.aoa_to_sheet(analysisData);
  wsAnalysis['!cols'] = autoWidth(analysisData);
  // Enable text wrapping on analysis cells (column B, rows 4+)
  for (let r = 3; r < analysisData.length; r++) {
    const cellRef = XLSX.utils.encode_cell({ r, c: 1 });
    if (wsAnalysis[cellRef]) {
      wsAnalysis[cellRef].s = { alignment: { wrapText: true } };
    }
  }
  XLSX.utils.book_append_sheet(wb, wsAnalysis, 'Analysis');

  // --- Generate filename ---
  const bankName = result.bank?.bank_name || 'Bank';
  const year = result.bank?.fiscal_year || '';
  const safeName = bankName.replace(/[^a-zA-Z0-9_-]/g, '_');
  const filename = `CAMELS_${safeName}${year ? '_' + year : ''}.xlsx`;

  // --- Trigger download ---
  XLSX.writeFile(wb, filename);
}
