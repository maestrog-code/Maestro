import { getAccessToken } from "@/lib/auth/tokenStorage";
import { getApiBaseUrl, ApiConfigError } from "@/lib/api/config";

/**
 * The single place that attaches auth to a backend request. Components/lib functions
 * should call this instead of raw fetch() so no call site can accidentally forget the
 * Authorization header.
 *
 * `path` is relative to the API base (e.g. "/api/v1/organizations").
 */
export async function authenticatedFetch(path: string, init: RequestInit = {}): Promise<Response> {
  let baseUrl: string;
  try {
    baseUrl = getApiBaseUrl();
  } catch (err) {
    if (err instanceof Error) throw new ApiConfigError(err.message);
    throw err;
  }

  const token = getAccessToken();
  const headers = new Headers(init.headers);
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  if (!headers.has("Content-Type") && init.body && typeof init.body === "string") {
    headers.set("Content-Type", "application/json");
  }

  return fetch(`${baseUrl}${path}`, {
    ...init,
    headers,
    // Cookie is still sent as a fallback where same-origin (e.g. local dev proxy setups),
    // but the Authorization header above is what actually authenticates cross-domain.
    credentials: "include",
  });
}
