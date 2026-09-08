"use client";

import { FormEvent, useEffect, useState } from "react";

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
  fecha_apertura: string | null;
  fecha_cierre: string | null;
  fecha_examen: string | null;
};

type Proceso = Pendiente & Record<string, unknown>;
type Temario = { contenido_texto: string; origen: string; estado: string; fuente_url: string | null; observaciones: string | null } | null;

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`/api/empleo/admin/gestion/${path.replace(/^\/+/, "")}`, { cache: "no-store", ...init, headers: { "Content-Type": "application/json", ...(init?.headers || {}) } });
  const text = await r.text();
  let body: unknown = null;
  try { body = text ? JSON.parse(text) : null; } catch { body = text; }
  if (!r.ok) {
    const detail = body && typeof body === "object" && "detail" in body ? String((body as { detail: unknown }).detail) : `HTTP ${r.status}`;
    throw new Error(detail);
  }
  return body as T;
}

function fecha(v: string | null) { return v ? new Date(v).toLocaleDateString("es-ES") : "—"; }

export default function EmpleoAdminPage() {
  const [pendientes, setPendientes] = useState<Pendiente[]>([]);
  const [seleccion, setSeleccion] = useState<Proceso | null>(null);
  const [temario, setTemario] = useState<Temario>(null);
  const [cargando, setCargando] = useState(true);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState("");
  const [mensaje, setMensaje] = useState("");
  const [modoNuevo, setModoNuevo] = useState(false);
  const [form, setForm] = useState({ organismo_id: "1", denominacion: "", codigo_externo: "", grupo: "", tipo_proceso: "Oposición", sistema_selectivo: "Oposición", turno: "TURNO_LIBRE", plazas: "", estado: "EN_CURSO", fecha_convocatoria: "", fecha_apertura: "", fecha_cierre: "", fecha_examen: "", lugar_examen: "", revision_estado: "PENDIENTE_REVISION", observaciones_internas: "" });
  const [textoTemario, setTextoTemario] = useState("");
  const [estadoTemario, setEstadoTemario] = useState("PENDIENTE_REVISION");

  async function cargar() {
    setCargando(true); setError("");
    try { setPendientes(await api<Pendiente[]>("pendientes?limite=200")); }
    catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setCargando(false); }
  }

  useEffect(() => { void cargar(); }, []);

  async function abrir(id: number) {
    setError(""); setMensaje(""); setModoNuevo(false);
    try {
      const p = await api<Proceso>(`procesos/${id}`);
      setSeleccion(p);
      setForm({
        organismo_id: String(p.organismo_id), denominacion: p.denominacion || "", codigo_externo: p.codigo_externo || "",
        grupo: p.grupo || "", tipo_proceso: p.tipo_proceso || "", sistema_selectivo: p.sistema_selectivo || "", turno: p.turno || "",
        plazas: p.plazas == null ? "" : String(p.plazas), estado: p.estado || "EN_CURSO", fecha_convocatoria: String(p.fecha_convocatoria || "").slice(0,10),
        fecha_apertura: String(p.fecha_apertura || "").slice(0,10), fecha_cierre: String(p.fecha_cierre || "").slice(0,10), fecha_examen: String(p.fecha_examen || "").slice(0,10),
        lugar_examen: p.lugar_examen || "", revision_estado: p.revision_estado || "PENDIENTE_REVISION", observaciones_internas: p.observaciones_internas || ""
      });
      const t = await api<Temario>(`procesos/${id}/temario`);
      setTemario(t); setTextoTemario(t?.contenido_texto || ""); setEstadoTemario(t?.estado || "PENDIENTE_REVISION");
    } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
  }

  function nuevo() {
    setSeleccion(null); setTemario(null); setTextoTemario(""); setEstadoTemario("PENDIENTE_REVISION"); setModoNuevo(true); setMensaje("");
    setForm({ organismo_id: "1", denominacion: "", codigo_externo: "", grupo: "", tipo_proceso: "Oposición", sistema_selectivo: "Oposición", turno: "TURNO_LIBRE", plazas: "", estado: "EN_CURSO", fecha_convocatoria: "", fecha_apertura: "", fecha_cierre: "", fecha_examen: "", lugar_examen: "", revision_estado: "PENDIENTE_REVISION", observaciones_internas: "" });
  }

  async function guardar(e: FormEvent) {
    e.preventDefault(); setGuardando(true); setError(""); setMensaje("");
    const payload = { ...form, organismo_id: Number(form.organismo_id), plazas: form.plazas ? Number(form.plazas) : null, codigo_externo: form.codigo_externo || null, grupo: form.grupo || null, tipo_proceso: form.tipo_proceso || null, sistema_selectivo: form.sistema_selectivo || null, turno: form.turno || null, fecha_convocatoria: form.fecha_convocatoria || null, fecha_apertura: form.fecha_apertura || null, fecha_cierre: form.fecha_cierre || null, fecha_examen: form.fecha_examen || null, lugar_examen: form.lugar_examen || null, observaciones_internas: form.observaciones_internas || null, es_oportunidad: true };
    try {
      const p = modoNuevo ? await api<Proceso>("procesos", { method: "POST", body: JSON.stringify(payload) }) : await api<Proceso>(`procesos/${seleccion?.id}`, { method: "PUT", body: JSON.stringify(payload) });
      setSeleccion(p); setModoNuevo(false); setMensaje("Convocatoria guardada."); await cargar();
    } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setGuardando(false); }
  }

  async function revisar(estado: string) {
    if (!seleccion) return; setGuardando(true); setError(""); setMensaje("");
    try { await api(`procesos/${seleccion.id}/revision`, { method: "PATCH", body: JSON.stringify({ estado, observaciones: form.observaciones_internas || null }) }); setForm(f => ({ ...f, revision_estado: estado })); setSeleccion({ ...seleccion, revision_estado: estado }); setMensaje(`Estado cambiado a ${estado}.`); await cargar(); }
    catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setGuardando(false); }
  }

  async function guardarTemario() {
    if (!seleccion || !textoTemario.trim()) return; setGuardando(true); setError("");
    try { await api(`procesos/${seleccion.id}/temario`, { method: "PUT", body: JSON.stringify({ contenido_texto: textoTemario, origen: "MANUAL", estado: estadoTemario }) }); setMensaje("Temario guardado."); }
    catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setGuardando(false); }
  }

  if (cargando) return <main style={s.main}><p>Cargando Centro de gestión…</p></main>;

  return <main style={s.main}>
    <header style={s.header}><div><div style={s.kicker}>TU COACH · ADMINISTRACIÓN</div><h1 style={s.title}>Centro de gestión de Empleo</h1><p style={s.subtitle}>Revisión, edición y mantenimiento de las oportunidades de empleo público.</p></div><a href="/empleo" style={s.link}>Volver a Empleo</a></header>
    {error && <div style={s.error}>{error}</div>}{mensaje && <div style={s.success}>{mensaje}</div>}
    <div style={s.layout}>
      <aside style={s.sidebar}><div style={s.sideHead}><strong>Pendientes de revisión</strong><button onClick={nuevo} style={s.primary}>+ Nueva</button></div>{pendientes.length === 0 ? <p style={s.muted}>No hay pendientes.</p> : pendientes.map(p => <button key={p.id} onClick={() => void abrir(p.id)} style={seleccion?.id === p.id ? s.itemActive : s.item}><strong>{p.denominacion}</strong><span>{p.organismo_nombre || "—"}</span><span>{p.origen_dato} · {p.revision_estado}</span></button>)}</aside>
      <section style={s.content}>
        {!seleccion && !modoNuevo ? <div style={s.empty}><h2>Gestión de convocatorias</h2><p>Selecciona una pendiente o crea una convocatoria manualmente.</p></div> : <>
          <form onSubmit={guardar} style={s.form}><h2>{modoNuevo ? "Nueva convocatoria" : "Editar convocatoria"}</h2><div style={s.grid}>
            <label>Organismo<select value={form.organismo_id} onChange={e => setForm({...form, organismo_id:e.target.value})}><option value="1">Generalitat Valenciana</option><option value="2">Diputación de Valencia</option><option value="3">Ayuntamiento de València</option></select></label>
            <label>Denominación<input required value={form.denominacion} onChange={e => setForm({...form, denominacion:e.target.value})}/></label>
            <label>Código externo<input value={form.codigo_externo} onChange={e => setForm({...form, codigo_externo:e.target.value})}/></label><label>Grupo<input value={form.grupo} onChange={e => setForm({...form, grupo:e.target.value})}/></label>
            <label>Tipo de proceso<input value={form.tipo_proceso} onChange={e => setForm({...form, tipo_proceso:e.target.value})}/></label><label>Sistema selectivo<input value={form.sistema_selectivo} onChange={e => setForm({...form, sistema_selectivo:e.target.value})}/></label>
            <label>Turno<input value={form.turno} onChange={e => setForm({...form, turno:e.target.value})}/></label><label>Plazas<input type="number" min="0" value={form.plazas} onChange={e => setForm({...form, plazas:e.target.value})}/></label>
            <label>Estado<input value={form.estado} onChange={e => setForm({...form, estado:e.target.value})}/></label><label>Revisión<select value={form.revision_estado} onChange={e => setForm({...form, revision_estado:e.target.value})}><option>PENDIENTE_REVISION</option><option>PUBLICADA</option><option>DESCARTADA</option></select></label>
            <label>Fecha convocatoria<input type="date" value={form.fecha_convocatoria} onChange={e => setForm({...form, fecha_convocatoria:e.target.value})}/></label><label>Inicio inscripción<input type="date" value={form.fecha_apertura} onChange={e => setForm({...form, fecha_apertura:e.target.value})}/></label>
            <label>Cierre inscripción<input type="date" value={form.fecha_cierre} onChange={e => setForm({...form, fecha_cierre:e.target.value})}/></label><label>Fecha examen<input type="date" value={form.fecha_examen} onChange={e => setForm({...form, fecha_examen:e.target.value})}/></label>
            <label>Lugar examen<input value={form.lugar_examen} onChange={e => setForm({...form, lugar_examen:e.target.value})}/></label>
          </div><label>Observaciones internas<textarea rows={4} value={form.observaciones_internas} onChange={e => setForm({...form, observaciones_internas:e.target.value})}/></label><div style={s.actions}><button disabled={guardando} style={s.primary}>{guardando ? "Guardando…" : "Guardar"}</button>{!modoNuevo && <><button type="button" disabled={guardando} onClick={() => void revisar("PUBLICADA")} style={s.secondary}>Publicar</button><button type="button" disabled={guardando} onClick={() => void revisar("DESCARTADA")} style={s.danger}>Descartar</button></>}</div></form>
          {!modoNuevo && seleccion && <section style={s.form}><h2>Temario oficial</h2><p style={s.muted}>Se conserva el texto literal del temario de la convocatoria. La comparación semántica se incorporará en una fase posterior.</p><select value={estadoTemario} onChange={e => setEstadoTemario(e.target.value)} style={s.status}><option>PENDIENTE_REVISION</option><option>VERIFICADO</option><option>DESCARTADO</option></select><textarea rows={18} value={textoTemario} onChange={e => setTextoTemario(e.target.value)} placeholder="Pegar aquí el temario oficial…" style={s.temario}/><button disabled={guardando || !textoTemario.trim()} onClick={() => void guardarTemario()} style={s.primary}>Guardar temario</button></section>}
          {!modoNuevo && seleccion && <div style={s.metaBox}><strong>Ficha interna</strong><div>ID {seleccion.id} · origen {String(seleccion.origen_dato || "—")} · actualizado {fecha(String(seleccion.updated_at || ""))}</div></div>}
        </>}
      </section>
    </div>
  </main>;
}

