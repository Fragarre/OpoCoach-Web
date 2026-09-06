"use client";

import { useEffect, useMemo, useState } from "react";
import { createClient } from "@/lib/supabase/client";

type Me = { id: string; email: string; employment_access: boolean; subscribed: boolean };
type Organismo = { id: number; nombre: string; tipo: string | null; provincia: string | null; municipio: string | null };
type Proceso = {
  id: number;
  organismo_id: number;
  organismo_nombre: string;
  codigo_externo: string | null;
  identificador_estable: string | null;
  denominacion: string;
  cuerpo_escala: string | null;
  grupo: string | null;
  subgrupo: string | null;
  tipo_proceso: string | null;
  sistema_selectivo: string | null;
  turno: string | null;
  plazas: number | null;
  estado: string | null;
  anio_oep: number | null;
  anio_convocatoria: number | null;
  fecha_convocatoria: string | null;
  fecha_apertura: string | null;
  fecha_cierre: string | null;
  fecha_examen: string | null;
  lugar_examen: string | null;
  ultima_publicacion_at: string | null;
  datos_json: unknown;
};
type Publicacion = { id: number; titulo: string; fecha_publicacion: string | null; url: string; tipo: string | null };
type Cambio = { id: number; fecha: string | null; descripcion: string; url: string | null };

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`/api/empleo/${path.replace(/^\/+/, "")}`, { cache: "no-store" });
  const text = await response.text();
  let body: unknown = null;
  try { body = text ? JSON.parse(text) : null; } catch { body = text; }
  if (!response.ok) {
    const detail = body && typeof body === "object" && "detail" in body ? String((body as { detail: unknown }).detail) : `HTTP ${response.status}`;
    throw new Error(detail);
  }
  return body as T;
}

function fecha(valor: string | null) {
  if (!valor) return "—";
  const d = new Date(valor);
  return Number.isNaN(d.getTime()) ? valor : d.toLocaleDateString("es-ES");
}

