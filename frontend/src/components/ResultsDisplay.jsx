function formatHourRange(start, end) {
  const fmt = (h) => {
    if (h === 0 || h === 24) return "12:00 AM";
    if (h < 12) return `${h}:00 AM`;
    if (h === 12) return "12:00 PM";
    return `${h - 12}:00 PM`;
  };
  return `${fmt(start)} – ${fmt(end)}`;
}

export default function ResultsDisplay({ result }) {
  if (!result) {
    return (
      <div className="card">
        <h2>Savings Report</h2>
        <p className="empty-state">
          Add appliances and run optimization to see your savings vs. run-on-arrival scheduling.
        </p>
      </div>
    );
  }

  return (
    <div className="card">
      <h2>Savings Report</h2>

      <div className="savings-grid">
        <div className="stat">
          <div className="label">FIFO baseline</div>
          <div className="value">${result.fifo_total_cost.toFixed(2)}</div>
        </div>
        <div className="stat">
          <div className="label">Optimized</div>
          <div className="value">${result.optimized_total_cost.toFixed(2)}</div>
        </div>
        <div className="stat savings">
          <div className="label">You save</div>
          <div className="value">
            ${result.savings_dollars.toFixed(2)}
            <span style={{ fontSize: "0.75rem", marginLeft: 4 }}>
              ({result.savings_percent}%)
            </span>
          </div>
        </div>
      </div>

      <table className="schedule-table">
        <thead>
          <tr>
            <th>Appliance</th>
            <th>Window</th>
            <th>Cost</th>
          </tr>
        </thead>
        <tbody>
          {result.schedules.map((s) => (
            <tr key={s.task_id}>
              <td>{s.name}</td>
              <td className="mono">{formatHourRange(s.start_hour, s.end_hour)}</td>
              <td className="mono">${s.cost.toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
