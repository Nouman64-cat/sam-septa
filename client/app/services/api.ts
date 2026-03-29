/**
 * Base API client.
 * All service modules import `post` and `getDownloadUrl` from here so the
 * base URL is defined in exactly one place.
 */

const BASE_URL =
  process.env.NEXT_PUBLIC_SERVER_URL?.replace(/\/$/, "") ??
  "http://127.0.0.1:8001";

// ── Custom error ───────────────────────────────────────────────────────────────

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// ── Core helpers ───────────────────────────────────────────────────────────────

/**
 * POST JSON to a backend path and return the parsed response.
 * Throws `ApiError` for non-2xx HTTP responses.
 */
export async function post<TBody, TResponse>(
  path: string,
  body: TBody,
): Promise<TResponse> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const json = await res.json();
      detail = json?.detail ?? json?.error ?? detail;
    } catch {
      // ignore parse error – keep default detail
    }
    throw new ApiError(res.status, detail);
  }

  return res.json() as Promise<TResponse>;
}

/**
 * GET a backend path and return the parsed JSON response.
 */
export async function get<TResponse>(path: string): Promise<TResponse> {
  const res = await fetch(`${BASE_URL}${path}`, { method: "GET" });

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const json = await res.json();
      detail = json?.detail ?? json?.error ?? detail;
    } catch { /* ignore */ }
    throw new ApiError(res.status, detail);
  }

  return res.json() as Promise<TResponse>;
}

/**
 * DELETE a backend path.
 */
export async function del(path: string): Promise<void> {
  const res = await fetch(`${BASE_URL}${path}`, { method: "DELETE" });

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const json = await res.json();
      detail = json?.detail ?? json?.error ?? detail;
    } catch { /* ignore */ }
    throw new ApiError(res.status, detail);
  }
}

/**
 * Build the full URL that streams a generated file back to the browser.
 * @param filePath  The relative path returned in `ScrapeResponse.filename`.
 */
export function getDownloadUrl(filePath: string): string {
  return `${BASE_URL}/download/${filePath}`;
}
