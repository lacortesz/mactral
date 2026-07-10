const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const PROJECTS_API_BASE_URL =
  import.meta.env.VITE_PROJECTS_API_BASE_URL ?? "http://localhost:8100";

export class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(status: number, body: unknown, message: string) {
    super(message);
    this.status = status;
    this.body = body;
  }
}

function extractMessage(status: number, body: unknown): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (detail && typeof detail === "object" && "message" in (detail as object)) {
      return String((detail as { message: unknown }).message);
    }
    if (Array.isArray(detail) && detail[0]?.msg) {
      return String(detail[0].msg).replace(/^Value error,\s*/, "");
    }
  }
  return `Error inesperado (HTTP ${status})`;
}

type FetchOptions = {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  token?: string | null;
};

async function doFetch<T>(baseUrl: string, path: string, opts: FetchOptions): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (opts.token) headers.Authorization = `Bearer ${opts.token}`;

  const response = await fetch(`${baseUrl}${path}`, {
    method: opts.method ?? "GET",
    headers,
    body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
  });

  const text = await response.text();
  const data = text ? JSON.parse(text) : null;

  if (!response.ok) {
    throw new ApiError(response.status, data, extractMessage(response.status, data));
  }

  return data as T;
}

export function apiFetch<T>(path: string, opts: FetchOptions = {}): Promise<T> {
  return doFetch<T>(API_BASE_URL, path, opts);
}

// E1-H3: el servicio de proyectos (services/projects) es una API separada.
export function projectsApiFetch<T>(path: string, opts: FetchOptions = {}): Promise<T> {
  return doFetch<T>(PROJECTS_API_BASE_URL, path, opts);
}

export function retryAfterSeconds(error: ApiError): number | null {
  if (
    error.body &&
    typeof error.body === "object" &&
    "detail" in error.body &&
    (error.body as { detail: unknown }).detail &&
    typeof (error.body as { detail: { retry_after_seconds?: number } }).detail === "object"
  ) {
    const detail = (error.body as { detail: { retry_after_seconds?: number } }).detail;
    return typeof detail.retry_after_seconds === "number" ? detail.retry_after_seconds : null;
  }
  return null;
}
