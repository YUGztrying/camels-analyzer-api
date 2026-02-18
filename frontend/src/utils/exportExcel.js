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
 * Format an absolute number with locale separators.
 */
function num(val) {
  if (val === null || val === undefined) return '-';
  return val.toLocaleString();
}

/**
 * Auto-size columns by scanning data widths.
 */
function autoWidth(data) {
  if (!data || data.length === 0) return [];
  const colCount = Math.max(...data.map((row) => row.length));
  const widths = [];
  for (let col = 0; col < colCount; col++) {
    let max = 10;
    for (const row of data) {
      const cell = row[col];
      const len = cell != null ? String(cell).length : 0;
      if (len > max) max = len;
    }
    widths.push({ wch: Math.min(max + 2, 60) });
  }
  return widths;
}

/**
 * Extract period labels from the periods array.
 */
function periodLabels(periods) {
  return periods.map(p => p.period_label || p.bank?.fiscal_year || '?');
}

/**
 * Build the "CAMELS Ratings" sheet — multi-period columns.
 */
function buildRatingsSheet(periods) {
  const labels = periodLabels(periods);
  const rows = [
    ['CAMELS Ratings Summary'],
    [],
    ['Component', ...labels],
  ];

  // Composite row
  rows.push([
    'Composite',
    ...periods.map(p => {
      const c = p.camels_rating;
      const r = c?.composite_rating ?? c?.rating;
      const s = c?.status;
      return r ? `${r} — ${s}` : 'N/A';
    }),
  ]);

  // Individual component rows
  const components = [
    ['C - Capital Adequacy', 'capital'],
    ['A - Asset Quality', 'asset_quality'],
    ['M - Management (Efficiency)', 'management'],
    ['E - Earnings', 'earnings'],
    ['L - Liquidity', 'liquidity'],
  ];

  for (const [label, key] of components) {
    rows.push([
      label,
      ...periods.map(p => {
        const r = p.detailed_ratings?.[key];
        return r?.rating ? `${r.rating} — ${r.status}` : 'N/A';
      }),
    ]);
  }

  // Bank info
  const latest = periods[periods.length - 1];
  const bank = latest?.bank || {};
  rows.push([]);
  rows.push(['Bank', bank.bank_name || 'Unknown']);
  rows.push(['Country', bank.country || 'N/A']);
  rows.push(['Currency', bank.currency || 'XOF']);

  return rows;
}

/**
 * Build the "Key Ratios" sheet — multi-period columns.
 */
function buildRatiosSheet(periods) {
  const labels = periodLabels(periods);

  const sections = [
    { title: 'CAPITAL ADEQUACY', ratios: [
      { label: 'Equity / Assets', key: 'equity_assets', src: 'km' },
      { label: 'Debt / Assets', key: 'debt_assets', src: 'km' },
    ]},
    { title: 'ASSET QUALITY', ratios: [
      { label: 'NPL Ratio', key: 'npl_ratio', src: 'km' },
      { label: 'Coverage Ratio', key: 'coverage_ratio', src: 'km' },
      { label: 'Cost of Risk / Avg Assets', key: 'cost_of_risk_avg_assets', src: 'km' },
    ]},
    { title: 'MANAGEMENT (EFFICIENCY)', ratios: [
      { label: 'Cost-to-Income Ratio', key: 'cost_to_income', src: 'km' },
    ]},
    { title: 'EARNINGS', ratios: [
      { label: 'ROAA', key: 'roaa', src: 'km' },
      { label: 'ROAE', key: 'roae', src: 'km' },
      { label: 'NII / Avg Assets', key: 'net_interest_income_avg_assets', src: 'bank' },
      { label: 'Non-Interest Inc / Avg Assets', key: 'non_interest_income_avg_assets', src: 'bank' },
      { label: 'OpEx / Avg Assets', key: 'opex_avg_assets', src: 'bank' },
      { label: 'Tax / Avg Assets', key: 'tax_expenses_avg_assets', src: 'bank' },
    ]},
    { title: 'LIQUIDITY', ratios: [
      { label: 'Liquid Assets / Total Assets', key: 'liquid_assets_total_assets', src: 'km' },
      { label: 'Gross Loans / Deposits', key: 'loans_deposits', src: 'km' },
    ]},
  ];

  const rows = [
    ['Key Ratios by CAMELS Category'],
    [],
    ['Ratio', ...labels],
  ];

  for (const section of sections) {
    rows.push([]);
    rows.push([section.title]);
    for (const r of section.ratios) {
      rows.push([
        r.label,
        ...periods.map(p => {
          const val = r.src === 'km' ? p.key_metrics?.[r.key] : p.bank?.[r.key];
          return pct(val);
        }),
      ]);
    }
  }

  return rows;
}

