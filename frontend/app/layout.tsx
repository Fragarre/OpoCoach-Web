import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "NetReto | Oposiciones para la Administración Pública de la Comunidad Valenciana",
  description: "NetReto: simulacros, tests, análisis y materiales para preparar oposiciones para la Administración Pública de la Comunidad Valenciana.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es">
      <body>
        <nav
          style={{
            display: "flex",
            justifyContent: "flex-end",
            gap: 16,
            padding: "10px 20px",
            borderBottom: "1px solid #e5e8ee",
            fontFamily: "system-ui, sans-serif",
            fontSize: 14,
          }}
        >
          <Link href="/empleo" style={{ textDecoration: "none" }}>
            Empleo público
          </Link>
        </nav>
        {children}
      </body>
    </html>
  );
}
