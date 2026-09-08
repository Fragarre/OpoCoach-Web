"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { createClient } from "@/lib/supabase/client";

type Me = { id: string; email: string; employment_access: boolean; subscribed: boolean };
type Organismo = { id: number; nombre: string; tipo: string | null; provincia: string | null; municipio: string | null };
type Proceso = {
  id: number; organismo_id: number; organismo_nombre: string; codigo_externo: string | null;
  identificador_estable: string | null; denominacion: string; cuerpo_escala: string | null;
  grupo: string | null; subgrupo: string | null; tipo_proceso: string | null; sistema_selectivo: string | null;
  turno: string | null; plazas: number | null; estado: string | null; es_oportunidad: boolean;
  anio_oep: number | null; anio_convocatoria: number | null; fecha_convocatoria: string | null;
  fecha_apertura: string | null; fecha_cierre: string | null; fecha_examen: string | null;
  lugar_examen: string | null; ultima_publicacion_at: string | null; datos_json: unknown;
};
type Suscripcion = { id: number; proceso_id: number };

async function getJson<T>(path: string, accessToken: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/empleo/${path.replace(/^\/+/, "")}`, {
    cache: "no-store", ...init,
    headers: { Authorization: `Bearer ${accessToken}`, ...(init?.headers || {}) },
  });
  const text = await response.text();
  let body: unknown = null;
  try { body = text ? JSON.parse(text) : null; } catch { body = text; }
  if (!response.ok) {
    const detail = body && typeof body === "object" && "detail" in body ? String((body as { detail: unknown }).detail) : `HTTP ${response.status}`;
    throw new Error(detail);
  }
  return body as T;
}

async function getAccessToken(supabase: ReturnType<typeof createClient>): Promise<string> {
  const { data, error } = await supabase.auth.getSession();
  if (error) throw new Error(error.message);
  const token = data.session?.access_token;
  if (!token) throw new Error("Se requiere autenticación.");
  return token;
}

function fecha(valor: string | null) {
  if (!valor) return "—";
  const d = new Date(valor);
  return Number.isNaN(d.getTime()) ? valor : d.toLocaleDateString("es-ES");
}

function identificacion(p: Proceso) {
  const texto = p.denominacion || "";
  const m = texto.match(/\b(?:Convocatoria|Convocat[oò]ria)\s+([A-Z]?\s*\d{1,3}\/\d{2,4}[A-Z]?)\b/i);
  if (m) return m[1].replace(/\s+/g, "").toUpperCase();
  const mAut = texto.match(/\b(AUT\s*\d{1,3}\/\d{2,4})\b/i);
  if (mAut) return mAut[1].replace(/\s+/g, "").toUpperCase();
  return null;
}

function resumen(p: Proceso) {
  let texto = p.denominacion || "";
  texto = texto.replace(/^\s*(?:Convocatoria|Convocat[oò]ria)\s+[A-Z]?\s*\d{1,3}\/\d{2,4}[A-Z]?\.?\s*/i, "");
  texto = texto.replace(/\.?\s*(?:TURNO|TORN)\s+(?:LIBRE|LLIURE)\.?\s*$/i, "");
  return texto.trim() || p.denominacion;
}

function CargandoOverlay() {
  return <div role="status" aria-live="polite" aria-busy="true" style={styles.overlay}><div style={styles.overlayBox}><div style={styles.spinner} aria-hidden="true" /><div>Cargando convocatorias…</div></div></div>;
}

export default function EmpleoPage() {
  const supabase = useMemo(() => createClient(), []);
  const lockRef = useRef(false);
  const [me, setMe] = useState<Me | null>(null);
  const [organismos, setOrganismos] = useState<Organismo[]>([]);
  const [procesos, setProcesos] = useState<Proceso[]>([]);
  const [suscripciones, setSuscripciones] = useState<Suscripcion[]>([]);
  const [seleccion, setSeleccion] = useState<Organismo | null>(null);
  const [municipio, setMunicipio] = useState("");
  const [cargando, setCargando] = useState(true);
  const [procesando, setProcesando] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState<number | null>(null);

  const gva = organismos.find(o => o.id === 1) || null;
  const diputacion = organismos.find(o => o.id === 2) || null;
  const ayuntamientos = organismos.filter(o => o.tipo === "AYUNTAMIENTO" && (o.provincia || "").toLowerCase() === "valencia");
  const municipios = [...new Set(ayuntamientos.map(o => o.municipio || o.nombre.replace(/^Ayuntamiento de\s+/i, "").trim()))].sort((a, b) => a.localeCompare(b, "es"));

  async function cargar(organismoId?: number) {
    setCargando(true); setError("");
    try {
      const token = await getAccessToken(supabase);
      const [m, o, p, s] = await Promise.all([
        getJson<Me>("me", token), getJson<Organismo[]>("organismos", token),
        getJson<Proceso[]>(organismoId ? `procesos?organismo_id=${organismoId}` : "procesos", token),
        getJson<Suscripcion[]>("suscripciones", token),
      ]);
      const visibles = o.filter(x => x.id === 1 || x.id === 2 || (x.tipo === "AYUNTAMIENTO" && (x.provincia || "").toLowerCase() === "valencia"));
      setMe(m); setOrganismos(visibles); setProcesos(p.filter(x => x.es_oportunidad && visibles.some(o => o.id === x.organismo_id))); setSuscripciones(s);
    } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setCargando(false); }
  }

  useEffect(() => { void cargar(); }, [supabase]);

  async function seleccionarOrganismo(o: Organismo | null) {
    if (lockRef.current) return;
    lockRef.current = true; setProcesando(true); setSeleccion(o); setError("");
    try {
      const token = await getAccessToken(supabase);
      const p = await getJson<Proceso[]>(o ? `procesos?organismo_id=${o.id}` : "procesos", token);
      setProcesos(p.filter(x => x.es_oportunidad));
    } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setProcesando(false); lockRef.current = false; }
  }

  async function seleccionarMunicipio(nombre: string) {
    setMunicipio(nombre);
    const o = ayuntamientos.find(x => (x.municipio || x.nombre.replace(/^Ayuntamiento de\s+/i, "").trim()) === nombre) || null;
    await seleccionarOrganismo(o);
  }

  async function toggleSeguimiento(procesoId: number, seguir: boolean) {
    setBusy(procesoId); setError("");
    try {
      const token = await getAccessToken(supabase);
      await getJson(`suscripciones/${procesoId}`, token, { method: seguir ? "POST" : "DELETE" });
      setSuscripciones(await getJson<Suscripcion[]>("suscripciones", token));
    } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setBusy(null); }
  }

  async function cerrarSesion() { await supabase.auth.signOut(); window.location.href = "/"; }

  if (cargando) return <main style={styles.main}><p>Cargando Empleo…</p></main>;
  if (!me) return <main style={styles.main}><h1>Empleo público</h1><p>{error || "No se ha podido identificar la sesión."}</p><a href="/">Volver</a></main>;
  if (!me.employment_access) return <main style={styles.main}><h1>Empleo público</h1><p>Tu cuenta no tiene acceso al módulo de Empleo.</p><a href="/">Volver a Tu Coach</a></main>;

  return <main style={styles.main}>
    {procesando && <CargandoOverlay />}
    <header style={styles.header}>
      <div><div style={styles.kicker}>TU COACH</div><h1 style={styles.title}>Empleo público</h1><p style={styles.subtitle}>Convocatorias activas y oportunidades de acceso al empleo público.</p></div>
      <div style={styles.headerActions}><a href="/" style={styles.link}>Tu Coach</a><button onClick={cerrarSesion} style={styles.secondary}>Cerrar sesión</button></div>
    </header>
    {error && <div style={styles.error}>{error}</div>}

    <section style={styles.heroGrid}>
      <button disabled={procesando} onClick={() => void seleccionarOrganismo(gva)} style={seleccion?.id === 1 ? styles.heroActive : styles.heroCard}>
        <span style={styles.heroIndex}>01</span><strong>Generalitat Valenciana</strong><span style={styles.heroDescription}>Convocatorias de la Administración de la Generalitat Valenciana.</span>
      </button>
      <button disabled={procesando} onClick={() => void seleccionarOrganismo(diputacion)} style={seleccion?.id === 2 ? styles.heroActive : styles.heroCard}>
        <span style={styles.heroIndex}>02</span><strong>Diputación de Valencia</strong><span style={styles.heroDescription}>Procesos selectivos y convocatorias de la Diputación.</span>
      </button>
      <div style={styles.heroCardStatic}>
        <span style={styles.heroIndex}>03</span><strong>Ayuntamientos de la provincia de Valencia</strong>
        <span style={styles.heroDescription}>Selecciona un municipio para consultar sus oportunidades.</span>
        <select value={municipio} disabled={procesando || ayuntamientos.length === 0} onChange={e => void seleccionarMunicipio(e.target.value)} style={styles.select}>
          <option value="">Seleccionar municipio…</option>
          {municipios.map(m => <option key={m} value={m}>{m}</option>)}
        </select>
        {ayuntamientos.length === 0 && <span style={styles.muted}>Próximamente incorporaremos más ayuntamientos.</span>}
      </div>
    </section>

    <section style={styles.panel}>
      <div style={styles.sectionHead}><div><h2 style={styles.h2}>{seleccion ? seleccion.nombre : "Convocatorias activas"}</h2><p style={styles.muted}>{procesos.length} oportunidades</p></div></div>
      {procesos.length === 0 ? <p>No hay convocatorias activas.</p> : <div style={styles.cards}>
        {procesos.map(p => {
          const idConv = identificacion(p); const seguida = suscripciones.some(s => s.proceso_id === p.id);
          return <article key={p.id} style={styles.card}><div style={styles.cardLayout}>
            <button style={styles.cardButton} onClick={() => { window.location.href = `/empleo/proceso/${p.id}`; }} aria-label={`Ver detalle de ${idConv ? `Convocatoria ${idConv}` : p.denominacion}`}>
              <div style={styles.cardTop}><span style={styles.badge}>{p.estado || "SIN ESTADO"}</span>{p.plazas != null && <span>{p.plazas} plazas</span>}</div>
              <div style={styles.cardOrg}>{p.organismo_nombre}</div><h3 style={styles.cardTitle}>{idConv ? `Convocatoria ${idConv}` : p.tipo_proceso || "Proceso selectivo"}</h3>
              <p style={styles.cardSummary}>{resumen(p)}</p><p style={styles.muted}>{p.tipo_proceso || "Proceso selectivo"}{p.turno ? ` · ${p.turno}` : ""}{p.grupo ? ` · ${p.grupo}` : ""}</p>
              <div style={styles.meta}>{p.fecha_apertura ? `Inscripción: ${fecha(p.fecha_apertura)}` : "Inscripción no indicada"}{p.fecha_cierre ? ` · Cierre: ${fecha(p.fecha_cierre)}` : ""}</div>
            </button>
            <button style={seguida ? styles.follow : styles.primary} disabled={busy === p.id || procesando} onClick={() => void toggleSeguimiento(p.id, !seguida)}>{busy === p.id ? "Guardando…" : seguida ? "Siguiendo" : "Seguir"}</button>
          </div></article>;
        })}
      </div>}
    </section>
  </main>;
}

const styles: Record<string, React.CSSProperties> = {
  main: { maxWidth: 1280, margin: "0 auto", padding: "32px 20px 56px", fontFamily: "system-ui, sans-serif", color: "#172033" },
  overlay: { position: "fixed", inset: 0, zIndex: 1000, background: "rgba(255,255,255,0.72)", display: "flex", alignItems: "center", justifyContent: "center", cursor: "wait" },
  overlayBox: { display: "flex", alignItems: "center", gap: 12, padding: "14px 18px", border: "1px solid #d9dee8", borderRadius: 10, background: "#fff", boxShadow: "0 8px 28px rgba(23,32,51,0.12)", fontWeight: 600 },
  spinner: { width: 22, height: 22, border: "3px solid #d9dee8", borderTop: "3px solid #172033", borderRadius: "50%", animation: "empleo-spin 0.8s linear infinite" },
  header: { display: "flex", justifyContent: "space-between", gap: 24, alignItems: "flex-start", marginBottom: 28 },
  headerActions: { display: "flex", gap: 10, alignItems: "center" },
  kicker: { fontSize: 12, letterSpacing: 1.4, fontWeight: 700, opacity: 0.62, marginBottom: 6 },
  title: { fontSize: 34, margin: 0 }, subtitle: { marginTop: 8, opacity: 0.72 }, h2: { margin: 0, fontSize: 20 },
  heroGrid: { display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 14, marginBottom: 18 },
  heroCard: { minHeight: 190, border: "1px solid #d9dee8", borderRadius: 14, background: "#fff", padding: 20, textAlign: "left", cursor: "pointer", display: "flex", flexDirection: "column", gap: 10 },
  heroActive: { minHeight: 190, border: "1px solid #172033", borderRadius: 14, background: "#edf2f8", padding: 20, textAlign: "left", cursor: "pointer", display: "flex", flexDirection: "column", gap: 10 },
  heroCardStatic: { minHeight: 190, border: "1px solid #d9dee8", borderRadius: 14, background: "#fff", padding: 20, textAlign: "left", display: "flex", flexDirection: "column", gap: 10 },
  heroIndex: { fontSize: 12, fontWeight: 700, letterSpacing: 1.2, opacity: 0.55 }, heroDescription: { fontSize: 14, lineHeight: 1.45, opacity: 0.7 },
  select: { width: "100%", marginTop: "auto", border: "1px solid #cfd6e2", borderRadius: 8, background: "#fff", padding: "9px 10px", font: "inherit", color: "inherit" },
  panel: { border: "1px solid #d9dee8", borderRadius: 14, padding: 18, background: "#fff" },
  cards: { display: "grid", gap: 12, marginTop: 16 }, card: { border: "1px solid #e1e5ec", borderRadius: 12, overflow: "hidden" },
  cardLayout: { display: "flex", justifyContent: "space-between", gap: 18, alignItems: "center", padding: 0 }, cardButton: { flex: 1, minWidth: 0, border: 0, background: "transparent", textAlign: "left", padding: 16, cursor: "pointer" },
  cardTop: { display: "flex", justifyContent: "space-between", gap: 12, fontSize: 13, opacity: 0.8 }, cardOrg: { marginTop: 10, fontSize: 13, fontWeight: 650, opacity: 0.72 },
  badge: { border: "1px solid #cfd6e2", borderRadius: 999, padding: "3px 8px", fontSize: 11 }, cardTitle: { margin: "8px 0 5px", fontSize: 19 }, cardSummary: { margin: 0, fontSize: 15, lineHeight: 1.4 }, meta: { marginTop: 9, fontSize: 13, opacity: 0.72 }, muted: { opacity: 0.68, fontSize: 13 },
  sectionHead: { display: "flex", justifyContent: "space-between" }, link: { textDecoration: "none" },
  primary: { border: "1px solid #172033", background: "#172033", color: "#fff", borderRadius: 8, padding: "8px 12px", cursor: "pointer", whiteSpace: "nowrap", marginRight: 16 },
  follow: { border: "1px solid #9aa6b8", background: "#edf2f8", borderRadius: 8, padding: "8px 12px", cursor: "pointer", whiteSpace: "nowrap", marginRight: 16 },
  secondary: { border: "1px solid #cfd6e2", background: "#fff", borderRadius: 8, padding: "8px 12px", cursor: "pointer" }, error: { marginBottom: 18, padding: 12, borderRadius: 8, border: "1px solid #e2b8b8", background: "#fff6f6" },
};

const empleoSpinStyle = `@keyframes empleo-spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`;
if (typeof document !== "undefined" && !document.getElementById("empleo-spin-style")) { const style = document.createElement("style"); style.id = "empleo-spin-style"; style.textContent = empleoSpinStyle; document.head.appendChild(style); }
