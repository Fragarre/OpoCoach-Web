"use client";

import { useEffect, useState } from "react";
import type { CSSProperties, FormEvent } from "react";
import { createClient } from "../../../lib/supabase/client";

type AmbitoAdministrativo = "SI" | "NO" | "REVISION";

type Pendiente = {
  id: number;
  organismo_id: number;
  organismo_nombre: string | null;
  codigo_externo: string | null;
  denominacion: string;
  grupo: string | null;
  tipo_proceso: string | null;
  sistema_selectivo: string | null;
  turno: string | null;
  plazas: number | null;
  estado: string | null;
  origen_dato: string;
  revision_estado: string;
  ambito_administrativo?: AmbitoAdministrativo;
  fecha_convocatoria: string | null;
  fecha_apertura: string | null;
  fecha_cierre: string | null;
  fecha_examen: string | null;
  lugar_examen: string | null;
  observaciones_internas: string | null;
};

type Convocatoria = Pendiente;

type Temario = {
  contenido_texto: string;
  origen: string;
  estado: string;
  fuente_url: string | null;
  observaciones: string | null;
} | null;

type ExtraccionTemario = {
  contenido_texto: string;
  fuente_url: string;
  fuente_publicacion_id: number;
  fuente_referencia: string | null;
  fuente_titulo: string | null;
  caracteres_fuente: number;
};

type Formulario = {
  organismo_id: string;
  denominacion: string;
  codigo_externo: string;
  grupo: string;
  tipo_proceso: string;
  sistema_selectivo: string;
  turno: string;
  plazas: string;
  estado: string;
  revision_estado: string;
  fecha_convocatoria: string;
  fecha_apertura: string;
  fecha_cierre: string;
  fecha_examen: string;
  lugar_examen: string;
  observaciones_internas: string;
};

const inicial: Formulario = {
  organismo_id: "1", denominacion: "", codigo_externo: "", grupo: "", tipo_proceso: "Oposición",
  sistema_selectivo: "Oposición", turno: "TURNO_LIBRE", plazas: "", estado: "EN_CURSO",
  revision_estado: "PENDIENTE_REVISION", fecha_convocatoria: "", fecha_apertura: "", fecha_cierre: "",
  fecha_examen: "", lugar_examen: "", observaciones_internas: "",
};

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const supabase = createClient();
  const { data: { session } } = await supabase.auth.getSession();
  const headers = new Headers(init?.headers);
  headers.set("Content-Type", "application/json");
  if (session?.access_token) headers.set("Authorization", `Bearer ${session.access_token}`);
  const response = await fetch(`/api/empleo/admin/gestion/${path}`, { cache: "no-store", ...init, headers });
  const text = await response.text();
  let body: unknown = null;
  try { body = text ? JSON.parse(text) : null; } catch { body = text; }
  if (!response.ok) {
    const detail = body && typeof body === "object" && "detail" in body ? String((body as { detail: unknown }).detail) : `HTTP ${response.status}`;
    throw new Error(detail);
  }
  return body as T;
}

function formularioDe(p: Pendiente): Formulario {
  return {
    organismo_id: String(p.organismo_id), denominacion: p.denominacion || "", codigo_externo: p.codigo_externo || "",
    grupo: p.grupo || "", tipo_proceso: p.tipo_proceso || "", sistema_selectivo: p.sistema_selectivo || "",
    turno: p.turno || "", plazas: p.plazas == null ? "" : String(p.plazas), estado: p.estado || "EN_CURSO",
    revision_estado: p.revision_estado || "PENDIENTE_REVISION", fecha_convocatoria: (p.fecha_convocatoria || "").slice(0, 10),
    fecha_apertura: (p.fecha_apertura || "").slice(0, 10), fecha_cierre: (p.fecha_cierre || "").slice(0, 10),
    fecha_examen: (p.fecha_examen || "").slice(0, 10), lugar_examen: p.lugar_examen || "",
    observaciones_internas: p.observaciones_internas || "",
  };
}

