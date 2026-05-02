import { Navigate, Route, Routes } from "react-router-dom";
import { AppLayout } from "./components/AppLayout";
import { RequireAuth } from "./components/RequireAuth";
import { DashboardOverviewPage } from "./pages/DashboardOverviewPage";
import { FinancePage } from "./pages/FinancePage";
import { LoginPage } from "./pages/LoginPage";
import { NewTechnicianPage } from "./pages/NewTechnicianPage";
import { ReportsPage } from "./pages/ReportsPage";
import { SchedulePage } from "./pages/SchedulePage";
import { TechnicianDetailPage } from "./pages/TechnicianDetailPage";
import { TechniciansPage } from "./pages/TechniciansPage";

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<RequireAuth />}>
        <Route element={<AppLayout />}>
          <Route path="/dashboard" element={<DashboardOverviewPage />} />
          <Route path="/technicians" element={<TechniciansPage />} />
          <Route path="/technicians/new" element={<NewTechnicianPage />} />
          <Route path="/technicians/:id" element={<TechnicianDetailPage />} />
          <Route path="/schedule" element={<SchedulePage />} />
          <Route path="/reports" element={<ReportsPage />} />
          <Route path="/finance" element={<FinancePage />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
