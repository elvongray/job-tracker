import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  // 1. Get the authentication token from the user's cookies.
  // We'll use a cookie for this since it's accessible on the server.
  const authToken = request.cookies.get("accessToken")?.value;

  // 2. Define which paths are considered "authentication" pages.
  // We don't want to redirect the user if they are already on the login/signup page.
  const isAuthPage =
    request.nextUrl.pathname.startsWith("/signin") ||
    request.nextUrl.pathname.startsWith("/signup");

  // 3. Handle redirection logic.
  if (isAuthPage) {
    // If the user is authenticated and tries to access login/signup,
    // redirect them to the main study page.
    if (authToken) {
      return NextResponse.redirect(new URL("/dashboard", request.url));
    }
  } else {
    // If the user is not authenticated and is trying to access any protected page,
    // redirect them to the login page.
    if (!authToken) {
      return NextResponse.redirect(new URL("/signin", request.url));
    }
  }

  // 4. If none of the above conditions are met, allow the request to proceed.
  return NextResponse.next();
}

// Configures which paths the middleware will run on.
export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    "/((?!api|_next/static|_next/image|favicon.ico).*)",
  ],
};