const s: Record<string, React.CSSProperties> = {
  main:{maxWidth:1440,margin:"0 auto",padding:"32px 20px 60px",fontFamily:"system-ui,sans-serif",color:"#172033"},header:{display:"flex",justifyContent:"space-between",gap:24,alignItems:"flex-start",marginBottom:24},kicker:{fontSize:12,letterSpacing:1.4,fontWeight:700,opacity:.6},title:{fontSize:32,margin:"6px 0"},subtitle:{opacity:.7},link:{color:"inherit",fontWeight:600},layout:{display:"grid",gridTemplateColumns:"360px minmax(0,1fr)",gap:18,alignItems:"start"},sidebar:{border:"1px solid #d9dee8",borderRadius:12,background:"#fff",padding:14,position:"sticky",top:18,maxHeight:"calc(100vh - 36px)",overflow:"auto"},sideHead:{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:10},item:{display:"flex",flexDirection:"column",gap:4,width:"100%",textAlign:"left",padding:"12px 10px",marginBottom:6,border:"1px solid transparent",borderRadius:9,background:"transparent",cursor:"pointer"},itemActive:{display:"flex",flexDirection:"column",gap:4,width:"100%",textAlign:"left",padding:"12px 10px",marginBottom:6,border:"1px solid #172033",borderRadius:9,background:"#edf2f8",cursor:"pointer"},content:{minWidth:0},empty:{border:"1px solid #d9dee8",borderRadius:12,padding:28,background:"#fff"},form:{border:"1px solid #d9dee8",borderRadius:12,padding:22,background:"#fff",marginBottom:18},grid:{display:"grid",gridTemplateColumns:"repeat(2,minmax(0,1fr))",gap:14},formLabel:{},form:"",actions:{display:"flex",gap:10,marginTop:16,flexWrap:"wrap"},primary:{border:0,borderRadius:8,padding:"9px 14px",background:"#172033",color:"#fff",fontWeight:700,cursor:"pointer"},secondary:{border:"1px solid #c8ced9",borderRadius:8,padding:"9px 14px",background:"#fff",cursor:"pointer"},danger:{border:"1px solid #c8ced9",borderRadius:8,padding:"9px 14px",background:"#fff",color:"#8b1e1e",cursor:"pointer"},status:{padding:9,border:"1px solid #c8ced9",borderRadius:7,marginBottom:10},temario:{display:"block",width:"100%",boxSizing:"border-box",margin:"8px 0 12px",padding:12,border:"1px solid #c8ced9",borderRadius:8,fontFamily:"inherit",resize:"vertical"},metaBox:{border:"1px solid #d9dee8",borderRadius:12,padding:16,background:"#f8f9fb"},error:{padding:12,marginBottom:14,borderRadius:8,background:"#fff0f0",color:"#8b1e1e"},success:{padding:12,marginBottom:14,borderRadius:8,background:"#f0f6f0"},muted:{opacity:.65,fontSize:14}
};
