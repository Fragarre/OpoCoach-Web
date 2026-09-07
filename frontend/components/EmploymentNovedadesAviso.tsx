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

type EstadoNovedades = {
  ultima_novedad_vista_at: string | null;
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
    if (pathname !== "/") {
      setVisible(false);
      return;
    }

    let cancelado = false;

    async function comprobar(accessToken: string) {
      try {
        const [cambiosResponse, estadoResponse] = await Promise.all([
          fetch("/api/empleo/seguimiento/cambios?limite=100", {
            cache: "no-store",
            headers: { Authorization: `Bearer ${accessToken}` },
          }),
          fetch("/api/empleo/seguimiento/estado", {
            cache: "no-store",
            headers: { Authorization: `Bearer ${accessToken}` },
          }),
        ]);

        if (!cambiosResponse.ok || !estadoResponse.ok || cancelado) return;

        const novedades = (await cambiosResponse.json()) as Novedad[];
        const estado = (await estadoResponse.json()) as EstadoNovedades;
        const vista = estado.ultima_novedad_vista_at;
        const utiles = novedades
          .filter((n) =>
            n.novedad_tipo === "PUBLICACION" ? esPublicacionUtil(n) : esCambioUtil(n)
          )
          .filter((n) => {
            if (!vista || !n.detectado_at) return true;
            return new Date(n.detectado_at).getTime() > new Date(vista).getTime();
          });

        if (!utiles.length || cancelado) {
          setVisible(false);
          setCount(0);
          setLatestAt(null);
          return;
        }

        const ultimo = utiles.reduce<string | null>((actual, item) => {
          if (!item.detectado_at) return actual;
          if (!actual) return item.detectado_at;
          return item.detectado_at > actual ? item.detectado_at : actual;
        }, null);

        setCount(utiles.length);
        setLatestAt(ultimo);
        setVisible(true);
      } catch {
        // El aviso nunca debe interferir con la carga normal de NetReto.
      }
    }

    async function iniciar() {
      const { data } = await supabase.auth.getSession();
      if (data.session && !cancelado) {
        void comprobar(data.session.access_token);
      }

      const {
        data: { subscription },
      } = supabase.auth.onAuthStateChange((event, session) => {
        if (event === "SIGNED_IN" && session) {
          void comprobar(session.access_token);
        }
        if (event === "SIGNED_OUT") {
          setVisible(false);
          setCount(0);
          setLatestAt(null);
        }
      });

      return () => subscription.unsubscribe();
    }

    let cleanup: (() => void) | undefined;
    void iniciar().then((fn) => {
      cleanup = fn;
    });

    return () => {
      cancelado = true;
      cleanup?.();
    };
  }, [pathname, supabase]);

  if (!visible || pathname !== "/") return null;

  async function marcarVistas() {
    if (!latestAt) {
      setVisible(false);
      return;
    }

    try {
      const { data } = await supabase.auth.getSession();
      if (data.session) {
        const params = new URLSearchParams({ hasta: latestAt });
        await fetch(`/api/empleo/seguimiento/estado/visto?${params.toString()}`, {
          method: "POST",
          cache: "no-store",
          headers: { Authorization: `Bearer ${data.session.access_token}` },
        });
      }
    } finally {
      setVisible(false);
    }
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
