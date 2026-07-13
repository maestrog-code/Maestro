import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export async function proxy(request: NextRequest) {
  const token = request.cookies.get("maestro_session")?.value;

  // Protect the root dashboard and any other sensitive routes
  if (request.nextUrl.pathname === "/") {
    if (!token) {
      // No token, redirect to login
      return NextResponse.redirect(new URL("/login", request.url));
    }
  }

  // If user is already authenticated and tries to access /login, redirect to /
  if (request.nextUrl.pathname === "/login") {
    if (token) {
      return NextResponse.redirect(new URL("/", request.url));
    }
  }

  return NextResponse.next();
}

// See "Matching Paths" below to learn more
export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - any static files with extensions (e.g., .svg, .png)
     */
    '/((?!api|_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
  ],
};
