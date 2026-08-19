import { createClient } from "@/lib/supabase/client";

type ApiTiming = {
  path: string;
  method: string;
  authMs: number;
  fetchMs: number;
  parseMs: number;
  totalMs: number;
  status: number;
};

declare global {
  interface Window {
    __OPOCOACH_API_TIMINGS__?: ApiTiming[];
  }
}

function registrarTiming(timing: ApiTiming) {
  if (typeof window !== "undefined") {
    const lista = window.__OPOCOACH_API_TIMINGS__ ?? [];
    lista.push(timing);

    // Conservamos sólo las últimas 200 peticiones para no crecer sin límite.
    if (lista.length > 200) {
      lista.splice(0, lista.length - 200);
    }

    window.__OPOCOACH_API_TIMINGS__ = lista;
  }

  if (process.env.NODE_ENV !== "production") {
    console.info(
      `[OpoCoach API] ${timing.method} ${timing.path} | ` +
        `auth=${timing.authMs.toFixed(1)} ms | ` +
        `fetch=${timing.fetchMs.toFixed(1)} ms | ` +
        `parse=${timing.parseMs.toFixed(1)} ms | ` +
        `total=${timing.totalMs.toFixed(1)} ms | ` +
        `status=${timing.status}`
    );
  }
}

export async function apiFetch<T>(
  path: string,
  init: RequestInit = {}
): Promise<T> {
  const inicioTotal = performance.now();

  const inicioAuth = performance.now();
  const supabase = createClient();
  const { data, error } = await supabase.auth.getSession();
  const finAuth = performance.now();

  if (error) {
    throw new Error(error.message);
  }

  const accessToken = data.session?.access_token;
  if (!accessToken) {
    throw new Error("No hay una sesión autenticada.");
  }

  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${accessToken}`);

  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const inicioFetch = performance.now();
  const response = await fetch(`/api/backend/${path.replace(/^\/+/, "")}`, {
    ...init,
    headers,
    cache: "no-store",
  });
  const finFetch = performance.now();

  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const body = await response.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch {
      // respuesta sin JSON
    }

    registrarTiming({
      path,
      method: init.method ?? "GET",
      authMs: finAuth - inicioAuth,
      fetchMs: finFetch - inicioFetch,
      parseMs: 0,
      totalMs: performance.now() - inicioTotal,
      status: response.status,
    });

    throw new Error(detail);
  }

  if (response.status === 204) {
    registrarTiming({
      path,
      method: init.method ?? "GET",
      authMs: finAuth - inicioAuth,
      fetchMs: finFetch - inicioFetch,
      parseMs: 0,
      totalMs: performance.now() - inicioTotal,
      status: response.status,
    });

    return undefined as T;
  }

  const inicioParse = performance.now();
  const resultado = (await response.json()) as T;
  const finParse = performance.now();

  registrarTiming({
    path,
    method: init.method ?? "GET",
    authMs: finAuth - inicioAuth,
    fetchMs: finFetch - inicioFetch,
    parseMs: finParse - inicioParse,
    totalMs: finParse - inicioTotal,
    status: response.status,
  });

  return resultado;
}
