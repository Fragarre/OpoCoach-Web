import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import EmploymentNovedadesAviso from "@/components/EmploymentNovedadesAviso";
import EmploymentPublicGate from "@/components/EmploymentPublicGate";
import AuthenticatedEmploymentNav from "@/components/AuthenticatedEmploymentNav";

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
          .brand-mark { font-size: 0 !important; display: grid !important; place-items: center !important; }
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
          body:not(:has(.public-site)) .employment-entry { display: none; }
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

          /* El quinto paso mantiene exactamente la estructura visual de los demás y presenta Empleo. */
          .public-process #materiales-proceso .process-content > * { display: none; }
          .public-process #materiales-proceso .process-content::before {
            content: "DESCUBRE";
            display: block;
            color: #5c6b80;
            font-size: 12px;
            letter-spacing: 1.4px;
            font-weight: 800;
            margin-bottom: 8px;
          }
          .public-process #materiales-proceso .process-content::after {
            content: "Encuentra oportunidades de empleo público que encajan contigo. Sigue las convocatorias y sus novedades oficiales desde un mismo lugar.";
            display: block;
            color: #17315f;
            font-size: 1rem;
            line-height: 1.55;
            font-weight: 700;
          }

          /* La propuesta de Empleo también gana peso dentro del hero. */
          .public-value-panel::after {
            content: "DESCUBRE OPORTUNIDADES DE EMPLEO PÚBLICO\\00000A\\00000AExplora convocatorias y sigue sus novedades oficiales.\\00000A\\00000AVer oportunidades →";
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
          .public-hero-copy > p { font-size: 0 !important; }
          .public-hero-copy > p::after {
            content: "Tu Coach combina simulacros, tests dirigidos y análisis de tus respuestas para que practiques con criterio y detectes dónde necesitas reforzar.";
            font-size: 1.12rem;
          }
          .public-proof-heading p { font-size: 0 !important; }
          .public-proof-heading p::after {
            content: "Tu Coach acompaña todo el ciclo de entrenamiento: eliges qué practicar, respondes, corriges y utilizas lo aprendido para decidir dónde concentrar el siguiente esfuerzo.";
            font-size: 1rem;
          }
          .public-highlight p { font-size: 0 !important; }
          .public-highlight p::after {
            content: "Tu Coach reúne contenido y herramientas para que puedas estudiar, consultar y analizar tu preparación dentro de tu convocatoria.";
            font-size: 1rem;
          }
          .public-pricing h2 { font-size: 0 !important; }
          .public-pricing h2::after {
            content: "Prueba Tu Coach antes de suscribirte";
            font-size: 2rem;
          }
          .pricing-name { font-size: 0 !important; }
          .pricing-name::after { content: "Tu Coach"; font-size: inherit; }
          .public-final-cta h2 { font-size: 0 !important; }
          .public-final-cta h2::after {
            content: "Haz tu primer test y comprueba cómo trabaja Tu Coach.";
            font-size: 2rem;
          }
          .public-footer strong { font-size: 0 !important; }
          .public-footer strong::after { content: "Tu Coach"; font-size: inherit; }

          /* Empleo autenticado: mismo lenguaje visual que el resto de Tu Coach. */
          .employment-app { width: 100%; }
          .employment-app > main {
            width: min(1240px, calc(100% - 40px)) !important;
            max-width: 1240px !important;
            margin: 0 auto !important;
            padding: 24px 0 56px !important;
            font-family: inherit !important;
            color: #172033 !important;
          }
          .employment-app > main > header {
            margin: 0 0 22px !important;
            padding: 22px 26px !important;
            border: 1px solid #d9e2ef !important;
            border-radius: 18px !important;
            background: #fff !important;
            box-shadow: 0 8px 24px rgba(31,55,94,.06) !important;
            align-items: center !important;
          }
          .employment-app > main > header .kicker {
            font-size: 0 !important;
            opacity: 1 !important;
            margin-bottom: 5px !important;
          }
          .employment-app > main > header .kicker::after {
            content: "TU COACH · EMPLEO PÚBLICO";
            font-size: 11px;
            letter-spacing: 1.5px;
            font-weight: 800;
            color: #1557c0;
          }
          .employment-app > main > header h1 {
            margin: 0 !important;
            font-size: 34px !important;
            line-height: 1.12 !important;
            letter-spacing: -.025em !important;
          }
          .employment-app > main > header p {
            margin: 7px 0 0 !important;
            color: #5c6b80 !important;
            font-size: 15px !important;
          }
          .employment-app .headerActions { gap: 9px !important; }
          .employment-app .headerActions .link {
            color: #1557c0 !important;
            font-weight: 750 !important;
          }
          .employment-app .headerActions .secondary,
          .employment-app .primary {
            border: 1px solid #1557c0 !important;
            border-radius: 9px !important;
            background: #1557c0 !important;
            color: #fff !important;
            font-weight: 800 !important;
            text-decoration: none !important;
          }
          .employment-app .headerActions .secondary { padding: 9px 14px !important; }
          .employment-app > main > .grid {
            grid-template-columns: 250px minmax(0, 1fr) !important;
            gap: 18px !important;
          }
          .employment-app .panel {
            border: 1px solid #d9e2ef !important;
            border-radius: 18px !important;
            padding: 20px !important;
            background: #fff !important;
            box-shadow: 0 6px 20px rgba(31,55,94,.035) !important;
          }
          .employment-app .h2 {
            font-size: 20px !important;
            letter-spacing: -.015em !important;
          }
          .employment-app .item,
          .employment-app .activeItem {
            margin-top: 2px !important;
            padding: 10px 10px !important;
            border-radius: 9px !important;
            font-family: inherit !important;
            font-size: 14px !important;
          }
          .employment-app .item { color: #34435a !important; }
          .employment-app .item:hover { background: #f3f7fc !important; }
          .employment-app .activeItem {
            background: #eaf2ff !important;
            color: #1557c0 !important;
            font-weight: 800 !important;
          }
          .employment-app .card {
            border: 1px solid #d9e2ef !important;
            border-radius: 14px !important;
            background: #fff !important;
            box-shadow: 0 5px 16px rgba(31,55,94,.03) !important;
          }
          .employment-app .cardButton { padding: 18px !important; }
          .employment-app .cardTop,
          .employment-app .muted,
          .employment-app .meta { color: #64738a !important; }
          .employment-app .cardOrg { color: #53627a !important; opacity: 1 !important; }
          .employment-app .badge {
            border: 1px solid #bcd1ee !important;
            background: #f4f8ff !important;
            color: #1557c0 !important;
          }
          .employment-app .cardTitle { color: #172033 !important; }
          .employment-app .cardSummary { color: #34435a !important; }
          .employment-app .follow,
          .employment-app .primary {
            border-radius: 9px !important;
            font-family: inherit !important;
            font-weight: 800 !important;
          }
          .employment-app .follow {
            border: 1px solid #bcd1ee !important;
            background: #eef5ff !important;
            color: #1557c0 !important;
            padding: 9px 13px !important;
          }
          .employment-app .cardLayout > .primary { margin-right: 18px !important; padding: 9px 13px !important; }
          .employment-app .sectionHead { margin-bottom: 2px !important; }
          .employment-app .error {
            border: 1px solid #e5bcbc !important;
            border-radius: 10px !important;
            background: #fff7f7 !important;
            color: #8a2424 !important;
          }

          @media (max-width: 700px) {
            .employment-entry { width: min(100% - 20px, 1240px); }
            .employment-entry-inner { align-items: flex-start; flex-direction: column; gap: 10px; }
            .employment-entry a { width: 100%; justify-content: center; }
            .public-process #materiales-proceso .process-content::after { font-size: .98rem; }
            .employment-app > main { width: min(100% - 20px, 1240px) !important; }
            .employment-app > main > header { padding: 20px !important; }
            .employment-app > main > .grid { grid-template-columns: 1fr !important; }
            .employment-app .headerActions { flex-wrap: wrap; }
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
        <EmploymentPublicGate>{children}</EmploymentPublicGate>
        <AuthenticatedEmploymentNav />
      </body>
    </html>
  );
}
