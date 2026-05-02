import { Navigate, Outlet } from "react-router-dom";
import { getAuthToken } from "../auth/storage";

export function RequireAuth() {
  if (!getAuthToken()) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
