/**
 * Minimal client-side access-token store.
 *
 * The backend accepts the JWT either as an `Authorization: Bearer` header or as the
 * `maestro_session` cookie (header takes priority — see backend/maestro/app/dependencies/auth.py).
 * The httpOnly cookie set by the login server action still exists as a fallback / for the
 * edge middleware's lightweight "is there a session at all" check, but the browser can't read
 * an httpOnly cookie's value to attach it as a header, and — critically — that cookie belongs
 * to the frontend's own domain, so it's never sent on cross-origin requests to the backend.
 *
 * The access token therefore also gets mirrored here so client-side fetches can attach it
 * explicitly as a Bearer header, which works regardless of domain.
 */

const STORAGE_KEY = "maestro_access_token";

let inMemoryToken: string | null = null;

export function setAccessToken(token: string): void {
  inMemoryToken = token;
  if (typeof window !== "undefined") {
    try {
      window.localStorage.setItem(STORAGE_KEY, token);
    } catch {
      // localStorage can throw in private-browsing/quota-exceeded situations;
      // the in-memory copy still works for the current page session.
    }
  }
}

export function getAccessToken(): string | null {
  if (inMemoryToken) return inMemoryToken;
  if (typeof window !== "undefined") {
    try {
      inMemoryToken = window.localStorage.getItem(STORAGE_KEY);
    } catch {
      inMemoryToken = null;
    }
  }
  return inMemoryToken;
}

export function clearAccessToken(): void {
  inMemoryToken = null;
  if (typeof window !== "undefined") {
    try {
      window.localStorage.removeItem(STORAGE_KEY);
    } catch {
      // no-op
    }
  }
}
