import * as XLSX from 'xlsx';

function pct(val) {
  if (val === null || val === undefined) return 'N/A';
  return `${(val * 100).toFixed(2)}%`;
}

function num(val) {
  if (val === null || val === undefined) return '-';
  return val.toLocaleString();
}

function negNum(val) {
  if (val === null || val === undefined) return '-';
  return `(${Math.abs(val).toLocaleString()})`;
}

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

function labels(periods) {
  return periods.map(p => p.period_label || p.bank?.fiscal_year || '?');
}

/** Sheet 1: CAMELS Ratings */
function buildRatingsSheet(periods) {
  const hdrs = labels(periods);
  const rows = [
    ['CAMELS Ratings Summary'],
    [],
    ['Component', ...hdrs],
    ['Composite', ...periods.map(p => {
      const c = p.camels_rating;
      const r = c?.composite_rating ?? c?.rating;
      return r ? `${r} — ${c?.status}` : 'N/A';
    })],
  ];
  for (const [label, key] of [
    ['C - Capital', 'capital'],
    ['A - Asset Quality', 'asset_quality'],
    ['M - Management', 'management'],
    ['E - Earnings', 'earnings'],
    ['L - Liquidity', 'liquidity'],
  ]) {
    rows.push([label, ...periods.map(p => {
      const r = p.detailed_ratings?.[key];
      return r?.rating ? `${r.rating} — ${r.status}` : 'N/A';
    })]);
  }

  const latest = periods[periods.length - 1];
  const bank = latest?.bank || {};
  rows.push([], ['Bank', bank.bank_name || 'Unknown'],
    ['Country', bank.country || 'N/A'], ['Currency', bank.currency || 'XOF']);
  return rows;
}

/** Sheet 2: Financials — Balance Sheet + Income Statement + Growth */
function buildFinancialsSheet(periods) {
  const hdrs = labels(periods);
  const rows = [
    ['Financial Statements'],
    [],
    ['Balance Sheet', ...hdrs],
  ];

  // Balance sheet items
  const bsItems = [
    ['Total Assets', 'total_assets'],
    ['Total Liabilities', 'total_liabilities'],
    ["Shareholder's Equity", 'total_equity'],
    ['Cash & Cash Equivalent', 'cash_reserves_requirements'],
    ['Investment Securities', 'investment_securities'],
    ['Gross Loans', 'gross_loans'],
    ['Customer Deposits', 'deposits'],
    ['Borrowings', 'short_term_borrowings'],
    ['Long-Term Debt', 'long_term_debt'],
  ];
  const bsNeg = [['Loan Loss Provisions', 'loan_loss_provisions']];

  for (const [label, key] of bsItems) {
    rows.push([label, ...periods.map(p => num(p.bank?.[key]))]);
  }
  for (const [label, key] of bsNeg) {
    rows.push([label, ...periods.map(p => negNum(p.bank?.[key]))]);
  }

  // Income statement
  rows.push([], ['Income Statement', ...hdrs]);
  rows.push(['Net Interest Income', ...periods.map(p => num(p.bank?.net_interest_income))]);
  rows.push(['Non-Interest Income', ...periods.map(p => {
    const oi = p.bank?.operating_income;
    const nii = p.bank?.net_interest_income;
    return (oi != null && nii != null) ? num(oi - nii) : '-';
  })]);
  rows.push(['Operating Expenses', ...periods.map(p => negNum(p.bank?.operating_expenses))]);
  rows.push(['Cost of Risk', ...periods.map(p => negNum(p.bank?.provision_expenses))]);
  rows.push(['Net Profit', ...periods.map(p => num(p.bank?.net_income))]);

  // Growth
  if (periods.length > 1) {
    rows.push([], ['Growth', ...hdrs]);
    for (const [label, key] of [
      ['Assets Growth', 'total_assets'],
      ['Gross Loans', 'gross_loans'],
      ['Deposits', 'deposits'],
      ["Shareholders' Equity", 'total_equity'],
    ]) {
      rows.push([label, ...periods.map((p, i) => {
        if (i === 0) return '—';
        const prev = periods[i - 1].bank?.[key];
        const curr = p.bank?.[key];
        return (curr != null && prev != null && prev !== 0)
          ? pct((curr - prev) / Math.abs(prev)) : 'N/A';
      })]);
    }
  }

  return rows;
}

