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

export default function MantenimientoPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [cargando, setCargando] = useState(true);
  const [lanzando, setLanzando] = useState(false);
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

  async function lanzarValidacion() {
    setLanzando(true);
    setError(null);
    try {
      await apiFetch<Job>("/api/v1/admin/jobs", {
        method: "POST",
        body: JSON.stringify({ tipo: "VALIDACION_COMPLETA", parametros: {} }),
      });
      await cargar();
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "No se pudo crear el trabajo.");
    } finally {
      setLanzando(false);
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
          La primera operación disponible es estrictamente de solo lectura sobre la base de datos.
        </p>
      </header>

      <section style={{ border: "1px solid #d9d9d9", borderRadius: 12, padding: 20, background: "#fff" }}>
        <div style={{ display: "flex", gap: 12, alignItems: "center", justifyContent: "space-between", flexWrap: "wrap" }}>
          <div>
            <div style={{ fontSize: 11, fontWeight: 700, marginBottom: 6 }}>SOLO LECTURA</div>
            <h2 style={{ margin: "0 0 6px", fontSize: 20 }}>Validación completa</h2>
            <p style={{ margin: 0, color: "#555" }}>
              Comprueba integridad, bancos, duplicados, referencias jurídicas, modelos y auditorías sin guardar cambios en la base.
            </p>
          </div>
          <button
            type="button"
            disabled={Boolean(activo) || lanzando}
            onClick={() => void lanzarValidacion()}
            style={{ padding: "10px 16px", fontWeight: 700, cursor: activo || lanzando ? "not-allowed" : "pointer" }}
          >
            {lanzando ? "Creando…" : activo ? "Hay un trabajo activo" : "Ejecutar validación"}
          </button>
        </div>
        <p style={{ margin: "14px 0 0", fontSize: 13, color: "#666" }}>
          Requiere que TuCoach Agent esté ejecutándose en el portátil.
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
