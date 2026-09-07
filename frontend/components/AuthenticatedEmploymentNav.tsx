"use client";

import { useEffect, useMemo } from "react";
import { usePathname } from "next/navigation";
import { createClient } from "@/lib/supabase/client";

const ID = "authenticated-employment-nav";

export default function AuthenticatedEmploymentNav() {
  const pathname = usePathname();
  const supabase = useMemo(() => createClient(), []);

  useEffect(() => {
    if (pathname !== "/") return;

    let activo = true;

    async function sincronizar() {
      const { data } = await supabase.auth.getSession();
      if (!activo) return;
      actualizar(Boolean(data.session));
    }

    function actualizar(autenticado: boolean) {
      const nav = document.querySelector(".app-nav");
      if (!nav) return;

      const existente = document.getElementById(ID);
      if (!autenticado) {
        existente?.remove();
        return;
      }

      if (existente) return;

      const enlace = document.createElement("a");
      enlace.id = ID;
      enlace.className = "nav-link employment-nav-link";
      enlace.href = "/empleo";
      enlace.textContent = "Empleo público";
      enlace.setAttribute("aria-label", "Ir a Empleo público");
      nav.appendChild(enlace);
    }

    void sincronizar();

    const { data: listener } = supabase.auth.onAuthStateChange((_event, session) => {
      if (!activo) return;
      window.requestAnimationFrame(() => actualizar(Boolean(session)));
    });

    const observer = new MutationObserver(() => {
      void sincronizar();
    });
    observer.observe(document.body, { childList: true, subtree: true });

    return () => {
      activo = false;
      observer.disconnect();
      listener.subscription.unsubscribe();
      document.getElementById(ID)?.remove();
    };
  }, [pathname, supabase]);

  return (
    <style>{`
      .brand-mark {
        position: relative !important;
        display: grid !important;
        place-items: center !important;
      }
      .brand-mark::after {
        position: absolute !important;
        inset: 0 !important;
        display: grid !important;
        place-items: center !important;
        margin: 0 !important;
        width: auto !important;
        height: auto !important;
        transform: none !important;
      }
    `}</style>
  );
}
