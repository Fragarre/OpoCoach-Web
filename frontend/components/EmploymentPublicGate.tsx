"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { createClient } from "@/lib/supabase/client";

export default function EmploymentPublicGate({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const supabase = useMemo(() => createClient(), []);
  const [comprobando, setComprobando] = useState(pathname === "/empleo");
  const [autenticado, setAutenticado] = useState(false);

  useEffect(() => {
    if (pathname !== "/empleo") {
      setComprobando(false);
      return;
    }

    let activo = true;
    void supabase.auth.getSession().then(({ data }) => {
      if (!activo) return;
      setAutenticado(Boolean(data.session));
      setComprobando(false);
    });

    const { data: listener } = supabase.auth.onAuthStateChange((_event, session) => {
      if (!activo || pathname !== "/empleo") return;
      setAutenticado(Boolean(session));
      setComprobando(false);
    });

    return () => {
      activo = false;
      listener.subscription.unsubscribe();
    };
  }, [pathname, supabase]);

  if (pathname !== "/empleo") return <>{children}</>;
  if (comprobando) return <EmploymentLoading />;
  if (autenticado) return <>{children}</>;

  return <EmploymentMiniLanding />;
}

function EmploymentLoading() {
  return (
    <main style={styles.loading}>
      <div style={styles.loadingBox}>Cargando Empleo público…</div>
    </main>
  );
}

function EmploymentMiniLanding() {
  return (
    <main style={styles.main}>
      <section style={styles.hero}>
        <div style={styles.eyebrow}>EMPLEO PÚBLICO · TU COACH</div>
        <h1 style={styles.title}>Descubre oportunidades. Sigue sus novedades. Prepárate para tu plaza.</h1>
        <p style={styles.lead}>
          Tu Coach incorpora una funcionalidad para localizar oportunidades de empleo público,
          consultar la información oficial de cada convocatoria y seguir sus novedades desde un mismo lugar.
        </p>
        <div style={styles.actions}>
          <Link href="/" style={styles.primary}>Iniciar sesión o registrarse →</Link>
          <Link href="/" style={styles.secondary}>Volver a Tu Coach</Link>
        </div>
        <p style={styles.note}>Necesitas iniciar sesión para consultar y seguir las oportunidades.</p>
      </section>

      <section style={styles.grid} aria-label="Qué puedes hacer">
        <article style={styles.card}>
          <span style={styles.number}>01</span>
          <span style={styles.kicker}>DESCUBRE</span>
          <h2 style={styles.cardTitle}>Encuentra oportunidades que encajan contigo</h2>
          <p style={styles.cardText}>Consulta convocatorias de los organismos disponibles y filtra las oportunidades que te interesan.</p>
        </article>
        <article style={styles.card}>
          <span style={styles.number}>02</span>
          <span style={styles.kicker}>SIGUE</span>
          <h2 style={styles.cardTitle}>No pierdas de vista sus novedades oficiales</h2>
          <p style={styles.cardText}>Sigue una convocatoria y consulta desde Mi seguimiento sus publicaciones y cambios relevantes.</p>
        </article>
        <article style={styles.card}>
          <span style={styles.number}>03</span>
          <span style={styles.kicker}>PREPÁRATE</span>
          <h2 style={styles.cardTitle}>Conecta la oportunidad con tu preparación</h2>
          <p style={styles.cardText}>Cuando una convocatoria encaja contigo, Tu Coach te acompaña en el entrenamiento y el estudio.</p>
        </article>
      </section>

      <section style={styles.footerBlock}>
        <div>
          <span style={styles.kicker}>DE LA CONVOCATORIA A LA PREPARACIÓN</span>
          <h2 style={styles.footerTitle}>Una misma herramienta para descubrir, seguir y prepararte.</h2>
        </div>
        <Link href="/" style={styles.primary}>Entrar en Tu Coach →</Link>
      </section>
    </main>
  );
}

const styles: Record<string, React.CSSProperties> = {
  main: { maxWidth: 1120, margin: "0 auto", padding: "48px 20px 72px", fontFamily: "system-ui, sans-serif", color: "#172033" },
  loading: { minHeight: "70vh", display: "grid", placeItems: "center", padding: 24, fontFamily: "system-ui, sans-serif", color: "#172033", background: "#f5f7fb" },
  loadingBox: { padding: "14px 18px", border: "1px solid #d9dee8", borderRadius: 10, background: "#fff", boxShadow: "0 8px 28px rgba(23,32,51,.08)", fontWeight: 600 },
  hero: { padding: "52px 56px", border: "1px solid #c9daf3", borderRadius: 24, background: "linear-gradient(135deg,#f7faff,#edf5ff)", boxShadow: "0 18px 45px rgba(31,55,94,.08)" },
  eyebrow: { fontSize: 12, letterSpacing: 1.5, fontWeight: 800, color: "#1557c0", marginBottom: 12 },
  title: { maxWidth: 850, margin: 0, fontSize: "clamp(34px,5vw,58px)", lineHeight: 1.05, letterSpacing: "-.03em" },
  lead: { maxWidth: 760, margin: "22px 0 0", fontSize: 18, lineHeight: 1.65, color: "#53627a" },
  actions: { display: "flex", flexWrap: "wrap", gap: 10, marginTop: 28 },
  primary: { display: "inline-flex", alignItems: "center", justifyContent: "center", minHeight: 44, padding: "10px 16px", borderRadius: 9, background: "#1557c0", color: "#fff", textDecoration: "none", fontWeight: 800 },
  secondary: { display: "inline-flex", alignItems: "center", justifyContent: "center", minHeight: 44, padding: "10px 16px", borderRadius: 9, border: "1px solid #b9c6d8", background: "#fff", color: "#172033", textDecoration: "none", fontWeight: 700 },
  note: { margin: "14px 0 0", fontSize: 12, color: "#68768a" },
  grid: { display: "grid", gridTemplateColumns: "repeat(3,minmax(0,1fr))", gap: 0, marginTop: 22, border: "1px solid #d9dee8", borderRadius: 18, overflow: "hidden", background: "#fff" },
  card: { padding: "30px 28px 32px", borderRight: "1px solid #d9dee8" },
  number: { display: "grid", placeItems: "center", width: 50, height: 50, marginBottom: 24, borderRadius: 14, background: "#e7f0ff", color: "#1557c0", fontWeight: 900 },
  kicker: { display: "block", fontSize: 12, letterSpacing: 1.4, fontWeight: 800, color: "#5c6b80", marginBottom: 8 },
  cardTitle: { margin: 0, fontSize: 22, lineHeight: 1.25 },
  cardText: { margin: "10px 0 0", color: "#5c6b80", fontSize: 15, lineHeight: 1.55 },
  footerBlock: { display: "flex", alignItems: "center", justifyContent: "space-between", gap: 24, marginTop: 22, padding: "28px 30px", borderRadius: 18, background: "#172033", color: "#fff" },
  footerTitle: { margin: 0, fontSize: 24, lineHeight: 1.25 },
};