export default function EmpleoAdminPage() {
  const [pendientes, setPendientes] = useState<Pendiente[]>([]);
  const [convocatorias, setConvocatorias] = useState<Convocatoria[]>([]);
  const [seleccion, setSeleccion] = useState<Pendiente | null>(null);
  const [form, setForm] = useState<Formulario>(inicial);
  const [temario, setTemario] = useState<Temario>(null);
  const [textoTemario, setTextoTemario] = useState("");
  const [estadoTemario, setEstadoTemario] = useState("PENDIENTE_REVISION");
  const [origenTemario, setOrigenTemario] = useState("MANUAL");
  const [fuenteTemario, setFuenteTemario] = useState<string | null>(null);
  const [nuevo, setNuevo] = useState(false);
  const [cargando, setCargando] = useState(true);
  const [extrayendo, setExtrayendo] = useState(false);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState("");
  const [mensaje, setMensaje] = useState("");

  async function cargar() {
    setCargando(true); setError("");
    try {
      const [p, c] = await Promise.all([
        api<Pendiente[]>("pendientes?limite=200"),
        api<Convocatoria[]>("convocatorias"),
      ]);
      const ambitos = new Map(c.map(x => [x.id, x.ambito_administrativo || "REVISION"]));
      setPendientes(p.map(x => ({ ...x, ambito_administrativo: ambitos.get(x.id) || "REVISION" })));
      setConvocatorias(c);
    } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setCargando(false); }
  }

  useEffect(() => { void cargar(); }, []);

  async function abrir(p: Pendiente) {
    setSeleccion(p); setNuevo(false); setForm(formularioDe(p)); setMensaje(""); setError("");
    try {
      const t = await api<Temario>(`procesos/${p.id}/temario`);
      setTemario(t); setTextoTemario(t?.contenido_texto || ""); setEstadoTemario(t?.estado || "PENDIENTE_REVISION");
      setOrigenTemario(t?.origen || "MANUAL"); setFuenteTemario(t?.fuente_url || null);
    } catch (e) {
      setTemario(null); setTextoTemario(""); setEstadoTemario("PENDIENTE_REVISION"); setOrigenTemario("MANUAL"); setFuenteTemario(null);
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  function crear() {
    setSeleccion(null); setNuevo(true); setForm(inicial); setTemario(null); setTextoTemario("");
    setEstadoTemario("PENDIENTE_REVISION"); setOrigenTemario("MANUAL"); setFuenteTemario(null); setMensaje(""); setError("");
  }

  async function guardar(e: FormEvent) {
    e.preventDefault(); setGuardando(true); setError(""); setMensaje("");
    const payload = {
      ...form, organismo_id: Number(form.organismo_id), plazas: form.plazas ? Number(form.plazas) : null,
      codigo_externo: form.codigo_externo || null, grupo: form.grupo || null, tipo_proceso: form.tipo_proceso || null,
      sistema_selectivo: form.sistema_selectivo || null, turno: form.turno || null,
      fecha_convocatoria: form.fecha_convocatoria || null, fecha_apertura: form.fecha_apertura || null,
      fecha_cierre: form.fecha_cierre || null, fecha_examen: form.fecha_examen || null,
      lugar_examen: form.lugar_examen || null, observaciones_internas: form.observaciones_internas || null, es_oportunidad: true,
    };
    try {
      const p = nuevo ? await api<Pendiente>("procesos", { method: "POST", body: JSON.stringify(payload) })
        : await api<Pendiente>(`procesos/${seleccion?.id}`, { method: "PUT", body: JSON.stringify(payload) });
      setSeleccion(p); setForm(formularioDe(p)); setNuevo(false); setMensaje("Convocatoria guardada."); await cargar();
    } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setGuardando(false); }
  }

  async function cambiarRevision(estado: string) {
    if (!seleccion) return;
    setGuardando(true); setError(""); setMensaje("");
    try {
      await api(`procesos/${seleccion.id}/revision`, { method: "PATCH", body: JSON.stringify({ estado, observaciones: form.observaciones_internas || null }) });
      setForm((actual) => ({ ...actual, revision_estado: estado })); setSeleccion({ ...seleccion, revision_estado: estado });
      setMensaje(`Estado cambiado a ${estado}.`); await cargar();
    } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setGuardando(false); }
  }

  async function cambiarAmbito(ambito: AmbitoAdministrativo) {
    if (!seleccion) return;
    setGuardando(true); setError(""); setMensaje("");
    try {
      await api(`procesos/${seleccion.id}/ambito-administrativo`, {
        method: "PATCH", body: JSON.stringify({ ambito_administrativo: ambito }),
      });
      setSeleccion({ ...seleccion, ambito_administrativo: ambito });
      setMensaje(ambito === "SI" ? "Incluida en el ámbito administrativo de Tu Coach." : ambito === "NO" ? "Excluida del ámbito administrativo de Tu Coach." : "Marcada para revisión del ámbito administrativo.");
      await cargar();
    } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setGuardando(false); }
  }

  async function extraerTemario() {
    if (!seleccion) return;
    setExtrayendo(true); setError(""); setMensaje("");
    try {
      const resultado = await api<ExtraccionTemario>(`procesos/${seleccion.id}/temario/extraer`, { method: "POST" });
      setTextoTemario(resultado.contenido_texto); setOrigenTemario("AUTOMATICO"); setEstadoTemario("PENDIENTE_REVISION"); setFuenteTemario(resultado.fuente_url);
      setMensaje(`Temario extraído de ${resultado.fuente_titulo || resultado.fuente_referencia || "la fuente oficial"}. Revísalo antes de guardarlo.`);
    } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setExtrayendo(false); }
  }

  async function guardarTemario() {
    if (!seleccion || !textoTemario.trim()) return;
    setGuardando(true); setError(""); setMensaje("");
    try {
      const t = await api<Temario>(`procesos/${seleccion.id}/temario`, {
        method: "PUT",
        body: JSON.stringify({ contenido_texto: textoTemario, origen: origenTemario, estado: estadoTemario, fuente_url: fuenteTemario }),
      });
      setTemario(t); setMensaje("Temario guardado.");
    } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setGuardando(false); }
  }

  if (cargando) return <main style={styles.main}><p>Cargando Centro de gestión…</p></main>;

  const renderItem = (p: Pendiente) => (
    <button type="button" key={p.id} onClick={() => void abrir(p)} style={seleccion?.id === p.id ? styles.itemActive : styles.item}>
      <strong>{p.denominacion}</strong><span>{p.organismo_nombre || "—"}</span><span>{p.origen_dato} · {p.revision_estado} · Administrativo: {p.ambito_administrativo || "REVISION"}</span>
    </button>
  );

  return (
    <main style={styles.main}>
      <header style={styles.header}>
        <div><div style={styles.kicker}>TU COACH · ADMINISTRACIÓN</div><h1 style={styles.title}>Centro de gestión de Empleo</h1><p style={styles.subtitle}>Revisión, edición y mantenimiento de las oportunidades administrativas de empleo público.</p></div>
        <a href="/empleo" style={styles.link}>Volver a Empleo</a>
      </header>
      {error && <div style={styles.error}>{error}</div>}
      {mensaje && <div style={styles.success}>{mensaje}</div>}
      <div style={styles.layout}>
        <aside style={styles.sidebar}>
          <div style={styles.sideHead}><strong>Pendientes de revisión</strong><button type="button" onClick={crear} style={styles.primary}>+ Nueva</button></div>
          {pendientes.length === 0 ? <p style={styles.muted}>No hay pendientes.</p> : pendientes.map(renderItem)}
          <div style={styles.sectionTitle}>Convocatorias existentes</div>
          {convocatorias.length === 0 ? <p style={styles.muted}>No hay convocatorias.</p> : convocatorias.map(renderItem)}
        </aside>
        <section style={styles.content}>
          {!seleccion && !nuevo ? <div style={styles.empty}><h2>Gestión de convocatorias</h2><p>Selecciona una convocatoria pendiente o una convocatoria existente, o crea una nueva.</p></div> : <>
            <form onSubmit={guardar} style={styles.form}>
              <h2>{nuevo ? "Nueva convocatoria" : "Editar convocatoria"}</h2>
              {!nuevo && seleccion && <div style={styles.ambitoBox}>
                <div><strong>Ámbito administrativo de Tu Coach</strong><p style={styles.muted}>Solo las convocatorias marcadas como SI aparecen en el catálogo público. REVISION requiere decisión manual.</p></div>
                <select value={seleccion.ambito_administrativo || "REVISION"} disabled={guardando} onChange={(e) => void cambiarAmbito(e.target.value as AmbitoAdministrativo)} style={styles.status}>
                  <option value="SI">SI · Administrativa</option>
                  <option value="NO">NO · Fuera de ámbito</option>
                  <option value="REVISION">REVISION · Decidir manualmente</option>
                </select>
              </div>}
              <div style={styles.grid}>
                <label>Organismo<select value={form.organismo_id} onChange={(e) => setForm({ ...form, organismo_id: e.target.value })}><option value="1">Generalitat Valenciana</option><option value="2">Diputación de Valencia</option></select></label>
                <label>Denominación<input required value={form.denominacion} onChange={(e) => setForm({ ...form, denominacion: e.target.value })} /></label>
                <label>Código externo<input value={form.codigo_externo} onChange={(e) => setForm({ ...form, codigo_externo: e.target.value })} /></label>
                <label>Grupo<input value={form.grupo} onChange={(e) => setForm({ ...form, grupo: e.target.value })} /></label>
                <label>Tipo de proceso<input value={form.tipo_proceso} onChange={(e) => setForm({ ...form, tipo_proceso: e.target.value })} /></label>
                <label>Sistema selectivo<input value={form.sistema_selectivo} onChange={(e) => setForm({ ...form, sistema_selectivo: e.target.value })} /></label>
                <label>Turno<input value={form.turno} onChange={(e) => setForm({ ...form, turno: e.target.value })} /></label>
                <label>Plazas<input type="number" min="0" value={form.plazas} onChange={(e) => setForm({ ...form, plazas: e.target.value })} /></label>
                <label>Estado<input value={form.estado} onChange={(e) => setForm({ ...form, estado: e.target.value })} /></label>
                <label>Revisión<select value={form.revision_estado} onChange={(e) => setForm({ ...form, revision_estado: e.target.value })}><option>PENDIENTE_REVISION</option><option>PUBLICADA</option><option>DESCARTADA</option></select></label>
                <label>Fecha convocatoria<input type="date" value={form.fecha_convocatoria} onChange={(e) => setForm({ ...form, fecha_convocatoria: e.target.value })} /></label>
                <label>Inicio inscripción<input type="date" value={form.fecha_apertura} onChange={(e) => setForm({ ...form, fecha_apertura: e.target.value })} /></label>
                <label>Cierre inscripción<input type="date" value={form.fecha_cierre} onChange={(e) => setForm({ ...form, fecha_cierre: e.target.value })} /></label>
                <label>Fecha examen<input type="date" value={form.fecha_examen} onChange={(e) => setForm({ ...form, fecha_examen: e.target.value })} /></label>
                <label>Lugar examen<input value={form.lugar_examen} onChange={(e) => setForm({ ...form, lugar_examen: e.target.value })} /></label>
              </div>
              <label>Observaciones internas<textarea rows={4} value={form.observaciones_internas} onChange={(e) => setForm({ ...form, observaciones_internas: e.target.value })} /></label>
              <div style={styles.actions}><button type="submit" disabled={guardando} style={styles.primary}>{guardando ? "Guardando…" : "Guardar"}</button>{!nuevo && <><button type="button" disabled={guardando} onClick={() => void cambiarRevision("PUBLICADA")} style={styles.secondary}>Publicar</button><button type="button" disabled={guardando} onClick={() => void cambiarRevision("DESCARTADA")} style={styles.danger}>Descartar</button></>}</div>
            </form>
            {!nuevo && seleccion && <section style={styles.form}>
              <h2>Temario oficial</h2>
              <p style={styles.muted}>Se conserva el texto literal del temario de la convocatoria. La extracción automática solo propone el texto; no lo publica sin revisión.</p>
              <div style={styles.temarioActions}><button type="button" disabled={extrayendo || guardando} onClick={() => void extraerTemario()} style={styles.primary}>{extrayendo ? "Extrayendo…" : "Extraer de fuente oficial"}</button></div>
              <select value={estadoTemario} onChange={(e) => setEstadoTemario(e.target.value)} style={styles.status}><option>PENDIENTE_REVISION</option><option>VERIFICADO</option><option>DESCARTADO</option></select>
              <textarea rows={18} value={textoTemario} onChange={(e) => setTextoTemario(e.target.value)} placeholder="Pegar aquí el temario oficial…" style={styles.temario} />
              {fuenteTemario && <div style={styles.source}>Fuente: <a href={fuenteTemario} target="_blank" rel="noreferrer">publicación oficial</a> · Origen: {origenTemario}</div>}
              <button type="button" disabled={guardando || !textoTemario.trim()} onClick={() => void guardarTemario()} style={styles.primary}>Guardar temario</button>
              {temario && <p style={styles.muted}>Origen almacenado: {temario.origen} · Estado: {temario.estado}</p>}
            </section>}
          </>}
        </section>
      </div>
    </main>
  );
}

