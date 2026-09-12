import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";
import { NextRequest } from "next/server";

const METHODS_WITHOUT_BODY = new Set(["GET", "HEAD"]);

async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  const backendUrl = process.env.BACKEND_URL;
  const employmentBackendUrl = process.env.EMPLOYMENT_BACKEND_URL;

  if (!backendUrl && !employmentBackendUrl) {
    return Response.json(
      { detail: "No hay ningún backend de Empleo configurado." },
      { status: 500 }
    );
  }

  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;
  if (!supabaseUrl || !supabaseKey) {
    return Response.json(
      {
        detail:
          "Faltan NEXT_PUBLIC_SUPABASE_URL o NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY.",
      },
      { status: 500 }
    );
  }

  const { path } = await context.params;
  const ruta = path.join("/");

  const headers = new Headers();
  const authorization = request.headers.get("authorization");
  const contentType = request.headers.get("content-type");

  if (authorization) {
    headers.set("authorization", authorization);
  } else {
    const cookieStore = await cookies();
    const supabase = createServerClient(supabaseUrl, supabaseKey, {
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value, options }) => {
            cookieStore.set(name, value, options);
          });
        },
      },
    });

    const {
      data: { session },
    } = await supabase.auth.getSession();

    if (session?.access_token) {
      headers.set("authorization", `Bearer ${session.access_token}`);
    }
  }

  if (contentType) {
    headers.set("content-type", contentType);
  }

  const body = METHODS_WITHOUT_BODY.has(request.method)
    ? undefined
    : await request.text();

  function construirDestino(base: string, prefijoEmpleo: boolean) {
    const normalizada = base.replace(/\/$/, "");
    const raiz = prefijoEmpleo ? `${normalizada}/empleo/` : `${normalizada}/`;
    const destino = new URL(ruta, raiz);
    request.nextUrl.searchParams.forEach((value, key) => {
      destino.searchParams.append(key, value);
    });
    return destino;
  }

  async function solicitar(destino: URL) {
    return fetch(destino, {
      method: request.method,
      headers,
      body,
      cache: "no-store",
    });
  }

  try {
    // Ruta preferente: mismo backend Render que Tu Coach, bajo /empleo/*.
    if (backendUrl) {
      try {
        const response = await solicitar(construirDestino(backendUrl, true));

        // Durante la migración conservamos el servicio anterior como red de
        // seguridad únicamente ante fallos del servidor unificado. Los 4xx se
        // devuelven tal cual porque representan respuestas funcionales reales.
        if (response.status < 500 || !employmentBackendUrl) {
          return new Response(response.body, {
            status: response.status,
            headers: {
              "content-type":
                response.headers.get("content-type") ?? "application/json",
              "x-employment-source": "unified",
            },
          });
        }
      } catch (error) {
        if (!employmentBackendUrl) throw error;
      }
    }

    // Fallback temporal al servicio standalone. Se retirará cuando el backend
    // unificado y el cron hayan quedado validados extremo a extremo.
    if (!employmentBackendUrl) {
      throw new Error("Backend de Empleo no disponible.");
    }

    const response = await solicitar(
      construirDestino(employmentBackendUrl, false)
    );

    return new Response(response.body, {
      status: response.status,
      headers: {
        "content-type":
          response.headers.get("content-type") ?? "application/json",
        "x-employment-source": "legacy-fallback",
      },
    });
  } catch (error) {
    const detail =
      error instanceof Error ? error.message : "Error desconocido.";
    return Response.json(
      { detail: `Backend de empleo no disponible: ${detail}` },
      { status: 503 }
    );
  }
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
