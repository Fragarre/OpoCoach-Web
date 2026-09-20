import { NextRequest } from "next/server";

const BOP_CASTELLON_HOST = "bop.dipcas.es";

export async function GET(request: NextRequest) {
  const raw = request.nextUrl.searchParams.get("url");
  if (!raw) return Response.json({ detail: "Falta url." }, { status: 400 });

  let source: URL;
  try {
    source = new URL(raw);
  } catch {
    return Response.json({ detail: "URL no válida." }, { status: 400 });
  }

  if (
    source.protocol !== "https:" ||
    source.hostname !== BOP_CASTELLON_HOST ||
    !source.pathname.startsWith("/PortalBOP/api/descargarAnuncio")
  ) {
    return Response.json({ detail: "Fuente no permitida." }, { status: 400 });
  }

  try {
    const upstream = await fetch(source, { cache: "no-store" });
    if (!upstream.ok || !upstream.body) {
      return Response.json(
        { detail: "Documento oficial no disponible." },
        { status: upstream.status || 502 }
      );
    }
    return new Response(upstream.body, {
      status: 200,
      headers: {
        "content-type": upstream.headers.get("content-type") ?? "application/pdf",
        "content-disposition": 'inline; filename="convocatoria.pdf"',
        "cache-control": "no-store",
      },
    });
  } catch {
    return Response.json(
      { detail: "No se pudo abrir el documento oficial." },
      { status: 502 }
    );
  }
}
