"use client";

import type { ReactNode } from "react";
import { usePathname } from "next/navigation";
import NovedadesAviso from "./NovedadesAviso";

export default function EmpleoLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const enSeguimiento = pathname.startsWith("/empleo/seguimiento");
  const enDetalle = pathname.startsWith("/empleo/proceso/");

  return (
    <div className="employment-app">
      <nav className="employment-chrome" aria-label="Navegación de Empleo">
        <a href="/" className="employment-chrome-home">Tu Coach</a>
        <a
          href="/empleo"
          className={!enSeguimiento && !enDetalle ? "employment-chrome-current" : undefined}
          aria-current={!enSeguimiento && !enDetalle ? "page" : undefined}
        >
          Empleo público
        </a>
        <a
          href="/empleo/seguimiento"
          className={enSeguimiento ? "employment-chrome-current" : undefined}
          aria-current={enSeguimiento ? "page" : undefined}
        >
          Mi seguimiento
        </a>
      </nav>
      <NovedadesAviso />
      {children}
    </div>
  );
}
