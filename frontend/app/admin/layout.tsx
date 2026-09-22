"use client";

import { useEffect, useState } from "react";
import type { ReactNode } from "react";

import { apiFetch } from "@/lib/api";

type AdminMe = {
  id: string;
  email: string;
  admin: boolean;
};

type Estado = "COMPROBANDO" | "AUTORIZADO" | "DENEGADO";

export default function AdminLayout({ children }: { children: ReactNode }) {
  const [estado, setEstado] = useState<Estado>("COMPROBANDO");

  useEffect(() => {
    let activo = true;

    async function comprobar() {
      try {
        const admin = await apiFetch<AdminMe>("/api/v1/admin/me");
        if (activo) setEstado(admin.admin ? "AUTORIZADO" : "DENEGADO");
      } catch {
        if (activo) setEstado("DENEGADO");
      }
    }

    void comprobar();
    return () => {
      activo = false;
    };
  }, []);

  if (estado === "COMPROBANDO") {
    return (
      <main style={{ maxWidth: 960, margin: "0 auto", padding: "48px 20px" }}>
        <p>Comprobando autorización administrativa…</p>
      </main>
    );
  }

  if (estado === "DENEGADO") {
    return (
      <main style={{ maxWidth: 960, margin: "0 auto", padding: "48px 20px" }}>
        <h1>Acceso restringido</h1>
        <p>Esta zona requiere autorización administrativa de Tu Coach.</p>
        <a href="/">Volver a Tu Coach</a>
      </main>
    );
  }

  return <>{children}</>;
}