/** Sheet 3: Key Ratios */
function buildRatiosSheet(periods) {
  const hdrs = labels(periods);
  const sections = [
    { title: 'SOLVENCY RATIOS', ratios: [
      { label: 'CAR - Regulatory', key: 'car', src: 'km' },
      { label: 'Equity / Assets', key: 'equity_assets', src: 'km' },
    ]},
    { title: 'ASSET QUALITY', ratios: [
      { label: 'NPL Ratio', key: 'npl_ratio', src: 'km' },
      { label: 'Coverage Ratio', key: 'coverage_ratio', src: 'km' },
    ]},
    { title: 'PROFITABILITY', ratios: [
      { label: 'ROAA', key: 'roaa', src: 'km' },
      { label: 'ROAE', key: 'roae', src: 'km' },
      { label: 'Cost to Income Ratio', key: 'cost_to_income', src: 'km' },
    ]},
    { title: 'LIQUIDITY', ratios: [
      { label: 'Loans/Deposits', key: 'loans_deposits', src: 'km' },
      { label: 'Liquid Assets/Total Assets', key: 'liquid_assets_total_assets', src: 'km' },
    ]},
  ];

  const rows = [['Key Ratios'], [], ['Ratio', ...hdrs]];
  for (const section of sections) {
    rows.push([], [section.title]);
    for (const r of section.ratios) {
      rows.push([r.label, ...periods.map(p => {
        const val = r.src === 'km' ? p.key_metrics?.[r.key] : p.bank?.[r.key];
        return pct(val);
      })]);
    }
  }
  return rows;
}

/** Sheet 4: Analysis */
function buildAnalysisSheet(periods) {
  const latest = periods[periods.length - 1];
  const analysis = latest?.analysis || {};
  const label = latest?.period_label || latest?.bank?.fiscal_year || '';

  const rows = [[`CAMELS Analysis — ${label}`], [], ['Component', 'Analysis']];
  for (const [title, key] of [
    ['Capitalization', 'capital'],
    ['Asset Quality', 'asset_quality'],
    ['Management & Efficiency', 'management'],
    ['Earnings & Profitability', 'earnings'],
    ['Liquidity & Funding', 'liquidity'],
    ['Composite Assessment', 'composite'],
  ]) {
    const data = analysis[key];
    // Handle bullet arrays or legacy strings
    const text = Array.isArray(data) ? data.join('\n') : (data || 'No analysis available');
    rows.push([title, text]);
  }
  return rows;
}

/**
 * Export analysis results to an Excel (.xlsx) file and trigger a download.
 */
export function exportToExcel(result) {
  if (!result) return;

  const periods = result.all_periods || [result];
  const wb = XLSX.utils.book_new();

  const sheets = [
    ['CAMELS Ratings', buildRatingsSheet(periods)],
    ['Financials', buildFinancialsSheet(periods)],
    ['Key Ratios', buildRatiosSheet(periods)],
    ['Analysis', buildAnalysisSheet(periods)],
  ];

  for (const [name, data] of sheets) {
    const ws = XLSX.utils.aoa_to_sheet(data);
    ws['!cols'] = autoWidth(data);
    XLSX.utils.book_append_sheet(wb, ws, name);
  }

  const latest = periods[periods.length - 1];
  const bankName = latest?.bank?.bank_name || 'Bank';
  const safeName = bankName.replace(/[^a-zA-Z0-9_-]/g, '_');
  const yearRange = periods.length > 1
    ? `${periods[0].period_label || periods[0].bank?.fiscal_year || ''}_${latest.period_label || latest.bank?.fiscal_year || ''}`
    : (latest?.bank?.fiscal_year || '');
  const filename = `CAMELS_${safeName}${yearRange ? '_' + yearRange : ''}.xlsx`;

  XLSX.writeFile(wb, filename);
}
