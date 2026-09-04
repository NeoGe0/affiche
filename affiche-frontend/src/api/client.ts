export const API_BASE = import.meta.env.VITE_API_URL || '/affiche';

export const UNAUTHORIZED_EVENT = 'affiche:unauthorized';

export async function extractErrorMessage(response: Response): Promise<string> {
  const fallback = `Request failed: ${response.status}`;
  const text = await response.text();
  if (!text) return fallback;
  try {
    const body = JSON.parse(text);
    const detail = body?.detail;
    if (typeof detail === 'string') return detail;

    if (Array.isArray(detail)) {
      const msg = detail.map((d) => d?.msg).filter(Boolean).join('; ');
      if (msg) return msg;
    }
    if (typeof body?.message === 'string') return body.message;
    return text;
  } catch {

    return text;
  }
}

export function errorMessage(error: unknown, fallback: string): string {
  return error instanceof Error && error.message ? error.message : fallback;
}

async function failed(response: Response): Promise<Error> {
  if (response.status === 401) {
    window.dispatchEvent(new CustomEvent(UNAUTHORIZED_EVENT));
  }
  return new Error(await extractErrorMessage(response));
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;

  const response = await fetch(url, {
    ...options,

    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!response.ok) {
    throw await failed(response);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

export async function postForm<T>(endpoint: string, form: FormData): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    method: 'POST',
    body: form,
    credentials: 'include',
  });

  if (!response.ok) {
    throw await failed(response);
  }

  return response.json();
}

export const api = {
  get: <T>(endpoint: string) => request<T>(endpoint),
  post: <T>(endpoint: string, data?: unknown) =>
    request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    }),
  put: <T>(endpoint: string, data: unknown) =>
    request<T>(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
  patch: <T>(endpoint: string, data: unknown) =>
    request<T>(endpoint, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
  delete: <T>(endpoint: string) =>
    request<T>(endpoint, { method: 'DELETE' }),
};
