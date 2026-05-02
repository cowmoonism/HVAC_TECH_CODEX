import { FormEvent, useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import {
  getSchedule,
  getTechnicians,
  parseApiError,
  syncTechnicianCalendar,
  type CalendarEvent,
  type CalendarSyncResult,
  type Technician,
} from "../api/client";
import { canUseScheduleSync, canViewSchedule } from "../auth/storage";
import { AsyncState } from "../components/AsyncState";

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

export function SchedulePage() {
  const [technician, setTechnician] = useState("");
  const [technicians, setTechnicians] = useState<Technician[]>([]);
  const [startDate, setStartDate] = useState(todayIso());
  const [endDate, setEndDate] = useState(todayIso());
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<CalendarSyncResult | null>(null);
  const [syncError, setSyncError] = useState("");

  if (!canViewSchedule()) {
    return <Navigate to="/dashboard" replace />;
  }

  function loadSchedule() {
    setLoading(true);
    setError("");
    getSchedule({ technician, start_date: startDate, end_date: endDate })
      .then((response) => setEvents(response.events))
      .catch((err: Error) => setError(parseApiError(err)))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    getTechnicians()
      .then(setTechnicians)
      .catch(() => setTechnicians([]));
    loadSchedule();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    loadSchedule();
  }

  async function handleSyncSelectedTechnician() {
    if (!technician) {
      return;
    }
    setSyncing(true);
    setSyncError("");
    setSyncResult(null);
    try {
      const result = await syncTechnicianCalendar(technician, 14);
      setSyncResult(result);
      if (!result.error) {
        loadSchedule();
      }
    } catch (err) {
      setSyncError(parseApiError(err));
    } finally {
      setSyncing(false);
    }
  }

  return (
    <section className="page-stack">
      <div>
        <span className="eyebrow">Calendar</span>
        <h1>Schedule</h1>
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
          Start date
          <input type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} />
        </label>
        <label>
          End date
          <input type="date" value={endDate} onChange={(event) => setEndDate(event.target.value)} />
        </label>
        <button type="submit">Apply</button>
        {canUseScheduleSync() && technician && (
          <button className="secondary-button" type="button" onClick={handleSyncSelectedTechnician} disabled={syncing}>
            {syncing ? "Syncing..." : "Sync Selected Technician"}
          </button>
        )}
      </form>

      {(syncResult || syncError) && (
        <section className={`panel ${syncResult?.error || syncError ? "error-panel" : "muted-panel"}`}>
          <h2>Google Calendar Sync</h2>
          {syncResult && (
            <div className="sync-result-grid">
              <span>Created: {syncResult.created}</span>
              <span>Updated: {syncResult.updated}</span>
              <span>Skipped: {syncResult.skipped}</span>
              {syncResult.error && <span>Error: {syncResult.error}</span>}
            </div>
          )}
          {syncError && <p>{syncError}</p>}
        </section>
      )}

      <AsyncState loading={loading} error={error}>
        <div className="panel table-panel">
          <table>
            <thead>
              <tr>
                <th>Start</th>
                <th>Technician</th>
                <th>Title</th>
                <th>Status</th>
                <th>Location</th>
              </tr>
            </thead>
            <tbody>
              {events.map((event) => (
                <tr key={event.id}>
                  <td>{new Date(event.start_at).toLocaleString()}</td>
                  <td>{event.technician_display_name}</td>
                  <td>{event.title}</td>
                  <td>{event.status}</td>
                  <td>{event.location || "N/A"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </AsyncState>
    </section>
  );
}
