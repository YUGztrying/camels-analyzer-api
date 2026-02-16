import { fmtNum } from '../utils/formatters';

function Row({ label, value, negative }) {
  const display = value != null
    ? (negative ? `(${fmtNum(Math.abs(value))})` : fmtNum(value))
    : '-';
  return <tr><td>{label}</td><td>{display}</td></tr>;
}

function SectionTitle({ children }) {
  return <tr className="section-title"><td colSpan="2"><strong>{children}</strong></td></tr>;
}

function TotalRow({ label, value }) {
  return <tr className="total-row"><td><strong>{label}</strong></td><td><strong>{fmtNum(value)}</strong></td></tr>;
}

function SubtotalRow({ label, value }) {
  return <tr className="subtotal-row"><td><strong>{label}</strong></td><td><strong>{fmtNum(value)}</strong></td></tr>;
}

export function BalanceSheet({ bank }) {
  if (!bank) return null;
  return (
    <div className="financial-statement">
      <h4 className="statement-header">Balance Sheet — {bank.fiscal_year}</h4>
      <table className="statement-table">
        <thead>
          <tr><th>{bank.currency || 'XOF'} mn</th><th>{bank.fiscal_year}</th></tr>
        </thead>
        <tbody>
          <SectionTitle>ASSETS</SectionTitle>
          <Row label="Cash & Reserve Requirements" value={bank.cash_reserves_requirements} />
          <Row label="Due from Banks" value={bank.due_from_banks} />
          <Row label="Investment Securities" value={bank.investment_securities} />
          <Row label="Gross Loans" value={bank.gross_loans} />
          <Row label="Loan Loss Provisions" value={bank.loan_loss_provisions} negative />
          <Row label="Foreclosed Assets" value={bank.foreclosed_assets} />
          <Row label="Fixed Assets" value={bank.fixed_assets} />
          <Row label="Other Assets" value={bank.other_assets} />
          <TotalRow label="Total Assets" value={bank.total_assets} />

          <SectionTitle>LIABILITIES</SectionTitle>
          <Row label="Customer Deposits" value={bank.deposits} />
          <Row label="Short-Term Borrowings" value={bank.short_term_borrowings} />
          <Row label="Long-Term Debt" value={bank.long_term_debt} />
          <Row label="Interbank Liabilities" value={bank.interbank_liabilities} />
          <Row label="Other Liabilities" value={bank.other_liabilities} />
          <TotalRow label="Total Liabilities" value={bank.total_liabilities} />

          <SectionTitle>EQUITY</SectionTitle>
          <Row label="Paid-in Capital" value={bank.paid_in_capital} />
          <Row label="Reserves" value={bank.reserves} />
          <Row label="Retained Earnings" value={bank.retained_earnings} />
          <Row label="Net Profit" value={bank.net_profit} />
          <TotalRow label="Total Equity" value={bank.total_equity} />
        </tbody>
      </table>
    </div>
  );
}

export function IncomeStatement({ bank }) {
  if (!bank) return null;
  return (
    <div className="financial-statement">
      <h4 className="statement-header">Income Statement — {bank.fiscal_year}</h4>
      <table className="statement-table">
        <thead>
          <tr><th>{bank.currency || 'XOF'} mn</th><th>{bank.fiscal_year}</th></tr>
        </thead>
        <tbody>
          <Row label="Interest Income" value={bank.interest_income} />
          <Row label="Interest Expenses" value={bank.interest_expenses} negative />
          <SubtotalRow label="Net Interest Income" value={bank.net_interest_income} />

          <Row label="Fees & Commissions" value={bank.fees_commissions || bank.non_interest_income_commissions} />
          <Row label="Other Revenues" value={bank.other_revenues || bank.other_net_income} />
          {bank.operating_income && <SubtotalRow label="Operating Income" value={bank.operating_income} />}

          <Row label="Operating Expenses" value={bank.operating_expenses} negative />
          {bank.operating_profit && <SubtotalRow label="Operating Profit" value={bank.operating_profit} />}

          <Row label="Provision Expenses (ECL)" value={bank.provision_expenses} negative />
          <Row label="Income Tax" value={bank.income_tax} negative />
          <TotalRow label="Net Income" value={bank.net_income} />
        </tbody>
      </table>
    </div>
  );
}
