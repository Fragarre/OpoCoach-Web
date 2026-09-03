import { NextRequest, NextResponse } from "next/server";

const USERNAME = "netreto";
const PASSWORD = "NetReto2026";

export function proxy(request: NextRequest) {
  const authHeader = request.headers.get("authorization");

  if (authHeader?.startsWith("Basic ")) {
    const encoded = authHeader.substring(6);

    try {
      const decoded = atob(encoded);
      const separator = decoded.indexOf(":");

      if (separator !== -1) {
        const username = decoded.substring(0, separator);
        const password = decoded.substring(separator + 1);

        if (username === USERNAME && password === PASSWORD) {
          return NextResponse.next();
        }
      }
    } catch {
      // Credenciales inválidas
    }
  }

  return new NextResponse("Autenticación requerida", {
    status: 401,
    headers: {
      "WWW-Authenticate": 'Basic realm="NetReto"',
    },
  });
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico).*)",
  ],
};