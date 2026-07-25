const pageBase = new URL("./", window.location.href);

export function apiUrl(path: string): string {
  return new URL(path.replace(/^\//, ""), pageBase).toString();
}

export class ApiError extends Error {
  status: number;

  constructor(message: string, status = 0) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit, authRetried = false): Promise<T> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 15000);
  try {
    const controlToken = window.sessionStorage.getItem("aios_control_token") || "";
    const response = await fetch(apiUrl(path), {
      ...init,
      signal: controller.signal,
      headers: {
        Accept: "application/json",
        ...(init?.body ? { "Content-Type": "application/json" } : {}),
        ...(controlToken ? { "X-AIOS-Control-Token": controlToken } : {}),
        ...init?.headers,
      },
    });
    if (response.status === 401 && !authRetried) {
      const token = window.prompt("Enter the AIOS control token to authorize this operation:");
      if (token?.trim()) {
        window.sessionStorage.setItem("aios_control_token", token.trim());
        return request<T>(path, init, true);
      }
    }
    const contentType = response.headers.get("content-type") || "";
    const payload = contentType.includes("application/json")
      ? await response.json()
      : await response.text();
    if (!response.ok) {
      if (response.status === 401) window.sessionStorage.removeItem("aios_control_token");
      const detail = typeof payload === "object" && payload
        ? (payload.error || payload.detail || JSON.stringify(payload))
        : String(payload || response.statusText);
      throw new ApiError(detail, response.status);
    }
    return payload as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError(`Request timed out: ${path}`);
    }
    throw new ApiError(error instanceof Error ? error.message : String(error));
  } finally {
    window.clearTimeout(timeout);
  }
}

export function apiGet<T>(path: string): Promise<T> {
  return request<T>(path);
}

export function apiPost<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, { method: "POST", body: JSON.stringify(body) });
}

export function apiDelete<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, {
    method: "DELETE",
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}
