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
          /* Transición visual de marca: mantenemos las rutas y el dominio técnico actuales. */
          .brand-name {
            font-size: 0 !important;
          }
          .brand-name::after {
            content: "Tu Coach";
            font-size: 1.18rem;
          }
          .brand-mark {
            font-size: 0 !important;
          }
          .brand-mark::after {
            content: "TC";
            font-size: .72rem;
            font-weight: 900;
            letter-spacing: -.02em;
          }
          .brand-byline {
            display: none !important;
          }
          .brand-transition {
            width: min(1240px, calc(100% - 40px));
            margin: 0 auto 8px;
            padding: 8px 12px;
            border: 1px solid #d9e4f5;
            border-radius: 10px;
            background: #f6f9ff;
            color: #526078;
            font: 600 13px/1.4 system-ui, sans-serif;
          }
          .brand-transition a {
            color: #1557c0;
            text-decoration: none;
            font-weight: 800;
          }
          .brand-transition a:hover {
            text-decoration: underline;
          }
          @media (max-width: 700px) {
            .brand-transition {
              width: min(100% - 20px, 1240px);
              font-size: 12px;
            }
          }
        `}</style>

        <nav
          style={{
            display: "flex",
            justifyContent: "flex-end",
            gap: 16,
            padding: "10px 20px",
            borderBottom: "1px solid #e5e8ee",
            fontFamily: "system-ui,sans-serif",
            fontSize: 14,
          }}
        >
          <Link href="/empleo" style={{ textDecoration: "none" }}>
            Empleo público
          </Link>
          <Link href="/empleo/seguimiento" style={{ textDecoration: "none" }}>
            Mi seguimiento
          </Link>
        </nav>

        <div className="brand-transition">
          <strong>Tu Coach</strong> · preparación, entrenamiento y oportunidades de empleo público. {" "}
          <Link href="/empleo">Descubrir oportunidades →</Link>
        </div>

        <EmploymentNovedadesAviso />
        {children}
      </body>
    </html>
  );
}
