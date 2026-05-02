import { FormEvent, useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import {
  getDailySummary,
  getTechnicians,
  getWeeklySummary,
  parseApiError,
  type DailySummary,
  type Technician,
  type WeeklySummary,
} from "../api/client";
import { canViewReports } from "../auth/storage";
import { AsyncState } from "../components/AsyncState";

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

function startOfWeekIso() {
  const value = new Date();
  const day = value.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  value.setDate(value.getDate() + diff);
  return value.toISOString().slice(0, 10);
}

export function ReportsPage() {
  const [technician, setTechnician] = useState("");
  const [technicians, setTechnicians] = useState<Technician[]>([]);
  const [dailyDate, setDailyDate] = useState(todayIso());
  const [weekStart, setWeekStart] = useState(startOfWeekIso());
  const [dailySummary, setDailySummary] = useState<DailySummary | null>(null);
  const [weeklySummary, setWeeklySummary] = useState<WeeklySummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  if (!canViewReports()) {
    return <Navigate to="/dashboard" replace />;
  }

  function loadSummaries(selectedTechnician = technician, selectedDailyDate = dailyDate, selectedWeekStart = weekStart) {
    setLoading(true);
    setError("");
    Promise.all([
      getDailySummary(selectedDailyDate, selectedTechnician),
      getWeeklySummary(selectedWeekStart, selectedTechnician),
    ])
      .then(([daily, weekly]) => {
        setDailySummary(daily);
        setWeeklySummary(weekly);
      })
      .catch((err: Error) => setError(parseApiError(err)))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    getTechnicians()
      .then(setTechnicians)
      .catch(() => setTechnicians([]));
    loadSummaries("", todayIso(), startOfWeekIso());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    loadSummaries();
  }

  return (
    <section className="page-stack">
      <div>
        <span className="eyebrow">Summaries</span>
        <h1>Reports</h1>
      </div>

      <form className="filter-bar" onSubmit={handleSubmit}>
        <label>
          Technician
          <select value={technician} onChange={(event) => setTechnician(event.target.value)}>
            <option value="">All technicians</option>
            {technicians.map((item) => (
              <option key={item.id} value={item.id}>
                {item.display_name || `${item.first_name} ${item.last_name}`}
              </option>
            ))}
          </select>
        </label>
        <label>
          Daily summary date
          <input type="date" value={dailyDate} onChange={(event) => setDailyDate(event.target.value)} />
        </label>
        <label>
          Weekly summary start
          <input type="date" value={weekStart} onChange={(event) => setWeekStart(event.target.value)} />
        </label>
        <button type="submit">Apply</button>
      </form>

      <AsyncState loading={loading} error={error}>
        {dailySummary && (
          <section className="page-stack">
            <div>
              <span className="eyebrow">Daily</span>
              <h2>{dailySummary.date}</h2>
            </div>
            <div className="metric-grid">
              <article className="metric-card">
                <span>Reports</span>
                <strong>{dailySummary.reports_count}</strong>
              </article>
              <article className="metric-card">
                <span>Revenue</span>
                <strong>${dailySummary.total_revenue}</strong>
              </article>
              <article className="metric-card">
                <span>Expenses</span>
                <strong>${dailySummary.expenses_total}</strong>
              </article>
              <article className="metric-card">
                <span>Net</span>
                <strong>${dailySummary.net_total}</strong>
              </article>
            </div>

            <section className="panel">
              <h2>Reviews</h2>
              <div className="sync-result-grid">
                <span>Google Yes: {dailySummary.reviews.google_review_yes}</span>
                <span>Groupon Yes: {dailySummary.reviews.groupon_review_yes}</span>
                <span>Maintenance Yes: {dailySummary.reviews.yearly_maintenance_plan_yes}</span>
              </div>
            </section>

            <section className="panel table-panel">
              <table>
                <thead>
                  <tr>
                    <th>Payment Type</th>
                    <th>Reports</th>
                    <th>Revenue</th>
                  </tr>
                </thead>
                <tbody>
                  {dailySummary.by_payment_type.map((item) => (
                    <tr key={item.payment_type}>
                      <td>{item.payment_type}</td>
                      <td>{item.reports_count}</td>
                      <td>${item.total_revenue}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>

            <section className="panel table-panel">
              <table>
                <thead>
                  <tr>
                    <th>Technician</th>
                    <th>Job</th>
                    <th>Address</th>
                    <th>Payment</th>
                    <th>Amount</th>
                    <th>Closed By</th>
                  </tr>
                </thead>
                <tbody>
                  {dailySummary.reports.map((report) => (
                    <tr key={report.id}>
                      <td>{report.technician_display_name}</td>
                      <td>{report.job_number || "N/A"}</td>
                      <td>{report.address || "N/A"}</td>
                      <td>{report.payment_type}</td>
                      <td>${report.amount}</td>
                      <td>{report.closed_by}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          </section>
        )}

        {weeklySummary && (
          <section className="page-stack">
            <div>
              <span className="eyebrow">Weekly</span>
              <h2>
                {weeklySummary.week_start} to {weeklySummary.week_end}
              </h2>
            </div>
            <div className="metric-grid">
              <article className="metric-card">
                <span>Reports</span>
                <strong>{weeklySummary.reports_count}</strong>
              </article>
              <article className="metric-card">
                <span>Revenue</span>
                <strong>${weeklySummary.total_revenue}</strong>
              </article>
              <article className="metric-card">
                <span>Expenses</span>
                <strong>${weeklySummary.expenses_total}</strong>
              </article>
              <article className="metric-card">
                <span>Net</span>
                <strong>${weeklySummary.net_total}</strong>
              </article>
            </div>

            <section className="panel">
              <h2>Review Totals</h2>
              <div className="sync-result-grid">
                <span>Google Yes: {weeklySummary.reviews.google_review_yes}</span>
                <span>Groupon Yes: {weeklySummary.reviews.groupon_review_yes}</span>
                <span>Maintenance Yes: {weeklySummary.reviews.yearly_maintenance_plan_yes}</span>
              </div>
            </section>

            <section className="panel table-panel">
              <table>
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Reports</th>
                    <th>Revenue</th>
                    <th>Expenses</th>
                    <th>Net</th>
                  </tr>
                </thead>
                <tbody>
                  {weeklySummary.by_day.map((day) => (
                    <tr key={day.date}>
                      <td>{day.date}</td>
                      <td>{day.reports_count}</td>
                      <td>${day.total_revenue}</td>
                      <td>${day.expenses_total}</td>
                      <td>${day.net_total}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>

            <section className="panel table-panel">
              <table>
                <thead>
                  <tr>
                    <th>Payment Type</th>
                    <th>Reports</th>
                    <th>Revenue</th>
                  </tr>
                </thead>
                <tbody>
                  {weeklySummary.by_payment_type.map((item) => (
                    <tr key={item.payment_type}>
                      <td>{item.payment_type}</td>
                      <td>{item.reports_count}</td>
                      <td>${item.total_revenue}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>

            {weeklySummary.by_technician && (
              <section className="panel table-panel">
                <table>
                  <thead>
                    <tr>
                      <th>Technician</th>
                      <th>Reports</th>
                      <th>Revenue</th>
                      <th>Expenses</th>
                      <th>Net</th>
                    </tr>
                  </thead>
                  <tbody>
                    {weeklySummary.by_technician.map((item) => (
                      <tr key={item.technician}>
                        <td>{item.technician_display_name}</td>
                        <td>{item.reports_count}</td>
                        <td>${item.total_revenue}</td>
                        <td>${item.expenses_total}</td>
                        <td>${item.net_total}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </section>
            )}
          </section>
        )}
      </AsyncState>
    </section>
  );
}
