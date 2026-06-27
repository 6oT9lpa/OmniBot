const apiBase = import.meta.env.VITE_API_BASE_URL || "";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly detail: unknown = message,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function apiRequest<T>(
  path: string,
  init: RequestInit = {},
  token?: string | null,
): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${apiBase}${path}`, {
    ...init,
    headers,
  });

  if (!response.ok) {
    const rawDetail = await response.text();
    let detail: unknown = rawDetail;
    let message = rawDetail || response.statusText;
    try {
      const parsed = JSON.parse(rawDetail);
      detail = parsed.detail ?? parsed;
      if (typeof detail === "string") {
        message = detail;
      } else if (detail && typeof detail === "object" && "message" in detail) {
        message = String((detail as { message: unknown }).message);
      }
    } catch {
      message = rawDetail || response.statusText;
    }
    throw new ApiError(message, response.status, detail);
  }

  return response.json() as Promise<T>;
}
