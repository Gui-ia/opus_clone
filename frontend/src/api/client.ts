const API_BASE = import.meta.env.VITE_API_URL || '';

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

export async function request<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, error.detail || 'Erro desconhecido');
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

export function toQueryString(
  params: Record<string, unknown>,
): string {
  const entries = Object.entries(params).filter(
    ([, v]) => v !== undefined && v !== null && v !== '',
  );
  return new URLSearchParams(
    entries.map(([k, v]) => [k, String(v)]),
  ).toString();
}
