import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import EmploymentNovedadesAviso from "@/components/EmploymentNovedadesAviso";

export const metadata: Metadata = {
  title: "Tu Coach | Oposiciones para la Administración Pública de la Comunidad Valenciana",
  description:
    "Tu Coach: simulacros, tests, análisis, materiales y seguimiento de oportunidades para preparar oposiciones para la Administración Pública de la Comunidad Valenciana.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es">
      <body>
        <style>{`
          /* Transición visual de marca: mantenemos rutas y dominio técnico actuales. */
          .brand-name { font-size: 0 !important; }
          .brand-name::after { content: "Tu Coach"; font-size: 1.18rem; }
          .brand-mark { font-size: 0 !important; }
          .brand-mark::after {
            content: "TC";
            display: block;
            font-size: .72rem;
            line-height: 1;
            font-weight: 900;
            letter-spacing: -.02em;
          }
          .brand-byline { display: none !important; }

          /* El acceso a Empleo deja de competir con la navegación principal. */
          .employment-entry {
            width: min(1240px, calc(100% - 40px));
            margin: 14px auto 0;
            padding: 0;
          }
          .employment-entry-inner {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 24px;
            padding: 13px 18px;
            border: 1px solid #c9daf3;
            border-radius: 14px;
            background: linear-gradient(100deg, #eef5ff, #f8fbff);
            box-shadow: 0 8px 22px rgba(31, 55, 94, .06);
          }
          .employment-entry-copy { display: grid; gap: 3px; }
          .employment-entry-copy strong { color: #0d397f; font-size: .98rem; }
          .employment-entry-copy span { color: #5a6980; font-size: .88rem; }
          .employment-entry a {
            flex: 0 0 auto;
            display: inline-flex;
            align-items: center;
            min-height: 40px;
            padding: 8px 14px;
            border-radius: 9px;
            background: #1557c0;
            color: #fff;
            font-size: .88rem;
            font-weight: 800;
            text-decoration: none;
          }
          .employment-entry a:hover { background: #0d459f; }

          /* El quinto paso del recorrido explica Empleo; Materiales sigue teniendo su sección propia. */
          .public-process #materiales-proceso {
            border-color: #bcd1ee;
            background: linear-gradient(145deg, #f4f8ff, #ffffff);
          }
          .public-process #materiales-proceso .process-number { display: none; }
          .public-process #materiales-proceso .process-content { display: none; }
          .public-process #materiales-proceso::before {
            content: "05";
            display: grid;
            place-items: center;
            width: 50px;
            height: 50px;
            margin-bottom: 24px;
            border-radius: 14px;
            background: #e5efff;
            color: #1557c0;
            font-weight: 900;
          }
          .public-process #materiales-proceso::after {
            content: "DESCUBRE\\A\\AEncuentra oportunidades de empleo público que encajan contigo. Sigue las convocatorias y sus novedades oficiales desde un mismo lugar.";
            white-space: pre-wrap;
            display: block;
            color: #17315f;
            font-size: .98rem;
            line-height: 1.55;
            font-weight: 700;
          }

          /* La propuesta de Empleo también gana peso dentro del hero. */
          .public-value-panel::after {
            content: "DESCUBRE OPORTUNIDADES DE EMPLEO PÚBLICO\\A\\AExplora convocatorias y sigue sus novedades oficiales.\\A\\AVer oportunidades →";
            white-space: pre-wrap;
            display: block;
            margin-top: 6px;
            padding: 17px 18px;
            border: 1px solid #bcd1ee;
            border-radius: 14px;
            background: #eef5ff;
            color: #1557c0;
            font-size: .9rem;
            line-height: 1.45;
            font-weight: 800;
          }

          /* Sustitución visual de referencias al nombre anterior en la landing. */
          .public-hero-copy > p {
            font-size: 0 !important;
          }
          .public-hero-copy > p::after {
            content: "Tu Coach combina simulacros, tests dirigidos y análisis de tus respuestas para que practiques con criterio y detectes dónde necesitas reforzar.";
            font-size: 1.12rem;
          }
          .public-proof-heading p {
            font-size: 0 !important;
          }
          .public-proof-heading p::after {
            content: "Tu Coach acompaña todo el ciclo de entrenamiento: eliges qué practicar, respondes, corriges y utilizas lo aprendido para decidir dónde concentrar el siguiente esfuerzo.";
            font-size: 1rem;
          }
          .public-footer strong { font-size: 0 !important; }
          .public-footer strong::after { content: "Tu Coach"; font-size: inherit; }

          @media (max-width: 700px) {
            .employment-entry { width: min(100% - 20px, 1240px); }
            .employment-entry-inner { align-items: flex-start; flex-direction: column; gap: 10px; }
            .employment-entry a { width: 100%; justify-content: center; }
          }
        `}</style>

        <div className="employment-entry">
          <div className="employment-entry-inner">
            <div className="employment-entry-copy">
              <strong>Empleo público: descubre oportunidades y sigue sus novedades oficiales</strong>
              <span>Una parte diferencial de Tu Coach: de la convocatoria a tu preparación, sin perder de vista los cambios.</span>
            </div>
            <Link href="/empleo">Descubrir oportunidades →</Link>
          </div>
        </div>

        <EmploymentNovedadesAviso />
        {children}
      </body>
    </html>
  );
}
