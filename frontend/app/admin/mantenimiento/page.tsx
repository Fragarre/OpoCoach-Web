"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { apiFetch } from "@/lib/api";

type Convocatoria = { id: number; codigo: string; puesto: string; numero: string; anio: number };

type Job = {
  id: string;
  tipo: string;
  estado: string;
  creado_at: string;
  iniciado_at?: string | null;
  finalizado_at?: string | null;
  resultado?: { returncode?: number; salida?: string; review?: Record<string, unknown> } | null;
  error_texto?: string | null;
};

const ACTIVOS = new Set(["PENDIENTE", "RECOGIDO", "EJECUTANDO", "ESPERANDO_CONFIRMACION"]);

const BLOQUES_OPERACIONES = [
  {
    titulo: "Validación general",
    operaciones: [
      {
        tipo: "AUDITORIA_BD",
        titulo: "Auditoría general de la BD",
        descripcion: "Comprueba estructura, integridad, distribución, problemas objetivos y duplicados de la base maestra.",
        boton: "Ejecutar auditoría",
      },
      {
        tipo: "VALIDACION_COMPLETA",
        titulo: "Validación completa",
        descripcion: "Comprueba integridad, bancos, duplicados, referencias jurídicas, modelos y auditorías sin guardar cambios en la base.",
        boton: "Ejecutar validación",
      },
    ],
  },
  {
    titulo: "Bancos de preguntas",
    operaciones: [
      {
        tipo: "SINCRONIZAR_BANCOS",
        titulo: "Sincronizar todos los bancos",
        descripcion: "Revisa todos los bancos activos y muestra las vinculaciones nuevas, retirables o reasignables. Aplicar cambios requiere confirmación explícita y crea un backup global.",
        boton: "Revisar sincronización",
        requiereConfirmacion: true,
      },
      {
        tipo: "AUDITORIA_CONSISTENCIA_GLOBAL",
        titulo: "Auditoría de consistencia global lote ↔ banco",
        descripcion: "Contrasta lote, banco real, selección esperada, temario, duplicados e integridad para una convocatoria.",
        boton: "Auditar consistencia",
        generaInforme: true,
        requiereConvocatoria: true,
      },
      {
        tipo: "AUDITORIA_ESTRUCTURA_BANCO",
        titulo: "Auditoría de estructura del banco",
        descripcion: "Inspecciona tablas, columnas, índices y claves foráneas relacionadas con los bancos.",
        boton: "Auditar estructura",
      },
      {
        tipo: "AUDITORIA_FUNCIONAL_BANCO",
        titulo: "Auditoría funcional de banco",
        descripcion: "Audita el banco de una convocatoria concreta y genera el informe diagnóstico local.",
        boton: "Auditar banco",
        generaInforme: true,
        requiereConvocatoria: true,
      },
      {
        tipo: "AUDITORIA_BANCOS_SELECCION",
        titulo: "Auditoría de selección de bancos",
        descripcion: "Reconstruye virtualmente la selección de los bancos activos y la compara con las preguntas almacenadas.",
        boton: "Auditar bancos",
      },
    ],
  },
  {
    titulo: "Generación de preguntas",
    operaciones: [
      {
        tipo: "GENERAR_PREGUNTAS_JURIDICAS_IA",
        titulo: "Generar preguntas jurídicas mediante IA",
        descripcion: "Ejecuta el mismo generador jurídico del mantenimiento local. Las preguntas aceptadas pueden incorporarse a la base maestra y después se sincronizan los bancos y se ejecuta la validación completa.",
        boton: "Generar preguntas",
        usaIa: true,
        modificaDatos: true,
        requiereGeneracionJuridica: true,
      },
    ],
  },
  {
    titulo: "Temario y normativa",
    operaciones: [
      {
        tipo: "MANTENIMIENTO_TEMARIO",
        titulo: "Mantenimiento controlado del temario",
        descripcion: "Revisa el temario.csv de una convocatoria. La primera fase no modifica datos; cualquier continuación requiere confirmación explícita.",
        boton: "Revisar temario",
        requiereConvocatoria: true,
        requiereConfirmacion: true,
      },
      {
        tipo: "AUDITORIA_CORPUS_TEMARIO",
        titulo: "Auditoría del temario/corpus",
        descripcion: "Comprueba referencias jurídicas y artículos fuente del temario y genera un informe diagnóstico en el repositorio local.",
        boton: "Auditar corpus",
        generaInforme: true,
      },
      {
        tipo: "BUSCAR_NORMA_RESPUESTA_CORRECTA",
        titulo: "Buscar norma por respuesta correcta",
        descripcion: "Usa IA para proponer norma y artículo a partir de la respuesta correcta de preguntas PENDIENTE. Sustituye el informe local anterior de esta misma auditoría.",
        boton: "Buscar norma",
        generaInforme: true,
        usaIa: true,
        requiereBusquedaNorma: true,
      },
      {
        tipo: "INVENTARIO_DENOMINACIONES_NORMAS",
        titulo: "Denominaciones de normas",
        descripcion: "Genera el inventario de denominaciones jurídicas presentes en lote_preguntas para diagnosticar la normalización.",
        boton: "Generar inventario",
        generaInforme: true,
      },
    ],
  },
  {
    titulo: "Materiales de estudio",
    operaciones: [
      {
        tipo: "AUDITORIA_MATERIALES_ESTUDIO",
        titulo: "Materiales de estudio",
        descripcion: "Contrasta los materiales preparados con las normas activas y la huella actual del corpus normativo.",
        boton: "Auditar materiales",
      },
    ],
  },
  {
    titulo: "Diagnóstico técnico",
    operaciones: [
      {
        tipo: "AUDITORIA_ESQUEMA_OBSOLETO",
        titulo: "Posibles objetos obsoletos",
        descripcion: "Inventaría tablas, columnas y referencias de código para diagnosticar deuda técnica. No elimina objetos.",
        boton: "Auditar esquema",
        generaInforme: true,
      },
    ],
  },
] as const;

