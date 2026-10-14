/**
 * Central resolver for the backend API base URL.
 *
 * Previously every call site did `process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"`,
 * which silently pointed production at localhost whenever the env var wasn't configured
 * on Vercel. That produced a confusing "Access Control Denied" screen that looked like
 * an account/permissions problem but was actually a missing deployment config.
 *
 * Development may still fall back to localhost. Production must not.
 */
export function getApiBaseUrl(): string {
  const url = process.env.NEXT_PUBLIC_API_URL;

  if (url) return url;

  if (process.env.NODE_ENV === "production") {
    throw new Error(
      "NEXT_PUBLIC_API_URL is not configured. Set it in the Vercel project's " +
      "Environment Variables to the deployed backend URL."
    );
  }

  return "http://localhost:8000";
}

export class ApiConfigError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ApiConfigError";
  }
}

/** Human-readable message for a given fetch/response failure. Used to avoid the
 * app defaulting every failure to a permissions-sounding "Access Control Denied". */
export function describeFetchFailure(error: unknown, status?: number): string {
  if (error instanceof ApiConfigError) return error.message;

  if (status === 401) return "Session expired. Please log in again.";
  if (status === 403) return "You don't have permission to access this resource.";
  if (status && status >= 500) return "Maestro's services are experiencing an issue. Please try again shortly.";

  if (error instanceof TypeError) {
    // Browser fetch throws a TypeError for network-level failures (DNS, CORS, offline, etc).
    return "Unable to reach Maestro's services. Check your connection and try again.";
  }

  return "An unexpected error occurred.";
}
