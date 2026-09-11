"use client";

import { useEffect, useMemo, useState } from "react";
import { usePathname } from "next/navigation";
import { createClient } from "@/lib/supabase/client";

type Novedad = { id:number; proceso_id:number; novedad_tipo:"PUBLICACION"|"CAMBIO"; tipo:string|null; campo:string|null; resumen:string|null; detectado_at:string|null };
type Estado = { ultima_novedad_vista_at:string|null };
type Suscripcion = { proceso_id:number };

const CAMPOS_RELEVANTES=new Set(["fecha_apertura","fecha_cierre","fecha_examen","estado","plazas","turno","etapa_actual","tipo_proceso","url_oficial"]);
const TIPOS_PUBLICACION=["convocatoria","bases","admitidos","excluidos","tribunal","fecha","lugar","examen","modificacion","modificación","resultado","calificacion","calificación","nombramiento","adjudicacion","adjudicación","lista","seguimiento"];
function esPublicacionUtil(n:Novedad){const texto=`${n.tipo||""} ${n.resumen||""}`.toLowerCase().trim();if(!texto)return false;if(/\bnavegaci[oó]n\b/.test(texto)&&texto.length<=80)return false;return TIPOS_PUBLICACION.some(x=>texto.includes(x));}
function esCambioUtil(n:Novedad){if(n.novedad_tipo!=="CAMBIO")return false;const campo=(n.campo||"").toLowerCase();if(CAMPOS_RELEVANTES.has(campo))return true;const texto=`${n.tipo||""} ${n.resumen||""}`.toLowerCase();return /(plazo|fecha de examen|fecha examen|lugar de examen|n[uú]mero de plazas|turno|etapa|estado del proceso|tribunal)/i.test(texto);}

export default function NovedadesAviso(){
 const pathname=usePathname();const supabase=useMemo(()=>createClient(),[]);const [cantidad,setCantidad]=useState(0);const [cargando,setCargando]=useState(true);const [error,setError]=useState(false);
 useEffect(()=>{if(pathname!=="/empleo"){setCargando(false);return;}let activo=true;(async()=>{try{const {data,error:e}=await supabase.auth.getSession();if(e||!data.session){if(activo)setCargando(false);return;}const token=data.session.access_token;const headers={Authorization:`Bearer ${token}`};const[nr,er,sr]=await Promise.all([fetch("/api/empleo/seguimiento/cambios",{cache:"no-store",headers}),fetch("/api/empleo/seguimiento/estado",{cache:"no-store",headers}),fetch("/api/empleo/suscripciones",{cache:"no-store",headers})]);if(!nr.ok||!er.ok||!sr.ok)throw new Error("No se pudo consultar el seguimiento");const novedades=(await nr.json()) as Novedad[];const estado=(await er.json()) as Estado;const suscripciones=(await sr.json()) as Suscripcion[];if(!activo)return;if(!estado.ultima_novedad_vista_at){setCantidad(0);setCargando(false);return;}const seguidas=new Set(suscripciones.map(s=>s.proceso_id));const visto=new Date(estado.ultima_novedad_vista_at).getTime();const total=novedades.filter(n=>seguidas.has(n.proceso_id)&&(n.novedad_tipo==="PUBLICACION"?esPublicacionUtil(n):esCambioUtil(n))&&(n.detectado_at?new Date(n.detectado_at).getTime():0)>visto).length;setCantidad(total);}catch{if(activo)setError(true)}finally{if(activo)setCargando(false)}})();return()=>{activo=false};},[pathname,supabase]);
 if(pathname!=="/empleo"||cargando||error||cantidad===0)return null;
 return <div role="status" style={s.notice}><div><strong>Tienes {cantidad} {cantidad===1?"novedad nueva":"novedades nuevas"}</strong><span style={s.texto}> en las convocatorias que sigues.</span></div><a href="/empleo/seguimiento" style={s.link}>Ver Mi seguimiento →</a></div>;
}
const s:Record<string,React.CSSProperties>={notice:{display:"flex",justifyContent:"space-between",alignItems:"center",gap:18,maxWidth:1280,margin:"0 auto 18px",padding:"13px 16px",border:"1px solid #cfd6e2",borderRadius:10,background:"#fff",color:"#172033",boxShadow:"0 2px 8px rgba(23,32,51,.05)"},texto:{marginLeft:4,opacity:.72},link:{fontWeight:650,textDecoration:"none",whiteSpace:"nowrap"}};