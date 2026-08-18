import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "OpoCoach",
  description: "Simulacros, tests y análisis para preparar tu oposición",
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
