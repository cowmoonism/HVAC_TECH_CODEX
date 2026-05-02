import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getTechnicians, type Technician } from "../api/client";
import { canManageTechnicians } from "../auth/storage";
import { AsyncState } from "../components/AsyncState";

export function TechniciansPage() {
  const [technicians, setTechnicians] = useState<Technician[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    getTechnicians()
      .then(setTechnicians)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <section className="page-stack">
      <div>
        <span className="eyebrow">Directory</span>
        <div className="page-heading-row">
          <h1>Technicians</h1>
          {canManageTechnicians() && (
            <Link className="button-link" to="/technicians/new">
              Add Technician
            </Link>
          )}
        </div>
      </div>
      <AsyncState loading={loading} error={error}>
        <div className="panel table-panel">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Status</th>
                <th>Phone</th>
                <th>Email</th>
                <th>State</th>
              </tr>
            </thead>
            <tbody>
              {technicians.map((technician) => (
                <tr key={technician.id}>
                  <td>
                    <Link to={`/technicians/${technician.id}`}>{technician.display_name || `${technician.first_name} ${technician.last_name}`}</Link>
                  </td>
                  <td>{technician.status}</td>
                  <td>{technician.phone || "N/A"}</td>
                  <td>{technician.email || "N/A"}</td>
                  <td>{technician.service_state || "N/A"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </AsyncState>
    </section>
  );
}