const styles: Record<string, CSSProperties> = {
  main: { maxWidth: 1440, margin: "0 auto", padding: "32px 20px 60px", fontFamily: "system-ui, sans-serif", color: "#172033" },
  header: { display: "flex", justifyContent: "space-between", gap: 24, alignItems: "flex-start", marginBottom: 24 },
  kicker: { fontSize: 12, letterSpacing: 1.4, fontWeight: 700, opacity: 0.6 }, title: { fontSize: 32, margin: "6px 0" }, subtitle: { opacity: 0.7 }, link: { color: "inherit", fontWeight: 600 },
  layout: { display: "grid", gridTemplateColumns: "360px minmax(0, 1fr)", gap: 18, alignItems: "start" }, sidebar: { border: "1px solid #d9dee8", borderRadius: 12, background: "#fff", padding: 14, position: "sticky", top: 18, maxHeight: "calc(100vh - 36px)", overflow: "auto" },
  sideHead: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }, sectionTitle: { fontWeight: 700, padding: "18px 8px 8px", borderTop: "1px solid #d9dee8", marginTop: 10 },
  item: { display: "flex", flexDirection: "column", gap: 4, width: "100%", textAlign: "left", padding: "12px 10px", marginBottom: 6, border: "1px solid transparent", borderRadius: 9, background: "transparent", cursor: "pointer" }, itemActive: { display: "flex", flexDirection: "column", gap: 4, width: "100%", textAlign: "left", padding: "12px 10px", marginBottom: 6, border: "1px solid #172033", borderRadius: 9, background: "#edf2f8", cursor: "pointer" },
  content: { minWidth: 0 }, empty: { border: "1px solid #d9dee8", borderRadius: 12, padding: 28, background: "#fff" }, form: { border: "1px solid #d9dee8", borderRadius: 12, padding: 22, background: "#fff", marginBottom: 18 }, grid: { display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 14 }, actions: { display: "flex", gap: 10, marginTop: 16, flexWrap: "wrap" }, temarioActions: { display: "flex", gap: 10, marginBottom: 10 },
  ambitoBox: { display: "flex", justifyContent: "space-between", alignItems: "center", gap: 18, padding: 14, marginBottom: 18, border: "1px solid #c8ced9", borderRadius: 9, background: "#f7f9fc" },
  primary: { border: 0, borderRadius: 8, padding: "9px 14px", background: "#172033", color: "#fff", fontWeight: 700, cursor: "pointer" }, secondary: { border: "1px solid #c8ced9", borderRadius: 8, padding: "9px 14px", background: "#fff", cursor: "pointer" }, danger: { border: "1px solid #c8ced9", borderRadius: 8, padding: "9px 14px", background: "#fff", color: "#8b1e1e", cursor: "pointer" }, status: { padding: 9, border: "1px solid #c8ced9", borderRadius: 7, marginBottom: 10 }, temario: { display: "block", width: "100%", boxSizing: "border-box", margin: "8px 0 12px", padding: 12, border: "1px solid #c8ced9", borderRadius: 8, fontFamily: "inherit", resize: "vertical" }, source: { marginBottom: 12, fontSize: 14, opacity: 0.7 }, error: { padding: 12, marginBottom: 14, borderRadius: 8, background: "#fff0f0", color: "#8b1e1e" }, success: { padding: 12, marginBottom: 14, borderRadius: 8, background: "#f0f6f0" }, muted: { opacity: 0.65, fontSize: 14 },
};