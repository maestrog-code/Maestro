"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { getApiBaseUrl } from "@/lib/api/config";

// Must match backend ACCESS_TOKEN_EXPIRE_MINUTES (backend/maestro/app/core/config.py).
// Previously this constant was computed but never actually used — the cookie was hardcoded
// to 30 days regardless, so sessions outlived their JWTs by a wide margin.
const ACCESS_TOKEN_MAX_AGE_SECONDS = 30 * 60;

export async function loginAction(prevState: any, formData: FormData) {
  const email = formData.get("email") as string;
  const password = formData.get("password") as string;

  if (!email || !password) {
    return { error: "Email and password are required." };
  }

  let apiBaseUrl: string;
  try {
    apiBaseUrl = getApiBaseUrl();
  } catch (err) {
    return { error: err instanceof Error ? err.message : "Configuration error." };
  }

  try {
    const params = new URLSearchParams();
    params.append("username", email);
    params.append("password", password);

    const res = await fetch(`${apiBaseUrl}/api/v1/auth/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: params,
    });

    if (!res.ok) {
      if (res.status === 401 || res.status === 422) {
        return { error: "Invalid credentials." };
      }
      if (res.status >= 500) {
        return { error: "Maestro's services are experiencing an issue. Please try again shortly." };
      }
      return { error: "An unexpected server error occurred." };
    }

    const data = await res.json();
    const accessToken: string = data.token.access_token;

    // Cookie is kept as a fallback (see backend/maestro/app/dependencies/auth.py, which checks
    // the Authorization header first and this cookie second) and so the edge middleware has a
    // cheap "is there a session at all" signal. It is NOT what authenticates cross-domain
    // requests to the backend — the client stores the token separately and sends it as a
    // Bearer header via authenticatedFetch() for that.
    const cookieStore = await cookies();
    cookieStore.set("maestro_session", accessToken, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      maxAge: ACCESS_TOKEN_MAX_AGE_SECONDS,
      path: "/",
    });

    // Returned to the client instead of redirecting from here, so the client can store the
    // token (for Bearer auth) before navigating.
    return { success: true, token: accessToken };
  } catch (error) {
    console.error("Login Server Action Error:", error);
    return { error: "Unable to reach Maestro's services. Check your connection and try again." };
  }
}

export async function logoutAction() {
  const cookieStore = await cookies();
  cookieStore.delete("maestro_session");
  redirect("/login");
}

export async function signupAction(prevState: any, formData: FormData) {
  const email = formData.get("email") as string;
  const password = formData.get("password") as string;
  const company = formData.get("company") as string;

  if (!email || !password || !company) {
    return { error: "All fields are required to provision a workspace." };
  }

  let apiBaseUrl: string;
  try {
    apiBaseUrl = getApiBaseUrl();
  } catch (err) {
    return { error: err instanceof Error ? err.message : "Configuration error." };
  }

  try {
    // 1. Register User
    const res = await fetch(`${apiBaseUrl}/api/v1/auth/register`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        email: email,
        password: password
      }),
    });

    if (!res.ok) {
      const errorData = await res.json().catch(() => null);
      return { error: errorData?.detail || "Registration failed. Email might already exist." };
    }

    const data = await res.json();
    const token = data.token.access_token;

    // 2. Provision Workspace (Organization)
    const orgRes = await fetch(`${apiBaseUrl}/api/v1/organizations/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      },
      body: JSON.stringify({
        name: company
      }),
    });

    if (!orgRes.ok) {
      return { error: "User created, but workspace provisioning failed." };
    }

  } catch (error) {
    console.error("Signup Server Action Error:", error);
    return { error: "Unable to reach Maestro's services. Check your connection and try again." };
  }

  // Redirect to login upon successful workspace creation
  redirect("/login?registered=true");
}
