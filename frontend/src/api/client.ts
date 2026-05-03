import { clearAuth, getAuthToken, setAuthToken, setRefreshToken, setUserRole, type UserRole } from "../auth/storage";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "");

export type DashboardOverview = {
  active_technicians_count: number;
  today_events_count: number;
  pending_reports_count: number;
  contracts_generated_today_count: number;
  today_reported_revenue?: string;
  today_expenses_total?: string;
};

export type AuthUser = {
  id: number;
  username: string;
  email: string;
  role: UserRole;
};

export type LoginResponse = {
  access: string;
  refresh: string;
  user: AuthUser;
};

export type Technician = {
  id: number;
  first_name: string;
  last_name: string;
  display_name: string;
  phone: string;
  email: string;
  status: string;
  service_state: string;
  timezone: string;
  telegram_user_id?: string;
  telegram_username?: string;
  telegram_group_chat_id?: string;
  google_calendar_id?: string;
  notes?: string;
};

export type TechnicianPayload = {
  first_name: string;
  last_name: string;
  display_name?: string;
  phone?: string;
  email?: string;
  status?: string;
  service_state?: string;
  timezone?: string;
  telegram_user_id?: string;
  telegram_username?: string;
  telegram_group_chat_id?: string;
  google_calendar_id?: string;
  notes?: string;
};

export type CalendarEvent = {
  id: number;
  technician: number;
  technician_display_name: string;
  event_type: string;
  status: string;
  title: string;
  location: string;
  description?: string;
  start_at: string;
  end_at: string;
  timezone: string;
  job_number?: string | null;
  is_report_required: boolean;
};

export type WorkReport = {
  id: number;
  report_date: string;
  job_number: string;
  building_number: string;
  address: string;
  payment_type?: string;
  amount?: string;
  closed_by: string;
  project_description: string;
  comments: string;
  groupon_review: string;
  google_review: string;
  yearly_maintenance_plan: string;
  created_at: string;
};

export type ExpenseReport = {
  id: number;
  expense_date: string;
  expense_type: string;
  amount: string;
  description: string;
  receipt_photo_url: string;
  created_at: string;
};

export type ServiceContract = {
  id: number;
  status: string;
  contract_number: string;
  contract_date: string;
  customer_name: string;
  customer_address: string;
  customer_phone: string;
  project_type: string;
  subtotal: string;
  sales_tax: string;
  total: string;
  pdf_file_url: string;
  pdf_generated_at: string | null;
  created_at: string;
};

export type TechnicianDetail = {
  technician: Technician;
  telegram_registration: TelegramRegistration;
  upcoming_calendar_events: CalendarEvent[];
  latest_work_reports: WorkReport[];
  latest_expenses?: ExpenseReport[];
  latest_contracts?: ServiceContract[];
};

export type TelegramRegistration = {
  status: string;
  token: string;
  telegram_user_id: string;
  telegram_username: string;
  telegram_group_chat_id: string;
  telegram_group_title: string;
  telegram_chat_type: string;
  claimed_at: string | null;
  linked_at: string | null;
  created_at: string | null;
  updated_at: string | null;
  bot_start_url: string;
};

export type ScheduleParams = {
  technician?: string | number;
  start_date?: string;
  end_date?: string;
};

export type ScheduleResponse = {
  start_date: string;
  end_date: string;
  events: CalendarEvent[];
};

export type CalendarSyncResult = {
  technician_id: number | string;
  created: number;
  updated: number;
  skipped: number;
  error?: string;
};

export type ScheduleDeliveryResult = {
  technician_id: number | string;
  target_date: string;
  sent: boolean;
  events_count: number;
  error?: string;
};

export type FinanceSummaryParams = {
  technician?: string | number;
  start_date: string;
  end_date: string;
};

export type FinanceTechnicianGroup = {
  technician: number;
  technician_display_name: string;
  total_revenue: string;
  total_expenses: string;
  net: string;
  reports_count: number;
  expenses_count: number;
};

export type FinanceSummary = {
  start_date: string;
  end_date: string;
  technician?: number;
  total_revenue: string;
  total_expenses: string;
  net: string;
  reports_count: number;
  expenses_count: number;
  by_technician?: FinanceTechnicianGroup[];
};

export type PaymentTypeSummary = {
  payment_type: string;
  reports_count: number;
  total_revenue: string;
};

export type ReviewSummary = {
  google_review_yes: number;
  groupon_review_yes: number;
  yearly_maintenance_plan_yes: number;
};

export type DailySummaryReport = {
  id: number;
  technician: number;
  technician_display_name: string;
  report_date: string;
  job_number: string;
  address: string;
  payment_type: string;
  amount: string;
  closed_by: string;
  google_review: string;
  groupon_review: string;
  yearly_maintenance_plan: string;
};

