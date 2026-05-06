const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

interface RequestOptions extends RequestInit {
  params?: Record<string, string>;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { params, ...init } = options;
  const url = new URL(`${BASE_URL}/api/v2${path}`);
  if (params) Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));

  const token = localStorage.getItem('ddr_access_token');
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(init.headers as Record<string, string> || {}),
  };

  const res = await fetch(url.toString(), { ...init, headers });

  if (res.status === 401) {
    localStorage.removeItem('ddr_access_token');
    localStorage.removeItem('ddr_user');
    window.location.href = '/auth';
    throw new Error('Unauthorized');
  }
  if (res.status === 403) throw new Error('Access Denied');
  if (res.status === 422) {
    const body = await res.json();
    throw new Error(body.detail || 'Validation error');
  }
  if (!res.ok) throw new Error(`Server error (${res.status})`);

  return res.json();
}

export const ddrApi = {
  get: <T>(path: string, params?: Record<string, string>) =>
    request<T>(path, { params }),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'POST', body: body ? JSON.stringify(body) : undefined }),
};

export async function checkHealth(): Promise<{ status: string } | null> {
  try {
    return await ddrApi.get<{ status: string }>('/health');
  } catch {
    return null;
  }
}

export async function login(email: string, password: string) {
  return ddrApi.post<{ access_token: string; user: { email: string; name: string } }>('/auth/login', { email, password });
}

export async function register(email: string, password: string, name: string) {
  return ddrApi.post<{ access_token: string; user: { email: string; name: string } }>('/auth/register', { email, password, name });
}
