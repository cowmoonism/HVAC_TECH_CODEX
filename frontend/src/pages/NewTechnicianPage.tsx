import { FormEvent, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { createTechnician, parseApiError, type TechnicianPayload } from "../api/client";
import { canManageTechnicians } from "../auth/storage";

const initialForm: TechnicianPayload = {
  first_name: "",
  last_name: "",
  display_name: "",
  phone: "",
  email: "",
  status: "ONBOARDING",
  service_state: "",
  timezone: "America/Los_Angeles",
  telegram_user_id: "",
  telegram_username: "",
  telegram_group_chat_id: "",
  google_calendar_id: "",
  notes: "",
};

export function NewTechnicianPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState<TechnicianPayload>(initialForm);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  if (!canManageTechnicians()) {
    return <Navigate to="/technicians" replace />;
  }

  function updateField(field: keyof TechnicianPayload, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    const payload = Object.fromEntries(
      Object.entries(form).map(([key, value]) => [key, typeof value === "string" ? value.trim() : value]),
    ) as TechnicianPayload;

    try {
      const technician = await createTechnician(payload);
      navigate(`/technicians/${technician.id}`);
    } catch (err) {
      setError(parseApiError(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="page-stack">
      <div>
        <span className="eyebrow">Onboarding</span>
        <h1>Add Technician</h1>
      </div>

      <form className="onboarding-form" onSubmit={handleSubmit}>
        <section className="panel form-section">
          <h2>Basic Info</h2>
          <div className="form-grid">
            <label>
              First name
              <input value={form.first_name} onChange={(event) => updateField("first_name", event.target.value)} required />
            </label>
            <label>
              Last name
              <input value={form.last_name} onChange={(event) => updateField("last_name", event.target.value)} required />
            </label>
            <label>
              Display name
              <input value={form.display_name} onChange={(event) => updateField("display_name", event.target.value)} />
            </label>
            <label>
              Phone
              <input value={form.phone} onChange={(event) => updateField("phone", event.target.value)} />
            </label>
            <label>
              Email
              <input type="email" value={form.email} onChange={(event) => updateField("email", event.target.value)} />
            </label>
            <label>
              Status
              <select value={form.status} onChange={(event) => updateField("status", event.target.value)}>
                <option value="ONBOARDING">ONBOARDING</option>
                <option value="ACTIVE">ACTIVE</option>
                <option value="INACTIVE">INACTIVE</option>
                <option value="SUSPENDED">SUSPENDED</option>
              </select>
            </label>
            <label>
              Service state
              <input maxLength={2} value={form.service_state} onChange={(event) => updateField("service_state", event.target.value.toUpperCase())} />
            </label>
            <label>
              Timezone
              <input value={form.timezone} onChange={(event) => updateField("timezone", event.target.value)} required />
            </label>
          </div>
        </section>

        <section className="panel form-section">
          <h2>Telegram Integration</h2>
          <div className="form-grid">
            <label>
              Telegram user ID
              <input value={form.telegram_user_id} onChange={(event) => updateField("telegram_user_id", event.target.value)} />
            </label>
            <label>
              Telegram username
              <input value={form.telegram_username} onChange={(event) => updateField("telegram_username", event.target.value)} />
            </label>
            <label>
              Telegram group chat ID
              <input value={form.telegram_group_chat_id} onChange={(event) => updateField("telegram_group_chat_id", event.target.value)} />
            </label>
          </div>
        </section>

        <section className="panel form-section">
          <h2>Google Calendar</h2>
          <label>
            Google Calendar ID
            <input value={form.google_calendar_id} onChange={(event) => updateField("google_calendar_id", event.target.value)} />
          </label>
        </section>

        <section className="panel form-section">
          <h2>Notes</h2>
          <label>
            Notes
            <textarea value={form.notes} onChange={(event) => updateField("notes", event.target.value)} rows={5} />
          </label>
        </section>

        {error && <div className="panel error-panel">{error}</div>}

        <div className="form-actions">
          <button type="submit" disabled={submitting}>
            {submitting ? "Creating..." : "Create Technician"}
          </button>
        </div>
      </form>
    </section>
  );
}
