"use client";

import Link from "next/link";

const modulos = [
  {
    titulo: "Empleo público",
    descripcion: "Revisión y gestión de convocatorias, publicaciones y temarios de Empleo.",
    href: "/admin/empleo",
    estado: "DISPONIBLE",
  },
  {
    titulo: "Mantenimiento",
    descripcion: "Validaciones, bancos de preguntas, temarios y publicación de contenidos.",
    href: null,
    estado: "PRÓXIMO",
  },
  {
    titulo: "Trabajos y agente local",
    descripcion: "Ejecución controlada de procesos de mantenimiento en el equipo local.",
    href: null,
    estado: "PRÓXIMO",
  },
] as const;

export default function AdminPage() {
  return (
    <main style={{ maxWidth: 1040, margin: "0 auto", padding: "40px 20px 64px" }}>
      <header style={{ marginBottom: 32 }}>
        <p style={{ margin: 0, fontSize: 13, fontWeight: 700, letterSpacing: "0.08em" }}>
          TU COACH · ADMINISTRACIÓN
        </p>
        <h1 style={{ margin: "8px 0 10px" }}>Centro de administración</h1>
        <p style={{ margin: 0, maxWidth: 720, color: "#555", lineHeight: 1.55 }}>
          Acceso central a las herramientas internas de Tu Coach. Las operaciones de
          mantenimiento se incorporarán progresivamente con revisión y confirmación
          antes de cualquier modificación de datos.
        </p>
      </header>

      <section
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
          gap: 16,
        }}
      >
        {modulos.map((modulo) => {
          const contenido = (
            <article
              style={{
                height: "100%",
                boxSizing: "border-box",
                border: "1px solid #d9d9d9",
                borderRadius: 12,
                padding: 20,
                background: "#fff",
              }}
            >
              <div
                style={{
                  display: "inline-block",
                  marginBottom: 12,
                  padding: "4px 8px",
                  borderRadius: 999,
                  background: modulo.href ? "#eef7ee" : "#f3f3f3",
                  fontSize: 11,
                  fontWeight: 700,
                }}
              >
                {modulo.estado}
              </div>
              <h2 style={{ margin: "0 0 8px", fontSize: 20 }}>{modulo.titulo}</h2>
              <p style={{ margin: 0, color: "#555", lineHeight: 1.5 }}>
                {modulo.descripcion}
              </p>
            </article>
          );

          return modulo.href ? (
            <Link
              key={modulo.titulo}
              href={modulo.href}
              style={{ color: "inherit", textDecoration: "none" }}
            >
              {contenido}
            </Link>
          ) : (
            <div key={modulo.titulo} aria-disabled="true">
              {contenido}
            </div>
          );
        })}
      </section>

      <p style={{ marginTop: 28 }}>
        <Link href="/" style={{ color: "inherit" }}>Volver a Tu Coach</Link>
      </p>
    </main>
  );
}