export default function MantenimientoPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [cargando, setCargando] = useState(true);
  const [lanzando, setLanzando] = useState<string | null>(null);
  const [accionJob, setAccionJob] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [convocatorias, setConvocatorias] = useState<Convocatoria[]>([]);
  const [convocatoriaId, setConvocatoriaId] = useState<number | null>(null);
  const [modoBusquedaNorma, setModoBusquedaNorma] = useState<"pregunta" | "lote">("lote");
  const [preguntaId, setPreguntaId] = useState("1");
  const [limiteBusqueda, setLimiteBusqueda] = useState("20");
  const [tipoJuridica, setTipoJuridica] = useState<"TEORICA" | "PRACTICA">("TEORICA");
  const [ambitoJuridica, setAmbitoJuridica] = useState<"MODELO_EXAMEN" | "TEMA" | "TODOS_TEMAS">("MODELO_EXAMEN");
  const [temaIdJuridica, setTemaIdJuridica] = useState("1");
  const [cantidadJuridica, setCantidadJuridica] = useState("1");

  async function cargar() {
    try {
      const datos = await apiFetch<Job[]>("/api/v1/admin/jobs?limite=20");
      setJobs(datos);
      setError(null);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "No se pudieron cargar los trabajos.");
    } finally {
      setCargando(false);
    }
  }

  useEffect(() => {
    void cargar();
    void apiFetch<Convocatoria[]>("/api/v1/convocatorias")
      .then((datos) => {
        setConvocatorias(datos);
        if (datos.length > 0) setConvocatoriaId(datos[0].id);
      })
      .catch((exc) => setError(exc instanceof Error ? exc.message : "No se pudieron cargar las convocatorias."));
    const timer = window.setInterval(() => void cargar(), 5000);
    return () => window.clearInterval(timer);
  }, []);

  const activo = useMemo(() => jobs.find((job) => ACTIVOS.has(job.estado)), [jobs]);

  async function resolverConfirmacion(jobId: string, accion: "confirmar" | "cancelar") {
    setAccionJob(`${jobId}:${accion}`);
    setError(null);
    try {
      await apiFetch<Job>(`/api/v1/admin/jobs/${jobId}/${accion}`, { method: "POST" });
      await cargar();
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : `No se pudo ${accion} el trabajo.`);
    } finally {
      setAccionJob(null);
    }
  }

  async function lanzar(tipo: string, requiereConvocatoria = false, requiereBusquedaNorma = false, requiereGeneracionJuridica = false) {
    setLanzando(tipo);
    setError(null);
    try {
      if (requiereGeneracionJuridica) {
        const confirmado = window.confirm(
          "Esta operación usa IA (tiene coste) y puede modificar la base maestra, sincronizar los bancos y ejecutar la validación completa. ¿Deseas continuar?"
        );
        if (!confirmado) return;
      }
      await apiFetch<Job>("/api/v1/admin/jobs", {
        method: "POST",
        body: JSON.stringify({
          tipo,
          parametros: requiereGeneracionJuridica
            ? {
                convocatoria_id: convocatoriaId,
                tipo: tipoJuridica,
                cantidad: Number(cantidadJuridica),
                ambito: ambitoJuridica,
                ...(ambitoJuridica === "TEMA" ? { tema_id: Number(temaIdJuridica) } : {}),
              }
            : requiereConvocatoria
              ? { convocatoria_id: convocatoriaId }
              : requiereBusquedaNorma
              ? modoBusquedaNorma === "pregunta"
                ? { pregunta_id: Number(preguntaId) }
                : { limite: Number(limiteBusqueda) }
              : {},
        }),
      });
      await cargar();
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "No se pudo crear el trabajo.");
    } finally {
      setLanzando(null);
    }
  }

  return (
    <main style={{ maxWidth: 1040, margin: "0 auto", padding: "40px 20px 64px" }}>
      <header style={{ marginBottom: 28 }}>
        <p style={{ margin: 0, fontSize: 13, fontWeight: 700, letterSpacing: "0.08em" }}>
          TU COACH · ADMINISTRACIÓN
        </p>
        <h1 style={{ margin: "8px 0 10px" }}>Mantenimiento</h1>
        <p style={{ margin: 0, maxWidth: 760, color: "#555", lineHeight: 1.55 }}>
          Ejecución controlada de operaciones sobre el repositorio local de mantenimiento.
          Las auditorías no modifican la base de datos. Las operaciones de mantenimiento se ejecutan por fases y requieren confirmación explícita antes de aplicar cambios.
        </p>
      </header>

      <section style={{ display: "grid", gap: 14 }}>
        {BLOQUES_OPERACIONES.map((bloque) => (
          <section key={bloque.titulo} style={{ display: "grid", gap: 12 }}>
            <h2 style={{ margin: "12px 0 0", fontSize: 22 }}>{bloque.titulo}</h2>
            {bloque.operaciones.map((operacion) => (
          <article
            key={operacion.tipo}
            style={{ border: "1px solid #d9d9d9", borderRadius: 12, padding: 20, background: "#fff" }}
          >
            <div style={{ display: "flex", gap: 12, alignItems: "center", justifyContent: "space-between", flexWrap: "wrap" }}>
              <div style={{ flex: "1 1 620px" }}>
                <div style={{ fontSize: 11, fontWeight: 700, marginBottom: 6 }}>
                  {("requiereConfirmacion" in operacion && operacion.requiereConfirmacion)
                    ? "REVIEW · REQUIERE CONFIRMACIÓN · APPLY MODIFICA DATOS · CREA BACKUP"
                    : ("modificaDatos" in operacion && operacion.modificaDatos)
                      ? `MODIFICA DATOS · IA · COSTE · CONFIRMACIÓN PREVIA`
                      : `NO MODIFICA BD${("generaInforme" in operacion && operacion.generaInforme) ? " · GENERA INFORME LOCAL" : ""}${("usaIa" in operacion && operacion.usaIa) ? " · IA · COSTE" : ""}`}
                </div>
                <h2 style={{ margin: "0 0 6px", fontSize: 20 }}>{operacion.titulo}</h2>
                <p style={{ margin: 0, color: "#555" }}>{operacion.descripcion}</p>
                {"requiereGeneracionJuridica" in operacion && operacion.requiereGeneracionJuridica && (
                  <div style={{ marginTop: 12, display: "flex", gap: 8, flexWrap: "wrap" }}>
                    <select value={convocatoriaId ?? ""} onChange={(event) => setConvocatoriaId(Number(event.target.value))} disabled={Boolean(activo) || lanzando !== null} style={{ padding: "8px 10px", minWidth: 260 }}>
                      {convocatorias.map((convocatoria) => <option key={convocatoria.id} value={convocatoria.id}>{convocatoria.codigo} · {convocatoria.puesto}</option>)}
                    </select>
                    <select value={tipoJuridica} onChange={(event) => {
                      const valor = event.target.value as "TEORICA" | "PRACTICA";
                      setTipoJuridica(valor);
                      if (valor === "PRACTICA" && ambitoJuridica === "MODELO_EXAMEN") setAmbitoJuridica("TEMA");
                    }} disabled={Boolean(activo) || lanzando !== null} style={{ padding: "8px 10px" }}>
                      <option value="TEORICA">TEÓRICA</option><option value="PRACTICA">PRÁCTICA</option>
                    </select>
                    <select value={ambitoJuridica} onChange={(event) => setAmbitoJuridica(event.target.value as "MODELO_EXAMEN" | "TEMA" | "TODOS_TEMAS")} disabled={Boolean(activo) || lanzando !== null} style={{ padding: "8px 10px" }}>
                      {tipoJuridica === "TEORICA" && <option value="MODELO_EXAMEN">Modelo de examen</option>}
                      <option value="TEMA">Tema concreto</option><option value="TODOS_TEMAS">Todos los temas</option>
                    </select>
                    {ambitoJuridica === "TEMA" && <input type="number" min={1} value={temaIdJuridica} onChange={(event) => setTemaIdJuridica(event.target.value)} aria-label="ID de tema" style={{ padding: "8px 10px", width: 110 }} />}
                    <input type="number" min={1} value={cantidadJuridica} onChange={(event) => setCantidadJuridica(event.target.value)} aria-label="Cantidad de preguntas" style={{ padding: "8px 10px", width: 110 }} />
                  </div>
                )}
                {"requiereBusquedaNorma" in operacion && operacion.requiereBusquedaNorma && (
                  <div style={{ marginTop: 12, display: "flex", gap: 8, flexWrap: "wrap" }}>
                    <select
                      value={modoBusquedaNorma}
                      onChange={(event) => setModoBusquedaNorma(event.target.value as "pregunta" | "lote")}
                      disabled={Boolean(activo) || lanzando !== null}
                      style={{ padding: "8px 10px" }}
                    >
                      <option value="lote">Lote de PENDIENTES</option>
                      <option value="pregunta">Pregunta concreta</option>
                    </select>
                    <input
                      type="number"
                      min={1}
                      value={modoBusquedaNorma === "pregunta" ? preguntaId : limiteBusqueda}
                      onChange={(event) => modoBusquedaNorma === "pregunta" ? setPreguntaId(event.target.value) : setLimiteBusqueda(event.target.value)}
                      disabled={Boolean(activo) || lanzando !== null}
                      aria-label={modoBusquedaNorma === "pregunta" ? "ID de pregunta" : "Límite"}
                      style={{ padding: "8px 10px", width: 130 }}
                    />
                  </div>
                )}
                {"requiereConvocatoria" in operacion && operacion.requiereConvocatoria && (
                  <select
                    value={convocatoriaId ?? ""}
                    onChange={(event) => setConvocatoriaId(Number(event.target.value))}
                    disabled={Boolean(activo) || lanzando !== null || (("requiereConvocatoria" in operacion && operacion.requiereConvocatoria) && convocatoriaId === null)}
                    style={{ marginTop: 12, padding: "8px 10px", minWidth: 320 }}
                  >
                    {convocatorias.map((convocatoria) => (
                      <option key={convocatoria.id} value={convocatoria.id}>
                        {convocatoria.codigo} · {convocatoria.puesto}
                      </option>
                    ))}
                  </select>
                )}
              </div>
              <button
                type="button"
                disabled={
                  Boolean(activo) ||
                  lanzando !== null ||
                  ("requiereGeneracionJuridica" in operacion && operacion.requiereGeneracionJuridica &&
                    (convocatoriaId === null || !/^\d+$/.test(cantidadJuridica) || Number(cantidadJuridica) <= 0 ||
                      (ambitoJuridica === "TEMA" && (!/^\d+$/.test(temaIdJuridica) || Number(temaIdJuridica) <= 0)))) ||
                  ("requiereBusquedaNorma" in operacion && operacion.requiereBusquedaNorma &&
                    (modoBusquedaNorma === "pregunta"
                      ? !/^\d+$/.test(preguntaId) || Number(preguntaId) <= 0
                      : !/^\d+$/.test(limiteBusqueda) || Number(limiteBusqueda) <= 0))
                }
                onClick={() => void lanzar(
                  operacion.tipo,
                  "requiereConvocatoria" in operacion && operacion.requiereConvocatoria,
                  "requiereBusquedaNorma" in operacion && operacion.requiereBusquedaNorma,
                  "requiereGeneracionJuridica" in operacion && operacion.requiereGeneracionJuridica,
                )}
                style={{ padding: "10px 16px", fontWeight: 700, cursor: activo || lanzando ? "not-allowed" : "pointer" }}
              >
                {lanzando === operacion.tipo
                  ? "Creando…"
                  : activo
                    ? "Hay un trabajo activo"
                    : operacion.boton}
              </button>
            </div>
          </article>
          ))}
          </section>
        ))}
        <p style={{ margin: "0 0 0", fontSize: 13, color: "#666" }}>
          Todas las operaciones requieren que TuCoach Agent esté ejecutándose en el portátil.
          Solo puede existir un trabajo administrativo activo a la vez.
        </p>
      </section>

      {error && (
        <p role="alert" style={{ marginTop: 16, padding: 12, border: "1px solid #b42318", borderRadius: 8 }}>
          {error}
        </p>
      )}

      <section style={{ marginTop: 28 }}>
        <h2 style={{ fontSize: 20 }}>Trabajos recientes</h2>
        {cargando ? (
          <p>Cargando…</p>
        ) : jobs.length === 0 ? (
          <p>No hay trabajos registrados.</p>
        ) : (
          <div style={{ display: "grid", gap: 10 }}>
            {jobs.map((job) => (
              <article key={job.id} style={{ border: "1px solid #ddd", borderRadius: 10, padding: 14, background: "#fff" }}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
                  <strong>{job.tipo}</strong>
                  <span>{job.estado}</span>
                </div>
                <div style={{ marginTop: 6, fontSize: 12, color: "#666", wordBreak: "break-all" }}>{job.id}</div>
                {job.error_texto && <p style={{ marginBottom: 0 }}>Error: {job.error_texto}</p>}
                {job.resultado?.returncode !== undefined && (
                  <p style={{ marginBottom: 0 }}>Código de salida: {job.resultado.returncode}</p>
                )}
                {job.estado === "ESPERANDO_CONFIRMACION" && (
                  <div style={{ marginTop: 12, display: "flex", gap: 10, flexWrap: "wrap" }}>
                    <button type="button" disabled={accionJob !== null} onClick={() => void resolverConfirmacion(job.id, "confirmar")} style={{ padding: "9px 14px", fontWeight: 700 }}>
                      {accionJob === `${job.id}:confirmar` ? "Confirmando…" : "Confirmar continuación"}
                    </button>
                    <button type="button" disabled={accionJob !== null} onClick={() => void resolverConfirmacion(job.id, "cancelar")} style={{ padding: "9px 14px" }}>
                      {accionJob === `${job.id}:cancelar` ? "Cancelando…" : "Cancelar"}
                    </button>
                    <span style={{ alignSelf: "center", fontSize: 12, color: "#666" }}>
                      Confirmar autoriza la siguiente fase definida por el Agent; en operaciones APPLY puede modificar datos.
                    </span>
                  </div>
                )}
                {job.resultado?.salida && (
                  <details style={{ marginTop: 10 }}>
                    <summary style={{ cursor: "pointer", fontWeight: 600 }}>Ver salida</summary>
                    <pre style={{ margin: "10px 0 0", padding: 12, overflowX: "auto", whiteSpace: "pre-wrap", wordBreak: "break-word", background: "#f6f6f6", borderRadius: 8, fontSize: 12 }}>
                      {job.resultado.salida}
                    </pre>
                  </details>
                )}
              </article>
            ))}
          </div>
        )}
      </section>

      <p style={{ marginTop: 28 }}>
        <Link href="/admin" style={{ color: "inherit" }}>Volver al centro de administración</Link>
      </p>
    </main>
  );
}
