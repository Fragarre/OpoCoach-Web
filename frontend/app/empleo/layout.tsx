import type { ReactNode } from "react";
import NovedadesAviso from "./NovedadesAviso";

export default function EmpleoLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <NovedadesAviso />
      {children}
    </>
  );
}
