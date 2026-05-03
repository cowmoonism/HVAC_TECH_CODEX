import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
  activateTechnician,
  getTechnicianDetail,
  parseApiError,
  sendTechnicianSchedule,
  startTelegramRegistration,
  syncTechnicianCalendar,
  type CalendarSyncResult,
  type ScheduleDeliveryResult,
  type TechnicianDetail,
  type TelegramRegistration,
} from "../api/client";
import { canManageTechnicians, canUseScheduleSync } from "../auth/storage";
import { AsyncState } from "../components/AsyncState";

function tomorrowIso() {
  const value = new Date();
  value.setDate(value.getDate() + 1);
  return value.toISOString().slice(0, 10);
}

export function TechnicianDetailPage() {
  const { id } = useParams();
  const [detail, setDetail] = useState<TechnicianDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activationError, setActivationError] = useState("");
  const [activating, setActivating] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<CalendarSyncResult | null>(null);
  const [syncError, setSyncError] = useState("");
  const [startingRegistration, setStartingRegistration] = useState(false);
  const [registrationError, setRegistrationError] = useState("");
  const [registrationResult, setRegistrationResult] = useState<TelegramRegistration | null>(null);
  const [scheduleDate, setScheduleDate] = useState(tomorrowIso());
  const [sendingSchedule, setSendingSchedule] = useState(false);
  const [scheduleResult, setScheduleResult] = useState<ScheduleDeliveryResult | null>(null);
  const [scheduleError, setScheduleError] = useState("");

  function loadDetail(technicianId: string) {
    setLoading(true);
    setError("");
    getTechnicianDetail(technicianId)
      .then(setDetail)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    if (!id) {
      setError("Technician id is missing.");
      setLoading(false);
      return;
    }
    loadDetail(id);
  }, [id]);

  async function handleActivate() {
    if (!id) {
      return;
    }
    setActivating(true);
    setActivationError("");
    try {
      await activateTechnician(id);
      loadDetail(id);
    } catch (err) {
      setActivationError(parseApiError(err));
    } finally {
      setActivating(false);
    }
  }

  async function handleSyncCalendar() {
    if (!id) {
      return;
    }
    setSyncing(true);
    setSyncError("");
    setSyncResult(null);
    try {
      const result = await syncTechnicianCalendar(id, 14);
      setSyncResult(result);
      if (!result.error) {
        loadDetail(id);
      }
    } catch (err) {
      setSyncError(parseApiError(err));
    } finally {
      setSyncing(false);
    }
  }

  async function handleSendSchedule() {
    if (!id) {
      return;
    }
    setSendingSchedule(true);
    setScheduleError("");
    setScheduleResult(null);
    try {
      const result = await sendTechnicianSchedule(id, scheduleDate);
      setScheduleResult(result);
    } catch (err) {
      setScheduleError(parseApiError(err));
    } finally {
      setSendingSchedule(false);
    }
  }

  async function handleStartTelegramRegistration() {
    if (!id) {
      return;
    }
    setStartingRegistration(true);
    setRegistrationError("");
    try {
      const result = await startTelegramRegistration(id);
      setRegistrationResult(result);
      loadDetail(id);
    } catch (err) {
      setRegistrationError(parseApiError(err));
    } finally {
      setStartingRegistration(false);
    }
  }

  return (
    <section className="page-stack">
      <AsyncState loading={loading} error={error}>
        {detail && (
          <>
            <div>
              <span className="eyebrow">Technician</span>
              <div className="page-heading-row">
                <h1>{detail.technician.display_name}</h1>
                {canManageTechnicians() && detail.technician.status !== "ACTIVE" && (
                  <button type="button" onClick={handleActivate} disabled={activating}>
                    {activating ? "Activating..." : "Activate"}
                  </button>
                )}
                {canUseScheduleSync() && detail.technician.google_calendar_id && (
                  <button className="secondary-button" type="button" onClick={handleSyncCalendar} disabled={syncing}>
                    {syncing ? "Syncing..." : "Sync Google Calendar"}
                  </button>
                )}
              </div>
              <p className="subtle">
                {detail.technician.phone || "No phone"} - {detail.technician.email || "No email"} - {detail.technician.status}
              </p>
            </div>

            <section className="panel">
              <h2>Onboarding Checklist</h2>
              {activationError && <div className="panel error-panel compact-panel">{activationError}</div>}
              <div className="checklist">
                <span className={detail.technician.telegram_user_id ? "check-pass" : "check-missing"}>
                  Telegram User ID present
                </span>
                <span className={detail.technician.telegram_group_chat_id ? "check-pass" : "check-missing"}>
                  Telegram Group Chat ID present
                </span>
                <span className={detail.technician.google_calendar_id ? "check-pass" : "check-missing"}>
                  Google Calendar ID present
                </span>
                <span className={["ACTIVE", "ONBOARDING"].includes(detail.technician.status) ? "check-pass" : "check-missing"}>
                  Status ACTIVE or ONBOARDING
                </span>
              </div>
            </section>

            {canManageTechnicians() && (
              <section className="panel">
                <div className="page-heading-row">
                  <h2>Telegram Registration</h2>
                  <button type="button" onClick={handleStartTelegramRegistration} disabled={startingRegistration}>
                    {startingRegistration ? "Preparing..." : "Start Telegram Registration"}
                  </button>
                </div>
                <p className="subtle">
                  Ask the technician to open the private bot link first, then press Complete Registration inside the work group chat.
                </p>
                <div className="checklist">
                  <span className={detail.telegram_registration.telegram_user_id ? "check-pass" : "check-missing"}>
                    Telegram user claimed
                  </span>
                  <span className={detail.telegram_registration.telegram_group_chat_id ? "check-pass" : "check-missing"}>
                    Work group linked
                  </span>
                </div>
                {(registrationResult || detail.telegram_registration.token) && (
                  <div className="panel compact-panel muted-panel">
                    <p><strong>Status:</strong> {(registrationResult ?? detail.telegram_registration).status}</p>
                    {(registrationResult ?? detail.telegram_registration).bot_start_url ? (
                      <p className="subtle">
                        Bot link: <a href={(registrationResult ?? detail.telegram_registration).bot_start_url} target="_blank" rel="noreferrer">{(registrationResult ?? detail.telegram_registration).bot_start_url}</a>
                      </p>
                    ) : (
                      <p className="subtle">Set `TECHNICIAN_BOT_USERNAME` in backend settings to generate a direct bot start link.</p>
                    )}
                    {(registrationResult ?? detail.telegram_registration).token && (
                      <p className="subtle">Registration token: {(registrationResult ?? detail.telegram_registration).token}</p>
                    )}
                    {detail.telegram_registration.telegram_username && (
                      <p className="subtle">Claimed by: @{detail.telegram_registration.telegram_username}</p>
                    )}
                    {detail.telegram_registration.telegram_group_title && (
                      <p className="subtle">Linked group: {detail.telegram_registration.telegram_group_title}</p>
                    )}
                  </div>
                )}
                {registrationError && <div className="panel error-panel compact-panel">{registrationError}</div>}
              </section>
            )}

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

            {canUseScheduleSync() && (
              <section className="panel">
                <h2>Schedule Delivery</h2>
                <div className="inline-controls">
                  <label>
                    Date
                    <input type="date" value={scheduleDate} onChange={(event) => setScheduleDate(event.target.value)} />
                  </label>
                  <button type="button" onClick={handleSendSchedule} disabled={sendingSchedule}>
                    {sendingSchedule ? "Sending..." : "Send Schedule"}
                  </button>
                </div>
                {(scheduleResult || scheduleError) && (
                  <div className={`panel compact-panel ${scheduleResult?.error || scheduleError ? "error-panel" : "muted-panel"}`}>
                    {scheduleResult && (
                      <div className="sync-result-grid">
                        <span>Sent: {scheduleResult.sent ? "Yes" : "No"}</span>
                        <span>Events: {scheduleResult.events_count}</span>
                        <span>Date: {scheduleResult.target_date}</span>
                        {scheduleResult.error && <span>Error: {scheduleResult.error}</span>}
                      </div>
                    )}
                    {scheduleError && <p>{scheduleError}</p>}
                  </div>
                )}
              </section>
            )}

            <section className="panel">
              <h2>Upcoming Events</h2>
              <div className="list-stack">
                {detail.upcoming_calendar_events.map((event) => (
                  <article className="list-item" key={event.id}>
                    <strong>{event.title}</strong>
                    <span>{new Date(event.start_at).toLocaleString()}</span>
                    <span>{event.location || "No location"}</span>
                  </article>
                ))}
                {detail.upcoming_calendar_events.length === 0 && <p className="subtle">No upcoming events.</p>}
              </div>
            </section>

            <section className="panel">
              <h2>Latest Work Reports</h2>
              <div className="list-stack">
                {detail.latest_work_reports.map((report) => (
                  <article className="list-item" key={report.id}>
                    <strong>{report.job_number || "No job number"}</strong>
                    <span>{report.report_date}</span>
                    <span>{report.amount ? `$${report.amount}` : "Amount hidden"}</span>
                  </article>
                ))}
                {detail.latest_work_reports.length === 0 && <p className="subtle">No reports yet.</p>}
              </div>
            </section>

            {detail.latest_expenses && (
              <section className="panel">
                <h2>Latest Expenses</h2>
                <div className="list-stack">
                  {detail.latest_expenses.map((expense) => (
                    <article className="list-item" key={expense.id}>
                      <strong>{expense.expense_type}</strong>
                      <span>{expense.expense_date}</span>
                      <span>${expense.amount}</span>
                    </article>
                  ))}
                  {detail.latest_expenses.length === 0 && <p className="subtle">No expenses yet.</p>}
                </div>
              </section>
            )}

            {detail.latest_contracts && (
              <section className="panel">
                <h2>Latest Contracts</h2>
                <div className="list-stack">
                  {detail.latest_contracts.map((contract) => (
                    <article className="list-item" key={contract.id}>
                      <strong>{contract.contract_number}</strong>
                      <span>{contract.customer_name}</span>
                      <span>${contract.total}</span>
                    </article>
                  ))}
                  {detail.latest_contracts.length === 0 && <p className="subtle">No contracts yet.</p>}
                </div>
              </section>
            )}
          </>
        )}
      </AsyncState>
    </section>
  );
}
