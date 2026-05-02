export type UserRole =
  | "OWNER"
  | "ADMIN"
  | "MANAGER"
  | "DISPATCHER"
  | "CALL_CENTER"
  | "ACCOUNTANT"
  | "TECHNICIAN";

const TOKEN_KEY = "auth_token";
const REFRESH_TOKEN_KEY = "refresh_token";
const ROLE_KEY = "user_role";

export function getAuthToken(): string {
  return localStorage.getItem(TOKEN_KEY) ?? "";
}

export function setAuthToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token.trim());
}

export function getRefreshToken(): string {
  return localStorage.getItem(REFRESH_TOKEN_KEY) ?? "";
}

export function setRefreshToken(token: string): void {
  localStorage.setItem(REFRESH_TOKEN_KEY, token.trim());
}

export function clearAuth(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  localStorage.removeItem(ROLE_KEY);
}

export function getUserRole(): UserRole | "" {
  return (localStorage.getItem(ROLE_KEY) ?? "") as UserRole | "";
}

export function setUserRole(role: UserRole): void {
  localStorage.setItem(ROLE_KEY, role);
}

export function isCallCenter(): boolean {
  return getUserRole() === "CALL_CENTER";
}

export function canManageTechnicians(): boolean {
  return ["OWNER", "ADMIN", "MANAGER"].includes(getUserRole());
}

export function canUseScheduleSync(): boolean {
  return ["OWNER", "ADMIN", "MANAGER", "DISPATCHER", "CALL_CENTER"].includes(getUserRole());
}

export function canViewSchedule(): boolean {
  return canUseScheduleSync();
}

export function canViewFinance(): boolean {
  return ["OWNER", "ADMIN", "MANAGER", "DISPATCHER", "ACCOUNTANT"].includes(getUserRole());
}

export function canViewReports(): boolean {
  return ["OWNER", "ADMIN", "MANAGER", "DISPATCHER", "ACCOUNTANT"].includes(getUserRole());
}
