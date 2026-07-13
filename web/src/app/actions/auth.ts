"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";

export async function loginAction(prevState: any, formData: FormData) {
  const email = formData.get("email") as string;
  const password = formData.get("password") as string;

  if (!email || !password) {
    return { error: "Email and password are required." };
  }

  try {
    const params = new URLSearchParams();
    params.append("username", email);
    params.append("password", password);

    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/auth/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: params,
    });

    if (!res.ok) {
      // Handle known errors cleanly
      if (res.status === 401 || res.status === 422) {
        return { error: "Invalid credentials." };
      }
      return { error: "An unexpected server error occurred." };
    }

    const data = await res.json();
    const token = data.token.access_token;
    const maxAge = 30 * 60; // 30 minutes in seconds

    // Set HTTP-only cookie
    const cookieStore = await cookies();
    cookieStore.set("maestro_session", data.token.access_token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      maxAge: 30 * 24 * 60 * 60, // 30 days
      path: "/",
    });

  } catch (error) {
    console.error("Login Server Action Error:", error);
    return { error: "Failed to connect to the authentication server." };
  }

  // Redirect on success (Next.js redirect throws an error under the hood, 
  // so it must be called outside the try/catch block)
  redirect("/");
}

export async function logoutAction() {
  const cookieStore = await cookies();
  cookieStore.delete("maestro_session");
  redirect("/login");
}
