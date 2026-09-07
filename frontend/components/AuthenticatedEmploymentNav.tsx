"use client";

import { useEffect, useMemo } from "react";
import { usePathname } from "next/navigation";
import { createClient } from "@/lib/supabase/client";

const ID = "authenticated-employment-nav";

export default function AuthenticatedEmploymentNav() {
  const pathname = usePathname();
  const supabase = useMemo(() => createClient(), []);

  useEffect(() => {
    if (pathname !== "/" && pathname !== "/empleo") return;

    let activo = true;

    async function sincronizar() {
      const { data } = await supabase.auth.getSession();
      if (!activo) return;
      actualizar(Boolean(data.session));
    }

    function actualizar(autenticado: boolean) {
      const nav = pathname === "/empleo"
        ? document.querySelector("main[style*='1280px'] header .headerActions")
        : document.querySelector(".app-nav");
      if (!nav) return;

      const existente = document.getElementById(ID);
      if (!autenticado) {
        existente?.remove();
        return;
      }
      if (existente) return;

      if (pathname === "/empleo") {
        const wrapper = document.createElement("nav");
        wrapper.id = ID;
        wrapper.className = "employment-app-nav";
        wrapper.setAttribute("aria-label", "Navegación de Tu Coach");
        [
          ["Inicio", "/"],
          ["Simulacros", "/simulacros"],
          ["Tests", "/tests"],
          ["Chat", "/chat"],
          ["Materiales", "/materiales"],
        ].forEach(([texto, href]) => {
          const enlace = document.createElement("a");
          enlace.href = href;
          enlace.textContent = texto;
          wrapper.appendChild(enlace);
        });
        const empleo = document.createElement("a");
        empleo.href = "/empleo";
        empleo.textContent = "Empleo público";
        empleo.setAttribute("aria-current", "page");
        empleo.className = "employment-current";
        wrapper.appendChild(empleo);
        nav.prepend(wrapper);
      } else {
        const enlace = document.createElement("a");
        enlace.id = ID;
        enlace.className = "nav-link employment-nav-link";
        enlace.href = "/empleo";
        enlace.textContent = "Empleo público";
        enlace.setAttribute("aria-label", "Ir a Empleo público");
        nav.appendChild(enlace);
      }
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

      main[style*="1280px"] {
        max-width: 1240px !important;
        padding: 0 0 56px !important;
        font-family: inherit !important;
      }
      main[style*="1280px"] > header {
        min-height: 90px;
        margin: 0 0 28px !important;
        padding: 16px 22px !important;
        align-items: center !important;
        border: 1px solid #dce3ef;
        border-radius: 18px;
        background: #fff;
        box-shadow: 0 8px 26px rgba(31,55,94,.06);
      }
      main[style*="1280px"] > header > div:first-child > .kicker {
        display: none !important;
      }
      main[style*="1280px"] > header > div:first-child > .title,
      main[style*="1280px"] > header > div:first-child > h1 {
        font-size: 30px !important;
        letter-spacing: -.02em;
        margin: 0 !important;
      }
      main[style*="1280px"] > header > div:first-child > .title::before,
      main[style*="1280px"] > header > div:first-child > h1::before {
        content: "Tu Coach · ";
        color: #1557c0;
      }
      main[style*="1280px"] > header .subtitle {
        margin-top: 5px !important;
        color: #68768a !important;
      }
      main[style*="1280px"] > header .headerActions > a:not(.employment-current) {
        display: none !important;
      }
      .employment-app-nav {
        display: flex;
        align-items: center;
        gap: 4px;
        margin-right: 10px;
      }
      .employment-app-nav a {
        display: inline-flex;
        align-items: center;
        min-height: 38px;
        padding: 8px 11px;
        border-radius: 10px;
        color: #53627a;
        text-decoration: none;
        font-weight: 700;
        font-size: .92rem;
      }
      .employment-app-nav a:hover { background: #edf3ff; color: #1557c0; }
      .employment-app-nav .employment-current {
        background: #e8f1ff;
        color: #1557c0;
      }
      main[style*="1280px"] > .grid,
      main[style*="1280px"] > section.grid {
        gap: 18px !important;
      }
      main[style*="1280px"] .panel {
        border-color: #dce3ef !important;
        border-radius: 18px !important;
        box-shadow: 0 8px 26px rgba(31,55,94,.04);
      }
      main[style*="1280px"] .activeItem {
        background: #e8f1ff !important;
        color: #1557c0 !important;
      }
      main[style*="1280px"] .primary,
      main[style*="1280px"] .follow {
        border-radius: 10px !important;
        background: #172033 !important;
      }
      main[style*="1280px"] .card {
        border-color: #dce3ef !important;
        border-radius: 14px !important;
      }
      main[style*="1280px"] .cardTitle {
        letter-spacing: -.01em;
      }

      @media (max-width: 1050px) {
        .employment-app-nav a:nth-child(n+4) { display: none; }
      }
      @media (max-width: 760px) {
        main[style*="1280px"] > header { align-items: flex-start !important; flex-direction: column; }
        .employment-app-nav { flex-wrap: wrap; margin: 8px 0 0; }
        main[style*="1280px"] .grid { grid-template-columns: 1fr !important; }
      }
    `}</style>
  );
}
