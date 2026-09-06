"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { createClient } from "@/lib/supabase/client";

type Novedad = {
  id: number;
  novedad_tipo: "PUBLICACION" | "CAMBIO";
  tipo: string | null;
  campo: string | null;
  resumen: string | null;
  detectado_at: string | null;
};

const CAMPOS_RELEVANTES = new Set([
  "fecha_apertura",
  "fecha_cierre",
  "fecha_examen",
  "estado",
  "plazas",
  "turno",
  "etapa_actual",
  "tipo_proceso",
  "url_oficial",
]);

const TIPOS_PUBLICACION = [
  "convocatoria",
  "bases",
  "admitidos",
  "excluidos",
  "tribunal",
  "fecha",
  "lugar",
  "examen",
  "modificacion",
  "modificación",
  "resultado",
  "calificacion",
  "calificación",
  "nombramiento",
  "adjudicacion",
  "adjudicación",
  "lista",
];

function esPublicacionUtil(n: Novedad): boolean {
  const texto = `${n.tipo || ""} ${n.resumen || ""}`.toLowerCase().trim();
  if (!texto) return false;
  if (/\bnavegaci[oó]n\b/.test(texto) && texto.length <= 80) return false;
  return TIPOS_PUBLICACION.some((x) => texto.includes(x));
}

function esCambioUtil(n: Novedad): boolean {
  if (n.novedad_tipo !== "CAMBIO") return false;
  const campo = (n.campo || "").toLowerCase();
  if (CAMPOS_RELEVANTES.has(campo)) return true;
  const texto = `${n.tipo || ""} ${n.resumen || ""}`.toLowerCase();
  return /(plazo|fecha de examen|fecha examen|lugar de examen|n[uú]mero de plazas|turno|etapa|estado del proceso|tribunal)/i.test(texto);
}

export default function EmploymentNovedadesAviso() {
  const pathname = usePathname();
  const supabase = useMemo(() => createClient(), []);
  const [visible, setVisible] = useState(false);
  const [count, setCount] = useState(0);
  const [latestAt, setLatestAt] = useState<string | null>(null);

  useEffect(() => {
    // El aviso se muestra al entrar en la aplicación principal, no dentro del módulo Empleo.
    if (pathname !== "/") {
      setVisible(false);
      return;
    }

    let cancelado = false;

    async function comprobar() {
      const { data, error } = await supabase.auth.getSession();
      if (error || !data.session || cancelado) return;

      try {
        const response = await fetch("/api/empleo/seguimiento/cambios?limite=100", {
          cache: "no-store",
          headers: { Authorization: `Bearer ${data.session.access_token}` },
        });
        if (!response.ok) return;

        const novedades = (await response.json()) as Novedad[];
        const utiles = novedades.filter((n) =>
          n.novedad_tipo === "PUBLICACION" ? esPublicacionUtil(n) : esCambioUtil(n)
        );
        if (!utiles.length || cancelado) return;

        const ultimo = utiles.reduce<string | null>((actual, item) => {
          if (!item.detectado_at) return actual;
          if (!actual) return item.detectado_at;
          return item.detectado_at > actual ? item.detectado_at : actual;
        }, null);

        const key = `netreto:empleo:ultima-novedad-vista:${data.session.user.id}`;
        const vista = window.localStorage.getItem(key);

        if (!ultimo || !vista || ultimo > vista) {
          setCount(utiles.length);
          setLatestAt(ultimo);
          setVisible(true);
        }
      } catch {
        // El aviso nunca debe interferir con la carga normal de NetReto.
      }
    }

    void comprobar();
    return () => {
      cancelado = true;
    };
  }, [pathname, supabase]);

  if (!visible || pathname !== "/") return null;

  function marcarVistas() {
    void supabase.auth.getSession().then(({ data }) => {
      if (data.session && latestAt) {
        window.localStorage.setItem(
          `netreto:empleo:ultima-novedad-vista:${data.session.user.id}`,
          latestAt
        );
      }
      setVisible(false);
    });
  }

  function cerrarAviso() {
    setVisible(false);
  }

  return (
    <div
      role="status"
      style={{
        margin: "14px auto 0",
        maxWidth: 1100,
        padding: "0 20px",
        fontFamily: "system-ui, sans-serif",
      }}
    >
      <div
        style={{
          border: "1px solid #cfd6e2",
          borderRadius: 12,
          background: "#f7f9fc",
          padding: "12px 16px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: 16,
        }}
      >
        <div>
          <strong>
            {count === 1
              ? "Hay una novedad en las convocatorias que sigues."
              : `Hay ${count} novedades en las convocatorias que sigues.`}
          </strong>
          <div style={{ marginTop: 3, opacity: 0.72, fontSize: 13 }}>
            Revisa Mi seguimiento para consultar la información oficial.
          </div>
        </div>
        <div style={{ display: "flex", gap: 10, alignItems: "center", whiteSpace: "nowrap" }}>
          <Link href="/empleo/seguimiento" onClick={marcarVistas}>
            Revisar seguimiento
          </Link>
          <button
            type="button"
            onClick={cerrarAviso}
            style={{
              border: "1px solid #cfd6e2",
              background: "#fff",
              borderRadius: 8,
              padding: "7px 10px",
              cursor: "pointer",
            }}
          >
            Cerrar
          </button>
        </div>
      </div>
    </div>
  );
}
