import type { ReactNode } from "react";
import NovedadesAviso from "./NovedadesAviso";

export default function EmpleoLayout({ children }: { children: ReactNode }) {
  return (
    <div className="employment-app">
      <nav className="employment-chrome" aria-label="Navegación de Empleo">
        <a href="/" className="employment-chrome-home">Tu Coach</a>
        <a href="/empleo" className="employment-chrome-current">Empleo público</a>
        <a href="/empleo/seguimiento">Mi seguimiento</a>
      </nav>
      <NovedadesAviso />
      {children}
    </div>
  );
}
