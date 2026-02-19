import { useState } from 'react';

/**
 * Post-extraction modal — asks the user for CAR and NPL total amount
 * per period, since these are often not available in BS/IS.
 */
function InputModal({ periods, onConfirm, onSkip }) {
  const [inputs, setInputs] = useState({});

  const set = (pi, field, val) => {
    setInputs(prev => ({
      ...prev,
      [pi]: { ...prev[pi], [field]: val },
    }));
  };

  const handleConfirm = () => {
    const overrides = {};
    for (const [pi, vals] of Object.entries(inputs)) {
      const o = {};
      if (vals.car && !isNaN(parseFloat(vals.car))) {
        o.car = parseFloat(vals.car) / 100;
      }
      if (vals.npl_amount && !isNaN(parseFloat(vals.npl_amount))) {
        o.npls_mn = parseFloat(vals.npl_amount);
      }
      if (Object.keys(o).length > 0) {
        overrides[parseInt(pi)] = o;
      }
    }
    onConfirm(overrides);
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <h3>Additional Data Input</h3>
        <p className="modal-desc">
          These values are typically not available in the balance sheet or income statement.
          Enter them if you have access, or skip to proceed with available data.
        </p>

        <div className="modal-periods">
          {periods.map((p, i) => {
            const label = p.period_label || p.bank?.fiscal_year || `Period ${i + 1}`;
            const ccy = p.bank?.currency || 'XOF';
            return (
              <div key={i} className="modal-period">
                <h4 className="modal-period-label">{label}</h4>
                <div className="modal-fields">
                  <div className="modal-field">
                    <label>CAR — Capital Adequacy Ratio (%)</label>
                    <input
                      type="number"
                      step="0.01"
                      placeholder="e.g. 12.5"
                      value={inputs[i]?.car || ''}
                      onChange={e => set(i, 'car', e.target.value)}
                    />
                  </div>
                  <div className="modal-field">
                    <label>NPL Total Amount ({ccy})</label>
                    <input
                      type="number"
                      step="1"
                      placeholder="e.g. 15000"
                      value={inputs[i]?.npl_amount || ''}
                      onChange={e => set(i, 'npl_amount', e.target.value)}
                    />
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        <div className="modal-actions">
          <button className="modal-skip" onClick={onSkip}>
            Skip
          </button>
          <button className="modal-confirm" onClick={handleConfirm}>
            Confirm &amp; Analyze
          </button>
        </div>
      </div>
    </div>
  );
}

export default InputModal;
