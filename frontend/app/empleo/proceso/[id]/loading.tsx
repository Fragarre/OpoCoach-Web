export default function Loading() {
  return (
    <main style={styles.main}>
      <div style={styles.overlay} role="status" aria-live="polite" aria-busy="true">
        <div style={styles.box}>
          <span style={styles.spinner} aria-hidden="true" />
          Cargando convocatoria…
        </div>
      </div>
      <style>{`@keyframes empleo-proceso-spin { to { transform: rotate(360deg); } }`}</style>
    </main>
  );
}

const styles: Record<string, React.CSSProperties> = {
  main: { minHeight: "60vh", fontFamily: "system-ui, sans-serif" },
  overlay: { position: "fixed", inset: 0, zIndex: 2000, background: "rgba(255,255,255,0.72)", display: "flex", alignItems: "center", justifyContent: "center", pointerEvents: "all", cursor: "wait" },
  box: { display: "flex", alignItems: "center", gap: 10, padding: "12px 18px", border: "1px solid #d9dee8", borderRadius: 10, background: "#fff", boxShadow: "0 8px 30px rgba(23,32,51,0.12)", fontSize: 14, fontWeight: 600 },
  spinner: { width: 18, height: 18, border: "2px solid #d9dee8", borderTopColor: "#172033", borderRadius: "50%", display: "inline-block", animation: "empleo-proceso-spin .8s linear infinite" },
};
