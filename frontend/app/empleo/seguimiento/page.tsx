"use client";

import { useEffect, useMemo, useState } from "react";
import { createClient } from "@/lib/supabase/client";

type Seguimiento = {
  id: number;
  proceso_id: number;
  denominacion: string;
  organismo_nombre: string;
  tipo_proceso: string | null;
  plazas: number | null;
  estado: string | null;
  anio_convocatoria: number | null;
  fecha_apertura: string | null;
  fecha_cierre: string | null;
  fecha_examen: string | null;
};

type Cambio = {
  id: number;
  proceso_id: number;
  identificador_estable: string | null;
  denominacion: string;
  organismo_nombre: string;
  tipo: string | null;
  campo: string | null;
  resumen: string | null;
  detectado_at: string | null;
  significativo: boolean;
};

async function getJson<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/empleo/${path.replace(/^\/+/, "")}`, {
    cache: "no-store",
    ...init,
    headers: {
      Authorization: `Bearer ${token}`,
      ...(init?.headers || {}),
    },
  });
  const text = await response.text();
  let body: unknown = null;
  try { body = text ? JSON.parse(text) : null; } catch { body = text; }
  if (!response.ok) {
    const detail = body && typeof body === "object" && "detail" in body
      ? String((body as { detail: unknown }).detail)
      : `HTTP ${response.status}`;
    throw new Error(detail);
  }
  return body as T;
}

function fecha(valor: string | null) {
  if (!valor) return "—";
  const d = new Date(valor);
  return Number.isNaN(d.getTime()) ? valor : d.toLocaleDateString("es-ES");
}

export default function SeguimientoPage() {
  const supabase = useMemo(() => createClient(), []);
  const [items, setItems] = useState<Seguimiento[]>([]);
  const [cambios, setCambios] = useState<Cambio[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState("");

  async function cargar() {
    setCargando(true);
    setError("");
    try {
      const { data, error: authError } = await supabase.auth.getSession();
      if (authError) throw authError;
      const token = data.session?.access_token;
      if (!token) throw new Error("Se requiere autenticación.");
      const [suscripciones, novedades] = await Promise.all([
        getJson<Seguimiento[]>("suscripciones", token),
        getJson<Cambio[]>("seguimiento/cambios", token),
      ]);
      setItems(suscripciones);
      setCambios(novedades.filter(x => x.significativo));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setCargando(false);
    }
  }

  useEffect(() => { void cargar(); }, [supabase]);

  async function cancelar(procesoId: number) {
    setError("");
    try {
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      if (!token) throw new Error("Se requiere autenticación.");
      await getJson(`suscripciones/${procesoId}`, token, { method: "DELETE" });
      await cargar();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  if (cargando) return <main style={styles.main}><p>Cargando seguimiento…</p></main>;

  return (
    <main style={styles.main}>
      <header style={styles.header}>
        <div>
          <div style={styles.kicker}>NETRETO</div>
          <h1 style={styles.title}>Mi seguimiento</h1>
          <p style={styles.subtitle}>Convocatorias que estás siguiendo y novedades significativas.</p>
        </div>
        <div style={styles.actions}>
          <a href="/empleo" style={styles.link}>Volver a Empleo</a>
        </div>
      </header>

      {error && <div style={styles.error}>{error}</div>}

      <section style={styles.panel}>
        <div style={styles.sectionHead}>
          <h2 style={styles.h2}>Mis convocatorias</h2>
          <span style={styles.muted}>{items.length} seguidas</span>
        </div>
        {items.length === 0 ? (
          <p style={styles.muted}>No estás siguiendo ninguna convocatoria. Desde Empleo puedes entrar en una oportunidad y pulsar «Seguir».</p>
        ) : (
          <div style={styles.list}>
            {items.map(x => (
              <article key={x.id} style={styles.card}>
                <div>
                  <div style={styles.kicker}>{x.organismo_nombre}</div>
                  <h3 style={styles.cardTitle}>{x.denominacion}</h3>
                  <p style={styles.muted}>{x.tipo_proceso || "Proceso selectivo"}{x.plazas != null ? ` · ${x.plazas} plazas` : ""}</p>
                  <p style={styles.meta}>Apertura: {fecha(x.fecha_apertura)}{x.fecha_cierre ? ` · Cierre: ${fecha(x.fecha_cierre)}` : ""}{x.fecha_examen ? ` · Examen: ${fecha(x.fecha_examen)}` : ""}</p>
                </div>
                <button onClick={() => void cancelar(x.proceso_id)} style={styles.secondary}>Dejar de seguir</button>
              </article>
            ))}
          </div>
        )}
      </section>

      <section style={styles.panel}>
        <div style={styles.sectionHead}>
          <h2 style={styles.h2}>Últimas novedades</h2>
          <span style={styles.muted}>{cambios.length} cambios significativos</span>
        </div>
        {cambios.length === 0 ? (
          <p style={styles.muted}>No hay novedades significativas en tus convocatorias.</p>
        ) : (
          <div style={styles.list}>
            {cambios.map(c => (
              <article key={c.id} style={styles.change}>
                <div style={styles.kicker}>{c.organismo_nombre} · {fecha(c.detectado_at)}</div>
                <h3 style={styles.cardTitle}>{c.denominacion}</h3>
                <p style={styles.changeText}>{c.resumen || `${c.tipo || "Cambio"}${c.campo ? ` · ${c.campo}` : ""}`}</p>
              </article>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}

const styles: Record<string, React.CSSProperties> = {
  main: { maxWidth: 1100, margin: "0 auto", padding: "32px 20px 56px", fontFamily: "system-ui, sans-serif", color: "#172033" },
  header: { display: "flex", justifyContent: "space-between", gap: 24, alignItems: "flex-start", marginBottom: 24 },
  actions: { display: "flex", gap: 10, alignItems: "center" },
  kicker: { fontSize: 12, letterSpacing: 1.4, fontWeight: 700, opacity: 0.62, marginBottom: 6 },
  title: { fontSize: 34, margin: 0 },
  subtitle: { marginTop: 8, opacity: 0.72 },
  panel: { border: "1px solid #d9dee8", borderRadius: 14, padding: 18, background: "#fff", marginBottom: 18 },
  sectionHead: { display: "flex", justifyContent: "space-between", gap: 18, alignItems: "baseline", marginBottom: 12 },
  h2: { margin: 0, fontSize: 20 },
  list: { display: "grid", gap: 12 },
  card: { border: "1px solid #e1e5ec", borderRadius: 12, padding: 16, display: "flex", justifyContent: "space-between", gap: 18, alignItems: "center" },
  change: { borderTop: "1px solid #edf0f4", padding: "13px 0" },
  cardTitle: { margin: "4px 0 6px", fontSize: 17 },
  changeText: { margin: 0, lineHeight: 1.45 },
  muted: { opacity: 0.68, fontSize: 13 },
  meta: { margin: "8px 0 0", fontSize: 13, opacity: 0.72 },
  secondary: { border: "1px solid #cfd6e2", background: "#fff", borderRadius: 8, padding: "8px 12px", cursor: "pointer", whiteSpace: "nowrap" },
  link: { textDecoration: "none" },
  error: { marginBottom: 18, padding: 12, borderRadius: 8, border: "1px solid #e2b8b8", background: "#fff6f6" },
};