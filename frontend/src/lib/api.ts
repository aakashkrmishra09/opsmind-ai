import type { DashboardSummary, ServiceItem, UserProfile } from '../types/ops';

const TOKEN_KEY = 'opsmind_access_token';

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearStoredToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getStoredToken();
  const headers = new Headers(init.headers);
  headers.set('Content-Type', 'application/json');
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const response = await fetch(path, { ...init, headers });
  if (!response.ok) {
    const errBody = await response.json().catch(() => ({}));
    throw new Error(errBody.detail || `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export async function loginUser(email: string, password: string): Promise<string> {
  const data = await apiRequest<{ access_token: string }>('/api/v1/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
  setStoredToken(data.access_token);
  return data.access_token;
}

export async function fetchCurrentUser(): Promise<UserProfile> {
  return apiRequest<UserProfile>('/api/v1/auth/me');
}

export async function fetchDashboardSummary(params: {
  timeRange: string;
  environment: string;
  serviceId: string;
}): Promise<DashboardSummary> {
  const qs = new URLSearchParams({ time_range: params.timeRange });
  if (params.environment) qs.set('environment', params.environment);
  if (params.serviceId) qs.set('service_id', params.serviceId);
  return apiRequest<DashboardSummary>(`/api/v1/dashboard/summary?${qs.toString()}`);
}

export async function fetchServices(environment?: string): Promise<ServiceItem[]> {
  const qs = new URLSearchParams();
  if (environment) qs.set('environment', environment);
  const query = qs.toString() ? `?${qs.toString()}` : '';
  return apiRequest<ServiceItem[]>(`/api/v1/services${query}`);
}