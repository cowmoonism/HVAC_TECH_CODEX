import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { canViewFinance, canViewReports, canViewSchedule, clearAuth, getUserRole } from "../auth/storage";

const navItems = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/technicians", label: "Technicians" },
  { to: "/schedule", label: "Schedule", isVisible: canViewSchedule },
  { to: "/reports", label: "Reports", isVisible: canViewReports },
  { to: "/finance", label: "Finance", isVisible: canViewFinance },
];

export function AppLayout() {
  const navigate = useNavigate();
  const role = getUserRole() || "No role set";

  function handleLogout() {
    clearAuth();
    navigate("/login");
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">HV</span>
          <div>
            <strong>HVAC Ops</strong>
            <span>Dashboard</span>
          </div>
        </div>
        <nav className="nav-list" aria-label="Main navigation">
          {navItems
            .filter((item) => (item.isVisible ? item.isVisible() : true))
            .map((item) => (
              <NavLink key={item.to} to={item.to}>
                {item.label}
              </NavLink>
            ))}
        </nav>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <div>
            <span className="eyebrow">Current Role</span>
            <strong>{role}</strong>
          </div>
          <button className="secondary-button" type="button" onClick={handleLogout}>
            Log out
          </button>
        </header>
        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
