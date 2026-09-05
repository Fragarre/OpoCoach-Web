import { NextRequest } from "next/server";

const METHODS_WITHOUT_BODY = new Set(["GET", "HEAD"]);

async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  const backendUrl = process.env.EMPLOYMENT_BACKEND_URL;
  if (!backendUrl) {
    return Response.json(
      { detail: "EMPLOYMENT_BACKEND_URL no está configurado." },
      { status: 500 }
    );
  }

  const { path } = await context.params;
  const destino = new URL(path.join("/"), `${backendUrl.replace(/\/$/, "")}/`);

  request.nextUrl.searchParams.forEach((value, key) => {
    destino.searchParams.append(key, value);
  });

  const headers = new Headers();
  const authorization = request.headers.get("authorization");
  const contentType = request.headers.get("content-type");

  if (authorization) {
    headers.set("authorization", authorization);
  }
  if (contentType) {
    headers.set("content-type", contentType);
  }

  const body = METHODS_WITHOUT_BODY.has(request.method)
    ? undefined
    : await request.text();

  try {
    const response = await fetch(destino, {
      method: request.method,
      headers,
      body,
      cache: "no-store",
    });

    return new Response(response.body, {
      status: response.status,
      headers: {
        "content-type":
          response.headers.get("content-type") ?? "application/json",
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
