import { useEffect, useState } from "react";
import { getDashboardOverview, type DashboardOverview } from "../api/client";
import { AsyncState } from "../components/AsyncState";

export function DashboardOverviewPage() {
  const [data, setData] = useState<DashboardOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    getDashboardOverview()
      .then(setData)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const metrics = data
    ? [
        ["Active technicians", data.active_technicians_count],
        ["Today's events", data.today_events_count],
        ["Pending reports", data.pending_reports_count],
        ["Contracts generated today", data.contracts_generated_today_count],
        ...(data.today_reported_revenue !== undefined ? [["Reported revenue today", `$${data.today_reported_revenue}`]] : []),
        ...(data.today_expenses_total !== undefined ? [["Expenses today", `$${data.today_expenses_total}`]] : []),
      ]
    : [];

  return (
    <section className="page-stack">
      <div>
        <span className="eyebrow">Operations</span>
        <h1>Dashboard</h1>
      </div>
      <AsyncState loading={loading} error={error}>
        <div className="metric-grid">
          {metrics.map(([label, value]) => (
            <article className="metric-card" key={label}>
              <span>{label}</span>
              <strong>{value}</strong>
            </article>
          ))}
        </div>
      </AsyncState>
    </section>
  );
}
