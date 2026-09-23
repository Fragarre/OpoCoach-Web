"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { apiFetch } from "@/lib/api";

type Job = {
  id: string;
  tipo: string;
  estado: string;
  creado_at: string;
  iniciado_at?: string | null;
  finalizado_at?: string | null;
  resultado?: { returncode?: number; salida?: string } | null;
  error_texto?: string | null;
};

const ACTIVOS = new Set(["PENDIENTE", "RECOGIDO", "EJECUTANDO", "ESPERANDO_CONFIRMACION"]);

const OPERACIONES = [
  {
    tipo: "VALIDACION_COMPLETA",
    titulo: "Validación completa",
    descripcion: "Comprueba integridad, bancos, duplicados, referencias jurídicas, modelos y auditorías sin guardar cambios en la base.",
    boton: "Ejecutar validación",
  },
  {
    tipo: "AUDITORIA_BD",
    titulo: "Auditoría general de la BD",
    descripcion: "Comprueba estructura, integridad, distribución, problemas objetivos y duplicados de la base maestra.",
    boton: "Ejecutar auditoría",
  },
  {
    tipo: "AUDITORIA_BANCOS_SELECCION",
    titulo: "Auditoría de selección de bancos",
    descripcion: "Reconstruye virtualmente la selección de los bancos activos y la compara con las preguntas almacenadas.",
    boton: "Auditar bancos",
  },
  {
    tipo: "AUDITORIA_ESTRUCTURA_BANCO",
    titulo: "Estructura del banco",
    descripcion: "Inspecciona tablas, columnas, índices y claves foráneas relacionadas con los bancos.",
    boton: "Auditar estructura",
  },
  {
    tipo: "AUDITORIA_MATERIALES_ESTUDIO",
    titulo: "Materiales de estudio",
    descripcion: "Contrasta los materiales preparados con las normas activas y la huella actual del corpus normativo.",
    boton: "Auditar materiales",
  },
  {
    tipo: "AUDITORIA_CORPUS_TEMARIO",
    titulo: "Auditoría del temario/corpus",
    descripcion: "Comprueba referencias jurídicas y artículos fuente del temario y genera un informe diagnóstico en el repositorio local.",
    boton: "Auditar corpus",
    generaInforme: true,
  },
  {
    tipo: "AUDITORIA_ESQUEMA_OBSOLETO",
    titulo: "Posibles objetos obsoletos",
    descripcion: "Inventaría tablas, columnas y referencias de código para diagnosticar deuda técnica. No elimina objetos.",
    boton: "Auditar esquema",
    generaInforme: true,
  },
  {
    tipo: "INVENTARIO_DENOMINACIONES_NORMAS",
    titulo: "Denominaciones de normas",
    descripcion: "Genera el inventario de denominaciones jurídicas presentes en lote_preguntas para diagnosticar la normalización.",
    boton: "Generar inventario",
    generaInforme: true,
  },
] as const;

export default function MantenimientoPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [cargando, setCargando] = useState(true);
  const [lanzando, setLanzando] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

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
    const timer = window.setInterval(() => void cargar(), 5000);
    return () => window.clearInterval(timer);
  }, []);

  const activo = useMemo(() => jobs.find((job) => ACTIVOS.has(job.estado)), [jobs]);

  async function lanzar(tipo: string) {
    setLanzando(tipo);
    setError(null);
    try {
      await apiFetch<Job>("/api/v1/admin/jobs", {
        method: "POST",
        body: JSON.stringify({ tipo, parametros: {} }),
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
          Las operaciones disponibles en esta fase no modifican la base de datos.
        </p>
      </header>

      <section style={{ display: "grid", gap: 14 }}>
        {OPERACIONES.map((operacion) => (
          <article
            key={operacion.tipo}
            style={{ border: "1px solid #d9d9d9", borderRadius: 12, padding: 20, background: "#fff" }}
          >
            <div style={{ display: "flex", gap: 12, alignItems: "center", justifyContent: "space-between", flexWrap: "wrap" }}>
              <div style={{ flex: "1 1 620px" }}>
                <div style={{ fontSize: 11, fontWeight: 700, marginBottom: 6 }}>\n                  NO MODIFICA BD{("generaInforme" in operacion && operacion.generaInforme) ? " · GENERA INFORME LOCAL" : ""}\n                </div>
                <h2 style={{ margin: "0 0 6px", fontSize: 20 }}>{operacion.titulo}</h2>
                <p style={{ margin: 0, color: "#555" }}>{operacion.descripcion}</p>
              </div>
              <button
                type="button"
                disabled={Boolean(activo) || lanzando !== null}
                onClick={() => void lanzar(operacion.tipo)}
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
