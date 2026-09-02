import type { Metadata } from "next";
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
      <body>{children}</body>
    </html>
  );
}
