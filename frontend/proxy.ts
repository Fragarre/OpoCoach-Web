import { NextRequest, NextResponse } from "next/server";

const USERNAME = "netreto";
const PASSWORD = "NetReto2026";

export function proxy(request: NextRequest) {
  const authorization = request.headers.get("authorization");

  if (authorization) {
    try {
      const encoded = authorization.replace(/^Basic\s+/i, "");
      const decoded = atob(encoded);

      if (decoded === `${USERNAME}:${PASSWORD}`) {
        return NextResponse.next();
      }
    } catch {
      // Credenciales no válidas
    }
  }

  return new NextResponse("Autenticación requerida", {
    status: 401,
    headers: {
      "WWW-Authenticate": 'Basic realm="NetReto-Web-2026"',
    },
  });
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico).*)",
  ],
};