export type DailySummary = {
  date: string;
  technician: number | null;
  reports_count: number;
  total_revenue: string;
  expenses_total: string;
  net_total: string;
  by_payment_type: PaymentTypeSummary[];
  reviews: ReviewSummary;
  reports: DailySummaryReport[];
};

export type WeeklyDaySummary = {
  date: string;
  reports_count: number;
  total_revenue: string;
  expenses_total: string;
  net_total: string;
};

export type WeeklyTechnicianSummary = {
  technician: number;
  technician_display_name: string;
  reports_count: number;
  total_revenue: string;
  expenses_total: string;
  net_total: string;
};

export type WeeklySummary = {
  week_start: string;
  week_end: string;
  technician: number | null;
  reports_count: number;
  total_revenue: string;
  expenses_total: string;
  net_total: string;
  by_day: WeeklyDaySummary[];
  by_payment_type: PaymentTypeSummary[];
  by_technician?: WeeklyTechnicianSummary[];
  reviews: ReviewSummary;
};

async function request<T>(path: string, options: RequestInit = {}, allowedErrorStatuses: number[] = []): Promise<T> {
  const token = getAuthToken();
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      Accept: "application/json",
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });

  if (response.status === 401) {
    clearAuth();
    if (window.location.pathname !== "/login") {
      window.location.assign("/login");
    }
  }

  if (!response.ok && !allowedErrorStatuses.includes(response.status)) {
    const text = await response.text();
    throw new Error(text || `Request failed with status ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export function parseApiError(error: unknown): string {
  if (!(error instanceof Error)) {
    return "Request failed.";
  }
  try {
    const parsed = JSON.parse(error.message) as Record<string, unknown>;
    return Object.entries(parsed)
      .map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(", ") : JSON.stringify(value)}`)
      .join(" ");
  } catch {
    return error.message;
  }
}

export async function login(username: string, password: string): Promise<LoginResponse> {
  const response = await request<LoginResponse>("/api/auth/login/", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
  setAuthToken(response.access);
  setRefreshToken(response.refresh);
  setUserRole(response.user.role);
  return response;
}

export function getCurrentUser(): Promise<AuthUser> {
  return request("/api/auth/me/");
}

function toQueryString(params: Record<string, string | number | undefined>): string {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== "") {
      query.set(key, String(value));
    }
  });
  const queryString = query.toString();
  return queryString ? `?${queryString}` : "";
}

export function getDashboardOverview(): Promise<DashboardOverview> {
  return request("/api/dashboard/overview/");
}

export function getTechnicians(): Promise<Technician[]> {
  return request("/api/technicians/");
}

export function createTechnician(payload: TechnicianPayload): Promise<Technician> {
  return request("/api/technicians/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function activateTechnician(id: string | number): Promise<Technician> {
  return request(`/api/technicians/${id}/activate/`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export function startTelegramRegistration(id: string | number): Promise<TelegramRegistration> {
  return request(`/api/technicians/${id}/start-telegram-registration/`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export function getTechnicianDetail(id: string | number): Promise<TechnicianDetail> {
  return request(`/api/dashboard/technicians/${id}/`);
}

export function getSchedule(params: ScheduleParams = {}): Promise<ScheduleResponse> {
  return request(`/api/dashboard/schedule/${toQueryString(params)}`);
}

export function syncTechnicianCalendar(technicianId: string | number, daysAhead = 14): Promise<CalendarSyncResult> {
  return request("/api/calendar/sync-technician/", {
    method: "POST",
    body: JSON.stringify({
      technician_id: technicianId,
      days_ahead: daysAhead,
    }),
  }, [503]);
}

export function sendTechnicianSchedule(technicianId: string | number, targetDate: string): Promise<ScheduleDeliveryResult> {
  return request("/api/calendar/send-technician-schedule/", {
    method: "POST",
    body: JSON.stringify({
      technician_id: technicianId,
      date: targetDate,
    }),
  }, [400]);
}

export function getFinanceSummary(params: FinanceSummaryParams): Promise<FinanceSummary> {
  return request(`/api/dashboard/finance-summary/${toQueryString(params)}`);
}

export function getDailySummary(date: string, technician?: string | number): Promise<DailySummary> {
  return request(`/api/reports/daily-summary/${toQueryString({ date, technician })}`);
}

export function getWeeklySummary(weekStart: string, technician?: string | number): Promise<WeeklySummary> {
  return request(`/api/reports/weekly-summary/${toQueryString({ week_start: weekStart, technician })}`);
}