export default function EmpleoPage() {
  const supabase = useMemo(() => createClient(), []);
  const [me, setMe] = useState<Me | null>(null);
  const [organismos, setOrganismos] = useState<Organismo[]>([]);
  const [procesos, setProcesos] = useState<Proceso[]>([]);
  const [seleccion, setSeleccion] = useState<Organismo | null>(null);
  const [detalle, setDetalle] = useState<Proceso | null>(null);
  const [publicaciones, setPublicaciones] = useState<Publicacion[]>([]);
  const [cambios, setCambios] = useState<Cambio[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState("");

  async function cargar(organismoId?: number) {
    setCargando(true); setError("");
    try {
      const [m, o, p] = await Promise.all([
        getJson<Me>("me"),
        getJson<Organismo[]>("organismos"),
        getJson<Proceso[]>(organismoId ? `procesos?organismo_id=${organismoId}` : "procesos"),
      ]);
      setMe(m); setOrganismos(o); setProcesos(p);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally { setCargando(false); }
  }

  useEffect(() => { void cargar(); }, []);

  async function abrirProceso(proceso: Proceso) {
    setError(""); setDetalle(proceso);
    try {
      const [p, c] = await Promise.all([
        getJson<Publicacion[]>(`procesos/${proceso.id}/publicaciones`),
        getJson<Cambio[]>(`procesos/${proceso.id}/cambios`),
      ]);
      setPublicaciones(p); setCambios(c);
    } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
  }

  async function cambiarOrganismo(o: Organismo | null) {
    setSeleccion(o); setDetalle(null); setPublicaciones([]); setCambios([]);
    try { setProcesos(await getJson<Proceso[]>(o ? `procesos?organismo_id=${o.id}` : "procesos")); }
    catch (e) { setError(e instanceof Error ? e.message : String(e)); }
  }

  async function cerrarSesion() { await supabase.auth.signOut(); window.location.href = "/"; }

  if (cargando) return <main style={styles.main}><p>Cargando Empleo…</p></main>;

  if (!me) return <main style={styles.main}><h1>Empleo público</h1><p>{error || "No se ha podido identificar la sesión."}</p><a href="/">Volver</a></main>;

  if (!me.employment_access) return <main style={styles.main}><h1>Empleo público</h1><p>Tu cuenta no tiene acceso al módulo de Empleo.</p><a href="/">Volver a NetReto</a></main>;

  return (
    <main style={styles.main}>
      <header style={styles.header}>
        <div><div style={styles.kicker}>NETRETO</div><h1 style={styles.title}>Empleo público</h1><p style={styles.subtitle}>Convocatorias, procesos y publicaciones oficiales.</p></div>
        <div style={styles.headerActions}><a href="/" style={styles.link}>NetReto</a><button onClick={cerrarSesion} style={styles.secondary}>Cerrar sesión</button></div>
      </header>

      {error && <div style={styles.error}>{error}</div>}

      <section style={styles.grid}>
        <aside style={styles.panel}>
          <h2 style={styles.h2}>Organismos</h2>
          <button style={!seleccion ? styles.activeItem : styles.item} onClick={() => void cambiarOrganismo(null)}>Todos</button>
          {organismos.map(o => <button key={o.id} style={seleccion?.id === o.id ? styles.activeItem : styles.item} onClick={() => void cambiarOrganismo(o)}>{o.nombre}</button>)}
        </aside>

        <section style={styles.panel}>
          <div style={styles.sectionHead}><div><h2 style={styles.h2}>{seleccion ? seleccion.nombre : "Procesos"}</h2><p style={styles.muted}>{procesos.length} procesos</p></div></div>
          {procesos.length === 0 ? <p>No hay procesos disponibles.</p> : <div style={styles.cards}>{procesos.map(p => (
            <article key={p.id} style={styles.card}>
              <button style={styles.cardButton} onClick={() => void abrirProceso(p)}>
                <div style={styles.cardTop}><span style={styles.badge}>{p.estado || "SIN ESTADO"}</span><span>{p.plazas ?? "—"} plazas</span></div>
                <h3 style={styles.cardTitle}>{p.denominacion}</h3>
                <p style={styles.muted}>{p.organismo_nombre} · {p.tipo_proceso || "—"} · {p.turno || "—"}</p>
                <div style={styles.meta}>Convocatoria: {fecha(p.fecha_convocatoria)} · Examen: {fecha(p.fecha_examen)}</div>
              </button>
            </article>
          ))}</div>}
        </section>
      </section>

      {detalle && <section style={styles.panelDetail}><div style={styles.detailHead}><div><div style={styles.kicker}>{detalle.organismo_nombre}</div><h2 style={styles.detailTitle}>{detalle.denominacion}</h2></div><button style={styles.secondary} onClick={() => setDetalle(null)}>Cerrar</button></div>
        <div style={styles.detailGrid}>
          <div><strong>Estado</strong><div>{detalle.estado || "—"}</div></div><div><strong>Turno</strong><div>{detalle.turno || "—"}</div></div><div><strong>Plazas</strong><div>{detalle.plazas ?? "—"}</div></div><div><strong>Grupo</strong><div>{detalle.grupo || detalle.subgrupo || "—"}</div></div><div><strong>Apertura</strong><div>{fecha(detalle.fecha_apertura)}</div></div><div><strong>Cierre</strong><div>{fecha(detalle.fecha_cierre)}</div></div><div><strong>Examen</strong><div>{fecha(detalle.fecha_examen)}</div></div><div><strong>Lugar</strong><div>{detalle.lugar_examen || "—"}</div></div>
        </div>
        <div style={styles.columns}>
          <div><h3>Publicaciones oficiales</h3>{publicaciones.length ? publicaciones.map(x => <div key={x.id} style={styles.row}><div>{x.titulo}</div><div style={styles.muted}>{fecha(x.fecha_publicacion)}</div><a href={x.url} target="_blank" rel="noreferrer">Abrir publicación</a></div>) : <p style={styles.muted}>Sin publicaciones registradas.</p>}</div>
          <div><h3>Cambios</h3>{cambios.length ? cambios.map(x => <div key={x.id} style={styles.row}><div>{x.descripcion}</div><div style={styles.muted}>{fecha(x.fecha)}</div>{x.url && <a href={x.url} target="_blank" rel="noreferrer">Abrir</a>}</div>) : <p style={styles.muted}>Sin cambios registrados.</p>}</div>
        </div>
      </section>}
    </main>
  );
}

const styles: Record<string, React.CSSProperties> = {
  main: { maxWidth: 1280, margin: "0 auto", padding: "32px 20px 56px", fontFamily: "system-ui, sans-serif", color: "#172033" },
  header: { display: "flex", justifyContent: "space-between", gap: 24, alignItems: "flex-start", marginBottom: 28 },
  headerActions: { display: "flex", gap: 10, alignItems: "center" },
  kicker: { fontSize: 12, letterSpacing: 1.4, fontWeight: 700, opacity: 0.62, marginBottom: 6 },
  title: { fontSize: 34, margin: 0 }, subtitle: { marginTop: 8, opacity: 0.72 }, h2: { margin: 0, fontSize: 20 }, detailTitle: { margin: 0, fontSize: 28 },
  panel: { border: "1px solid #d9dee8", borderRadius: 14, padding: 18, background: "#fff" }, panelDetail: { marginTop: 20, border: "1px solid #d9dee8", borderRadius: 14, padding: 22, background: "#fff" },
  grid: { display: "grid", gridTemplateColumns: "260px 1fr", gap: 18 }, cards: { display: "grid", gap: 12, marginTop: 16 }, card: { border: "1px solid #e1e5ec", borderRadius: 12, overflow: "hidden" }, cardButton: { width: "100%", border: 0, background: "transparent", textAlign: "left", padding: 16, cursor: "pointer" }, cardTop: { display: "flex", justifyContent: "space-between", fontSize: 13, opacity: 0.8 }, badge: { border: "1px solid #cfd6e2", borderRadius: 999, padding: "3px 8px", fontSize: 11 }, cardTitle: { margin: "10px 0 7px", fontSize: 18 }, meta: { marginTop: 9, fontSize: 13, opacity: 0.68 }, muted: { opacity: 0.68, fontSize: 13 }, item: { display: "block", width: "100%", textAlign: "left", border: 0, background: "transparent", padding: "9px 8px", borderRadius: 8, cursor: "pointer" }, activeItem: { display: "block", width: "100%", textAlign: "left", border: 0, background: "#edf2f8", padding: "9px 8px", borderRadius: 8, cursor: "pointer", fontWeight: 650 }, sectionHead: { display: "flex", justifyContent: "space-between" }, detailHead: { display: "flex", justifyContent: "space-between", gap: 18, marginBottom: 22 }, detailGrid: { display: "grid", gridTemplateColumns: "repeat(4, minmax(0,1fr))", gap: 16, paddingBottom: 22, borderBottom: "1px solid #e5e8ee" }, detailGridChild: {}, columns: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 28, marginTop: 22 }, row: { borderTop: "1px solid #edf0f4", padding: "12px 0", display: "grid", gap: 5 }, link: { textDecoration: "none" }, secondary: { border: "1px solid #cfd6e2", background: "#fff", borderRadius: 8, padding: "8px 12px", cursor: "pointer" }, error: { marginBottom: 18, padding: 12, borderRadius: 8, border: "1px solid #e2b8b8", background: "#fff6f6" },
};
