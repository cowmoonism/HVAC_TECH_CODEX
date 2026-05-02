import { FormEvent, useState } from "react";
import { Navigate } from "react-router-dom";
import { getFinanceSummary, type FinanceSummary } from "../api/client";
import { canViewFinance } from "../auth/storage";
import { AsyncState } from "../components/AsyncState";

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

export function FinancePage() {
  const [technician, setTechnician] = useState("");
  const [startDate, setStartDate] = useState(todayIso());
  const [endDate, setEndDate] = useState(todayIso());
  const [summary, setSummary] = useState<FinanceSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  if (!canViewFinance()) {
    return <Navigate to="/dashboard" replace />;
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");
    getFinanceSummary({ technician, start_date: startDate, end_date: endDate })
      .then(setSummary)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }

  return (
    <section className="page-stack">
      <div>
        <span className="eyebrow">Financials</span>
        <h1>Finance Summary</h1>
      </div>
      <form className="filter-bar" onSubmit={handleSubmit}>
        <label>
          Technician ID
          <input value={technician} onChange={(event) => setTechnician(event.target.value)} placeholder="Optional" />
        </label>
        <label>
          Start date
          <input type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} required />
        </label>
        <label>
          End date
          <input type="date" value={endDate} onChange={(event) => setEndDate(event.target.value)} required />
        </label>
        <button type="submit">Run</button>
      </form>
      <AsyncState loading={loading} error={error}>
        {summary && (
          <>
            <div className="metric-grid">
              <article className="metric-card">
                <span>Total revenue</span>
                <strong>${summary.total_revenue}</strong>
              </article>
              <article className="metric-card">
                <span>Total expenses</span>
                <strong>${summary.total_expenses}</strong>
              </article>
              <article className="metric-card">
                <span>Net</span>
                <strong>${summary.net}</strong>
              </article>
              <article className="metric-card">
                <span>Reports / Expenses</span>
                <strong>
                  {summary.reports_count} / {summary.expenses_count}
                </strong>
              </article>
            </div>

            {summary.by_technician && (
              <div className="panel table-panel">
                <table>
                  <thead>
                    <tr>
                      <th>Technician</th>
                      <th>Revenue</th>
                      <th>Expenses</th>
                      <th>Net</th>
                      <th>Reports</th>
                      <th>Expenses Count</th>
                    </tr>
                  </thead>
                  <tbody>
                    {summary.by_technician.map((row) => (
                      <tr key={row.technician}>
                        <td>{row.technician_display_name}</td>
                        <td>${row.total_revenue}</td>
                        <td>${row.total_expenses}</td>
                        <td>${row.net}</td>
                        <td>{row.reports_count}</td>
                        <td>{row.expenses_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
        {!summary && !loading && <div className="panel muted-panel">Choose a date range and run the summary.</div>}
      </AsyncState>
    </section>
  );
}