/**
 * Build the "Key Financials" sheet — multi-period columns with absolute numbers.
 */
function buildFinancialsSheet(periods) {
  const labels = periodLabels(periods);

  const items = [
    ['Total Assets', 'total_assets'],
    ['Gross Loans', 'gross_loans'],
    ['Total Deposits', 'deposits'],
    ['Total Equity', 'total_equity'],
    ['Interest Income', 'interest_income'],
    ['Interest Expenses', 'interest_expenses'],
    ['Net Interest Income', 'net_interest_income'],
    ['Operating Income (PNB)', 'operating_income'],
    ['Operating Expenses', 'operating_expenses'],
    ['Provision Expenses', 'provision_expenses'],
    ['Net Income', 'net_income'],
  ];

  const rows = [
    ['Key Financials'],
    [],
    ['Item', ...labels],
  ];

  for (const [label, key] of items) {
    rows.push([
      label,
      ...periods.map(p => num(p.bank?.[key])),
    ]);
  }

  return rows;
}

/**
 * Build the "Analysis" sheet — latest period only.
 */
function buildAnalysisSheet(periods) {
  const latest = periods[periods.length - 1];
  const analysis = latest?.analysis || {};
  const label = latest?.period_label || latest?.bank?.fiscal_year || '';

  const rows = [
    [`CAMELS Analysis — ${label}`],
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

  for (const [lbl, text] of sections) {
    rows.push([lbl, text || 'No analysis available']);
  }

  return rows;
}

/**
 * Export analysis results to an Excel (.xlsx) file and trigger a download.
 * Supports multi-period (all_periods) and single-period result formats.
 *
 * @param {Object} result - The full analysis result object from the API.
 */
export function exportToExcel(result) {
  if (!result) return;

  const periods = result.all_periods || [result];
  const wb = XLSX.utils.book_new();

  // --- Sheet 1: CAMELS Ratings ---
  const ratingsData = buildRatingsSheet(periods);
  const wsRatings = XLSX.utils.aoa_to_sheet(ratingsData);
  wsRatings['!cols'] = autoWidth(ratingsData);
  XLSX.utils.book_append_sheet(wb, wsRatings, 'CAMELS Ratings');

  // --- Sheet 2: Key Ratios ---
  const ratiosData = buildRatiosSheet(periods);
  const wsRatios = XLSX.utils.aoa_to_sheet(ratiosData);
  wsRatios['!cols'] = autoWidth(ratiosData);
  XLSX.utils.book_append_sheet(wb, wsRatios, 'Key Ratios');

  // --- Sheet 3: Key Financials ---
  const financialsData = buildFinancialsSheet(periods);
  const wsFinancials = XLSX.utils.aoa_to_sheet(financialsData);
  wsFinancials['!cols'] = autoWidth(financialsData);
  XLSX.utils.book_append_sheet(wb, wsFinancials, 'Key Financials');

  // --- Sheet 4: Analysis ---
  const analysisData = buildAnalysisSheet(periods);
  const wsAnalysis = XLSX.utils.aoa_to_sheet(analysisData);
  wsAnalysis['!cols'] = autoWidth(analysisData);
  for (let r = 3; r < analysisData.length; r++) {
    const cellRef = XLSX.utils.encode_cell({ r, c: 1 });
    if (wsAnalysis[cellRef]) {
      wsAnalysis[cellRef].s = { alignment: { wrapText: true } };
    }
  }
  XLSX.utils.book_append_sheet(wb, wsAnalysis, 'Analysis');

  // --- Generate filename ---
  const latest = periods[periods.length - 1];
  const bankName = latest?.bank?.bank_name || 'Bank';
  const safeName = bankName.replace(/[^a-zA-Z0-9_-]/g, '_');
  const yearRange = periods.length > 1
    ? `${periods[0].period_label || periods[0].bank?.fiscal_year || ''}_${latest.period_label || latest.bank?.fiscal_year || ''}`
    : (latest?.bank?.fiscal_year || '');
  const filename = `CAMELS_${safeName}${yearRange ? '_' + yearRange : ''}.xlsx`;

  XLSX.writeFile(wb, filename);
}
