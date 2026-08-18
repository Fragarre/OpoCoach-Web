"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import type { Session } from "@supabase/supabase-js";

import { apiFetch } from "@/lib/api";
import { createClient } from "@/lib/supabase/client";

type EstadoSuscripcion = {
  suscrito: boolean;
  status: string;
  customer_id: string | null;
  subscription_id: string | null;
  plan: string | null;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
};

type Me = {
  id: string;
  email: string;
};

type Convocatoria = {
  id: number;
  puesto: string;
  numero: string;
  anio: number;
  codigo: string;
};

type Pregunta = {
  simulacro_pregunta_id: number;
  orden: number;
  parte_nombre: string | null;
  respuesta_usuario: string | null;
  seguridad_usuario: string | null;
  enunciado: string;
  opcion_a: string;
  opcion_b: string;
  opcion_c: string;
  opcion_d: string;
};

type PreguntaCorregida = Pregunta & {
  respuesta_correcta: string;
  resultado: "ACIERTO" | "FALLO" | "NO_CONTESTADA";
};

type Resultado = {
  simulacro_id: number;
  total: number;
  contestadas: number;
  aciertos: number;
  fallos: number;
  no_contestadas: number;
  puntos: number;
  nota: number;
  tiempo_correccion_segundos: number;
};

type AcumuladoTema = {
  tema_id: number | null;
  parte: string;
  numero_tema: number;
  titulo: string;
  preguntas: number;
  contestadas: number;
  no_contestadas: number;
  aciertos: number;
  fallos: number;
  fallos_seguro: number;
  porcentaje_convocatoria: number;
  porcentaje_aciertos: number;
  porcentaje_fallos: number;
  porcentaje_no_contestadas: number;
  porcentaje_aciertos_contestadas: number;
};

type AcumuladoNorma = {
  norma: string;
  preguntas: number;
  contestadas: number;
  no_contestadas: number;
  aciertos: number;
  fallos: number;
  fallos_seguro: number;
  porcentaje_convocatoria: number;
  porcentaje_aciertos: number;
  porcentaje_fallos: number;
  porcentaje_no_contestadas: number;
  porcentaje_aciertos_contestadas: number;
};

type AcumuladoSeguridad = {
  codigo: "SEGURO" | "MENOS_SEGURO";
  seguridad: string;
  contestadas: number;
  aciertos: number;
  fallos: number;
  porcentaje_aciertos: number;
  porcentaje_fallos: number;
};

type ResultadoAcumulado = {
  convocatoria_id: number;
  tipo_prueba: "SIMULACRO" | "TEST";
  simulacros: number;
  simulacros_ids: number[];
  preguntas: number;
  contestadas: number;
  no_contestadas: number;
  aciertos: number;
  fallos: number;
  temas: AcumuladoTema[];
  normas: AcumuladoNorma[];
  seguridad: AcumuladoSeguridad[];
  firma_datos: string;
};

type PdfGenerado = {
  filename: string;
  content_base64: string;
};

type AnalisisRendimiento = {
  firma_datos: string;
  texto: string;
};

type SimulacroListado = {
  id: number;
  convocatoria_id: number;
  numero: number;
  fecha_generacion: string;
  total_preguntas: number;
  estado: "GENERADO" | "FINALIZADO";
  tipo_prueba: "SIMULACRO" | "TEST";
  convocatoria_codigo: string | null;
  contestadas: number;
};

type TemaTest = {
  id: number;
  parte: string;
  numero_tema: number;
  titulo: string;
  tipo_contenido: string | null;
  disponibles: number;
};

type NormaTest = {
  norma_clave: string;
  norma_nombre: string;
  disponibles: number;
};

type TestCreado = {
  id: number;
  numero: number;
  total_solicitado: number;
  total_generado: number;
  avisos: string[];
};

type RespuestaLocal = {
  respuesta: string | null;
  seguridad: string | null;
};

const ORIGENES = ["A1", "A2", "C1", "C2"] as const;
const FUENTES = ["REAL", "IA"] as const;

const SEGURIDADES = [
  ["SEGURO", "Seguro"],
  ["MENOS_SEGURO", "Menos seguro"],
] as const;

function formatearTiempo(segundos: number): string {
  const total = Math.max(0, Math.floor(segundos));
  const horas = Math.floor(total / 3600);
  const minutos = Math.floor((total % 3600) / 60);
  const segundosRestantes = total % 60;

  if (horas > 0) {
    return `${horas} h ${String(minutos).padStart(2, "0")} min ${String(
      segundosRestantes
    ).padStart(2, "0")} s`;
  }

  return `${minutos} min ${String(segundosRestantes).padStart(2, "0")} s`;
}

function CronometroCorreccion({
  inicioMs,
  tiempoPrevio,
}: {
  inicioMs: number;
  tiempoPrevio: number;
}) {
  const [ahora, setAhora] = useState(Date.now());

  useEffect(() => {
    const intervalo = window.setInterval(() => setAhora(Date.now()), 1000);
    return () => window.clearInterval(intervalo);
  }, []);

  const sesion = Math.max(0, Math.floor((ahora - inicioMs) / 1000));
  return (
    <div style={{ fontWeight: 600, marginBottom: 14 }}>
      Tiempo transcurrido: {formatearTiempo(tiempoPrevio + sesion)}
    </div>
  );
}

export default function Home() {
  const supabase = useMemo(() => createClient(), []);
  const [session, setSession] = useState<Session | null>(null);
  const [cargandoSesion, setCargandoSesion] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [me, setMe] = useState<Me | null>(null);
  const [convocatorias, setConvocatorias] = useState<Convocatoria[]>([]);
  const [misSimulacros, setMisSimulacros] = useState<SimulacroListado[]>([]);
  const [misTests, setMisTests] = useState<SimulacroListado[]>([]);
  const [seccion, setSeccion] = useState<"SIMULACROS" | "TESTS">("SIMULACROS");
  const [tipoActivo, setTipoActivo] = useState<"SIMULACRO" | "TEST" | null>(null);
  const [convocatoriaTestId, setConvocatoriaTestId] = useState<number | null>(null);
  const [modoTest, setModoTest] = useState<"TEMA" | "NORMA">("TEMA");
  const [numeroPreguntasTest, setNumeroPreguntasTest] = useState(20);
  const [temasTest, setTemasTest] = useState<TemaTest[]>([]);
  const [normasTest, setNormasTest] = useState<NormaTest[]>([]);
  const [temasSeleccionados, setTemasSeleccionados] = useState<number[]>([]);
  const [normasSeleccionadas, setNormasSeleccionadas] = useState<string[]>([]);
  const [simulacroId, setSimulacroId] = useState<number | null>(null);
  const [preguntas, setPreguntas] = useState<Pregunta[]>([]);
  const [respuestas, setRespuestas] = useState<Record<number, RespuestaLocal>>({});
  const [evaluarSeguridad, setEvaluarSeguridad] = useState(false);
  const [resultado, setResultado] = useState<Resultado | null>(null);
  const [mostrarCronometro, setMostrarCronometro] = useState(false);
  const [tiempoPrevioCorreccion, setTiempoPrevioCorreccion] = useState(0);
  const [inicioCorreccionMs, setInicioCorreccionMs] = useState<number | null>(null);
  const [correccion, setCorreccion] = useState<PreguntaCorregida[]>([]);
  const [resultadoAcumulado, setResultadoAcumulado] = useState<ResultadoAcumulado | null>(null);
  const [analisisRendimiento, setAnalisisRendimiento] = useState<
    Record<string, AnalisisRendimiento>
  >({});
  const [mensaje, setMensaje] = useState("");
  const [error, setError] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const [accionEnCurso, setAccionEnCurso] = useState<string | null>(null);
  const [checkoutRetorno, setCheckoutRetorno] = useState<"success" | "cancel" | null>(null);
  const [estadoSuscripcion, setEstadoSuscripcion] = useState<EstadoSuscripcion | null>(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const estado = params.get("checkout");

    if (estado === "success" || estado === "cancel") {
      setCheckoutRetorno(estado);
      window.history.replaceState({}, "", window.location.pathname);
    }
  }, []);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session);
      setCargandoSesion(false);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession);
      if (!nextSession) {
        setMe(null);
        setConvocatorias([]);
        setMisSimulacros([]);
        setMisTests([]);
        setAnalisisRendimiento({});
        limpiarSimulacro();
      }
    });

    return () => subscription.unsubscribe();
  }, [supabase]);

  useEffect(() => {
    if (!session) return;

    Promise.all([
      apiFetch<Me>("api/v1/me"),
      apiFetch<Convocatoria[]>("api/v1/convocatorias"),
      apiFetch<SimulacroListado[]>("api/v1/simulacros"),
      apiFetch<SimulacroListado[]>("api/v1/tests"),
      apiFetch<EstadoSuscripcion>("api/v1/billing/subscription"),
    ])
      .then(([usuario, lista, guardados, tests, suscripcion]) => {
        setMe(usuario);
        setConvocatorias(lista);
        setMisSimulacros(guardados);
        setMisTests(tests);
        setEstadoSuscripcion(suscripcion);
        if (convocatoriaTestId === null && lista.length > 0) {
          setConvocatoriaTestId(lista[0].id);
        }
        setError("");
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : String(err));
      });
  }, [session]);

  useEffect(() => {
    if (!session || convocatoriaTestId === null) return;

    const query = FUENTES
      .map((f) => `fuente=${encodeURIComponent(f)}`)
      .join("&");

    if (!query) {
      setTemasTest([]);
      setNormasTest([]);
      return;
    }

    Promise.all([
      apiFetch<TemaTest[]>(
        `api/v1/convocatorias/${convocatoriaTestId}/tests/temas?${query}`
      ),
      apiFetch<NormaTest[]>(
        `api/v1/convocatorias/${convocatoriaTestId}/tests/normas?${query}`
      ),
    ])
      .then(([temas, normas]) => {
        setTemasTest(temas);
        setNormasTest(normas);
        setTemasSeleccionados((actual) =>
          actual.filter((id) => temas.some((t) => t.id === id))
        );
        setNormasSeleccionadas((actual) =>
          actual.filter((clave) =>
            normas.some((n) => n.norma_clave === clave)
          )
        );
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : String(err));
      });
  }, [session, convocatoriaTestId]);

  function limpiarSimulacro() {
    setPreguntas([]);
    setRespuestas({});
    setEvaluarSeguridad(false);
    setResultado(null);
    setCorreccion([]);
    setResultadoAcumulado(null);
    setSimulacroId(null);
    setTipoActivo(null);
    setMostrarCronometro(false);
    setTiempoPrevioCorreccion(0);
    setInicioCorreccionMs(null);
  }


  function iniciarTiempoCorreccion(tiempoPrevio = 0) {
    setTiempoPrevioCorreccion(Math.max(0, Math.floor(tiempoPrevio)));
    setInicioCorreccionMs(Date.now());
    setMostrarCronometro(false);
  }


  async function recargarSimulacros() {
    const guardados = await apiFetch<SimulacroListado[]>("api/v1/simulacros");
    setMisSimulacros(guardados);
  }

  async function recargarTests() {
    const guardados = await apiFetch<SimulacroListado[]>("api/v1/tests");
    setMisTests(guardados);
  }

  async function recargarListaActiva() {
    if (tipoActivo === "TEST") {
      await recargarTests();
    } else {
      await recargarSimulacros();
    }
  }

  function inicializarRespuestas(lista: Pregunta[]) {
    const iniciales: Record<number, RespuestaLocal> = {};
    lista.forEach((p) => {
      iniciales[p.simulacro_pregunta_id] = {
        respuesta: p.respuesta_usuario,
        seguridad: p.seguridad_usuario,
      };
    });
    setRespuestas(iniciales);
    setEvaluarSeguridad(
      lista.some((p) => p.seguridad_usuario !== null)
    );
  }

  async function abrirSimulacro(simulacro: SimulacroListado) {
    setOcupado(true);
    setAccionEnCurso(
      simulacro.estado === "FINALIZADO"
        ? "Abriendo corrección..."
        : "Recuperando simulacro..."
    );
    setError("");
    setMensaje("");
    limpiarSimulacro();
    setTipoActivo(simulacro.tipo_prueba);

    try {
      if (simulacro.estado === "FINALIZADO") {
        const [res, corr, acumulado] = await Promise.all([
          apiFetch<Resultado>(
            `api/v1/simulacros/${simulacro.id}/resultado`
          ),
          apiFetch<PreguntaCorregida[]>(
            `api/v1/simulacros/${simulacro.id}/correccion`
          ),
          apiFetch<ResultadoAcumulado>(
            `api/v1/simulacros/${simulacro.id}/acumulado`
          ),
        ]);
        setSimulacroId(simulacro.id);
        setResultado(res);
        setTiempoPrevioCorreccion(res.tiempo_correccion_segundos);
        setInicioCorreccionMs(null);
        setMostrarCronometro(false);
        setCorreccion(corr);
        setResultadoAcumulado(acumulado);
      } else {
        const [lista, tiempo] = await Promise.all([
          apiFetch<Pregunta[]>(
            `api/v1/simulacros/${simulacro.id}/preguntas`
          ),
          apiFetch<{ tiempo_correccion_segundos: number }>(
            `api/v1/simulacros/${simulacro.id}/tiempo-correccion`
          ),
        ]);
        setSimulacroId(simulacro.id);
        setPreguntas(lista);
        inicializarRespuestas(lista);
        iniciarTiempoCorreccion(tiempo.tiempo_correccion_segundos);
      }
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setOcupado(false);
      setAccionEnCurso(null);
    }
  }

  async function modificarRespuestas() {
    if (simulacroId === null) return;

    setOcupado(true);
    setAccionEnCurso("Preparando modificación de respuestas...");
    setError("");
    setMensaje("");

    try {
      const [lista, tiempo] = await Promise.all([
        apiFetch<Pregunta[]>(
          `api/v1/simulacros/${simulacroId}/preguntas`
        ),
        apiFetch<{ tiempo_correccion_segundos: number }>(
          `api/v1/simulacros/${simulacroId}/tiempo-correccion`
        ),
      ]);

      setPreguntas(lista);
      inicializarRespuestas(lista);
      setResultado(null);
      setCorreccion([]);
      setResultadoAcumulado(null);
      iniciarTiempoCorreccion(tiempo.tiempo_correccion_segundos);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setOcupado(false);
      setAccionEnCurso(null);
    }
  }

  async function eliminarGuardado(simulacro: SimulacroListado) {
    const nombre = simulacro.tipo_prueba === "TEST" ? "test" : "simulacro";
    const confirmar = window.confirm(
      `¿Eliminar definitivamente el ${nombre} nº ${simulacro.numero}?`
    );
    if (!confirmar) return;

    setOcupado(true);
    setAccionEnCurso(`Eliminando simulacro ${simulacro.numero}...`);
    setError("");
    setMensaje("");

    try {
      await apiFetch<void>(`api/v1/simulacros/${simulacro.id}`, {
        method: "DELETE",
      });
      if (simulacro.tipo_prueba === "TEST") {
        await recargarTests();
      } else {
        await recargarSimulacros();
      }
      setMensaje(
        `${simulacro.tipo_prueba === "TEST" ? "Test" : "Simulacro"} nº ${simulacro.numero} eliminado.`
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setOcupado(false);
      setAccionEnCurso(null);
    }
  }

  function claveAnalisisActual(): string | null {
    if (!resultadoAcumulado) return null;
    return `${resultadoAcumulado.tipo_prueba}:${resultadoAcumulado.convocatoria_id}`;
  }

  function analisisActual(): AnalisisRendimiento | null {
    const clave = claveAnalisisActual();
    if (!clave || !resultadoAcumulado) return null;

    const cache = analisisRendimiento[clave];
    if (!cache) return null;

    return cache.firma_datos === resultadoAcumulado.firma_datos
      ? cache
      : null;
  }

  async function descargarPdfSoluciones() {
    if (simulacroId === null) return;

    setOcupado(true);
    setAccionEnCurso("Generando PDF de soluciones...");
    setError("");
    setMensaje("");

    try {
      const pdf = await apiFetch<PdfGenerado>(
        `api/v1/simulacros/${simulacroId}/pdf-soluciones`
      );

      const binario = atob(pdf.content_base64);
      const bytes = new Uint8Array(binario.length);

      for (let i = 0; i < binario.length; i += 1) {
        bytes[i] = binario.charCodeAt(i);
      }

      const blob = new Blob([bytes], { type: "application/pdf" });
      const url = URL.createObjectURL(blob);
      const enlace = document.createElement("a");

      enlace.href = url;
      enlace.download = pdf.filename;
      document.body.appendChild(enlace);
      enlace.click();
      enlace.remove();

      URL.revokeObjectURL(url);
      setMensaje("PDF de soluciones generado.");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setOcupado(false);
      setAccionEnCurso(null);
    }
  }


  async function descargarPdfPreguntas() {
    if (simulacroId === null) return;

    setOcupado(true);
    setAccionEnCurso("Generando PDF de preguntas...");
    setError("");
    setMensaje("");

    try {
      const pdf = await apiFetch<PdfGenerado>(
        `api/v1/simulacros/${simulacroId}/pdf-preguntas?incluir_seguridad=true`
      );

      const binario = atob(pdf.content_base64);
      const bytes = new Uint8Array(binario.length);

      for (let i = 0; i < binario.length; i += 1) {
        bytes[i] = binario.charCodeAt(i);
      }

      const blob = new Blob([bytes], { type: "application/pdf" });
      const url = URL.createObjectURL(blob);
      const enlace = document.createElement("a");

      enlace.href = url;
      enlace.download = pdf.filename;
      document.body.appendChild(enlace);
      enlace.click();
      enlace.remove();

      URL.revokeObjectURL(url);
      setMensaje("PDF de preguntas generado.");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setOcupado(false);
      setAccionEnCurso(null);
    }
  }


  async function generarAnalisisRendimiento() {
    if (simulacroId === null || !resultadoAcumulado) return;

    setOcupado(true);
    setAccionEnCurso("Analizando los resultados acumulados...");
    setError("");
    setMensaje("");

    try {
      const analisis = await apiFetch<AnalisisRendimiento>(
        `api/v1/simulacros/${simulacroId}/analisis-rendimiento`,
        { method: "POST" }
      );

      const clave = `${resultadoAcumulado.tipo_prueba}:${resultadoAcumulado.convocatoria_id}`;
      setAnalisisRendimiento((actual) => ({
        ...actual,
        [clave]: analisis,
      }));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setOcupado(false);
      setAccionEnCurso(null);
    }
  }

  function renderInlineMarkdown(texto: string) {
    const partes = texto.split(/(\*\*[^*]+\*\*)/g);

    return partes.map((parte, indice) => {
      if (parte.startsWith("**") && parte.endsWith("**")) {
        return <strong key={indice}>{parte.slice(2, -2)}</strong>;
      }

      return <span key={indice}>{parte}</span>;
    });
  }

  function renderAnalisisRendimiento(texto: string) {
    return texto.split("\n").map((linea, indice) => {
      const textoLinea = linea.trim();

      if (!textoLinea) {
        return <div key={indice} style={{ height: 8 }} />;
      }

      if (textoLinea.startsWith("### ")) {
        return (
          <h3 key={indice} style={{ marginTop: 22, marginBottom: 10 }}>
            {renderInlineMarkdown(textoLinea.slice(4))}
          </h3>
        );
      }

      const numero = textoLinea.match(/^(\d+)\.\s+(.*)$/);
      if (numero) {
        return (
          <p key={indice} style={{ margin: "8px 0 8px 18px" }}>
            <strong>{numero[1]}.</strong>{" "}
            {renderInlineMarkdown(numero[2])}
          </p>
        );
      }

      if (textoLinea.startsWith("- ")) {
        return (
          <p key={indice} style={{ margin: "6px 0 6px 22px" }}>
            • {renderInlineMarkdown(textoLinea.slice(2))}
          </p>
        );
      }

      return (
        <p key={indice} style={{ margin: "8px 0", lineHeight: 1.55 }}>
          {renderInlineMarkdown(textoLinea)}
        </p>
      );
    });
  }


  async function actualizarSuscripcion() {
    try {
      const estado = await apiFetch<EstadoSuscripcion>(
        "api/v1/billing/subscription"
      );
      setEstadoSuscripcion(estado);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function abrirCheckout() {
    setError("");
    setMensaje("");
    setOcupado(true);
    setAccionEnCurso("Abriendo pago seguro de Stripe...");

    try {
      const checkout = await apiFetch<{ id: string; url: string }>(
        "api/v1/billing/checkout",
        { method: "POST" }
      );
      window.location.assign(checkout.url);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setOcupado(false);
      setAccionEnCurso(null);
    }
  }

  async function iniciarSesion(event: FormEvent) {
    event.preventDefault();
    setError("");
    setMensaje("");
    setOcupado(true);
    setAccionEnCurso("Iniciando sesión...");

    const { error: authError } = await supabase.auth.signInWithPassword({
      email: email.trim(),
      password,
    });

    setOcupado(false);
    setAccionEnCurso(null);

    if (authError) {
      setError(authError.message);
      return;
    }

    setPassword("");
  }

  async function cerrarSesion() {
    await supabase.auth.signOut();
  }

  function toggle(
    valor: string,
    seleccion: string[],
    setter: (x: string[]) => void
  ) {
    setter(
      seleccion.includes(valor)
        ? seleccion.filter((x) => x !== valor)
        : [...seleccion, valor]
    );
  }

  function establecerRespuesta(id: number, respuesta: string | null) {
    setRespuestas((actual) => {
      const previo = actual[id] ?? { respuesta: null, seguridad: null };
      return {
        ...actual,
        [id]: {
          respuesta,
          seguridad: respuesta === null ? null : previo.seguridad,
        },
      };
    });
  }

  function establecerSeguridad(id: number, seguridad: string | null) {
    setRespuestas((actual) => {
      const previo = actual[id] ?? { respuesta: null, seguridad: null };
      return {
        ...actual,
        [id]: {
          ...previo,
          seguridad,
        },
      };
    });
  }

  function cambiarEvaluacionSeguridad(activada: boolean) {
    setEvaluarSeguridad(activada);
    if (!activada) {
      setRespuestas((actual) => {
        const siguientes: Record<number, RespuestaLocal> = {};
        for (const [id, respuesta] of Object.entries(actual)) {
          siguientes[Number(id)] = { ...respuesta, seguridad: null };
        }
        return siguientes;
      });
    }
  }

  async function crear(convocatoriaId: number) {
    setError("");
    setMensaje("");
    limpiarSimulacro();
    setOcupado(true);
    setAccionEnCurso("Creando simulacro...");

    try {
      const creado = await apiFetch<{ id: number }>("api/v1/simulacros", {
        method: "POST",
        body: JSON.stringify({
          convocatoria_id: convocatoriaId,
          origenes: [...ORIGENES],
          fuentes: [...FUENTES],
        }),
      });

      const lista = await apiFetch<Pregunta[]>(
        `api/v1/simulacros/${creado.id}/preguntas`
      );

      setTipoActivo("SIMULACRO");
      setSimulacroId(creado.id);
      setPreguntas(lista);
      inicializarRespuestas(lista);
      iniciarTiempoCorreccion(0);
      await recargarSimulacros();
      setMensaje(
        `Simulacro ${creado.id} creado correctamente: ${lista.length} preguntas.`
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setOcupado(false);
      setAccionEnCurso(null);
    }
  }

  async function crearTest() {
    if (convocatoriaTestId === null) {
      setError("Selecciona una convocatoria.");
      return;
    }
    if (numeroPreguntasTest <= 0) {
      setError("El número de preguntas debe ser mayor que cero.");
      return;
    }
    if (modoTest === "TEMA" && temasSeleccionados.length === 0) {
      setError("Selecciona al menos un punto del temario.");
      return;
    }
    if (modoTest === "NORMA" && normasSeleccionadas.length === 0) {
      setError("Selecciona al menos una ley o norma.");
      return;
    }

    setOcupado(true);
    setAccionEnCurso("Creando test...");
    setError("");
    setMensaje("");
    limpiarSimulacro();
    setTipoActivo("TEST");

    try {
      const creado = await apiFetch<TestCreado>("api/v1/tests", {
        method: "POST",
        body: JSON.stringify({
          convocatoria_id: convocatoriaTestId,
          numero_preguntas: numeroPreguntasTest,
          modo_seleccion: modoTest,
          temas_seleccionados: temasSeleccionados,
          normas_seleccionadas: normasSeleccionadas,
          fuentes: [...FUENTES],
        }),
      });

      const lista = await apiFetch<Pregunta[]>(
        `api/v1/simulacros/${creado.id}/preguntas`
      );

      setSimulacroId(creado.id);
      setPreguntas(lista);
      inicializarRespuestas(lista);
      iniciarTiempoCorreccion(0);
      await recargarTests();

      const aviso =
        creado.avisos.length > 0 ? ` ${creado.avisos.join(" ")}` : "";
      setMensaje(
        `Test nº ${creado.numero} creado con ${creado.total_generado} preguntas.${aviso}`
      );
    } catch (err) {
      limpiarSimulacro();
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setOcupado(false);
      setAccionEnCurso(null);
    }
  }

  function payloadRespuestas() {
    return preguntas.map((p) => {
      const local = respuestas[p.simulacro_pregunta_id] ?? {
        respuesta: null,
        seguridad: null,
      };
      return {
        simulacro_pregunta_id: p.simulacro_pregunta_id,
        respuesta: local.respuesta,
        seguridad:
          evaluarSeguridad && local.respuesta ? local.seguridad : null,
      };
    });
  }

  function validarSeguridad(): string | null {
    if (!evaluarSeguridad) return null;

    for (const p of preguntas) {
      const local = respuestas[p.simulacro_pregunta_id];
      if (local?.respuesta && !local.seguridad) {
        return `La pregunta ${p.orden} está contestada pero no tiene nivel de seguridad.`;
      }
    }
    return null;
  }

  async function guardar() {
    if (simulacroId === null) return;

    const validacion = validarSeguridad();
    if (validacion) {
      setError(validacion);
      return;
    }

    setOcupado(true);
    setAccionEnCurso("Guardando respuestas...");
    setError("");
    setMensaje("");

    try {
      await apiFetch<void>(
        `api/v1/simulacros/${simulacroId}/respuestas`,
        {
          method: "PUT",
          body: JSON.stringify({ respuestas: payloadRespuestas() }),
        }
      );
      await recargarListaActiva();
      setMensaje("Respuestas guardadas correctamente.");
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setOcupado(false);
      setAccionEnCurso(null);
    }
  }

  async function calificar() {
    if (simulacroId === null) return;

    const validacion = validarSeguridad();
    if (validacion) {
      setError(validacion);
      return;
    }

    setOcupado(true);
    setAccionEnCurso("Guardando y calificando simulacro...");
    setError("");
    setMensaje("");

    try {
      await apiFetch<void>(
        `api/v1/simulacros/${simulacroId}/respuestas`,
        {
          method: "PUT",
          body: JSON.stringify({ respuestas: payloadRespuestas() }),
        }
      );

      const segundosSesion =
        inicioCorreccionMs === null
          ? 0
          : Math.max(0, Math.floor((Date.now() - inicioCorreccionMs) / 1000));

      const res = await apiFetch<Resultado>(
        `api/v1/simulacros/${simulacroId}/finalizar?segundos_adicionales=${segundosSesion}`,
        { method: "POST" }
      );

      const [corr, acumulado] = await Promise.all([
        apiFetch<PreguntaCorregida[]>(
          `api/v1/simulacros/${simulacroId}/correccion`
        ),
        apiFetch<ResultadoAcumulado>(
          `api/v1/simulacros/${simulacroId}/acumulado`
        ),
      ]);

      setResultado(res);
      setTiempoPrevioCorreccion(res.tiempo_correccion_segundos);
      setInicioCorreccionMs(null);
      setMostrarCronometro(false);
      setCorreccion(corr);
      setResultadoAcumulado(acumulado);
      await recargarListaActiva();
      setMensaje(`${tipoActivo === "TEST" ? "Test" : "Simulacro"} calificado correctamente.`);
      window.scrollTo({ top: 0, behavior: "smooth" });
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setOcupado(false);
      setAccionEnCurso(null);
    }
  }

  if (cargandoSesion) {
    return <main className="page">Comprobando sesión...</main>;
  }

  if (!session) {
    return (
      <main className="login">
        <section className="card">
          <h1>OpoCoach</h1>
          <p className="muted">Acceso de pruebas a la nueva aplicación web.</p>

          {error && (
            <div className="error">
              {error}
            </div>
          )}

          <form onSubmit={iniciarSesion}>
            <label htmlFor="email">Correo electrónico</label>
            <input
              id="email"
              type="email"
              autoComplete="username"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />

            <label htmlFor="password">Contraseña</label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />

            <div style={{ marginTop: 18 }}>
              <button className="primary" disabled={ocupado} type="submit">
                {ocupado ? "Entrando..." : "Entrar"}
              </button>
            </div>
          </form>
        </section>
      </main>
    );
  }

  return (
    <main className="page">
      <section className="card">
        <div className="row space-between">
          <div>
            <h1>OpoCoach Web</h1>
            <div className="muted">
              {me ? `${me.email} · ${me.id}` : "Cargando usuario..."}
            </div>
          </div>
          <button className="secondary" onClick={cerrarSesion}>
            Cerrar sesión
          </button>
        </div>
      </section>

      {simulacroId === null && (
        <section className="card billing-test-card">
          <div className="row space-between">
            <div>
              <h2>Suscripción de prueba</h2>
              <p className="muted">
                Stripe Sandbox · OpoCoach · 10,00 € al mes.
                No se realizan cobros reales.
              </p>
              {estadoSuscripcion && (
                <p>
                  Estado verificado:{" "}
                  <strong>
                    {estadoSuscripcion.suscrito
                      ? "Suscripción activa"
                      : estadoSuscripcion.status}
                  </strong>
                </p>
              )}
              {checkoutRetorno === "success" && (
                <div className="success inline-feedback">
                  <div>
                    Stripe ha devuelto el pago como completado. El acceso solo
                    se considera activo cuando el webhook firmado haya
                    actualizado PostgreSQL.
                  </div>
                  <button
                    type="button"
                    className="secondary"
                    onClick={actualizarSuscripcion}
                  >
                    Comprobar suscripción
                  </button>
                </div>
              )}
              {checkoutRetorno === "cancel" && (
                <div className="working inline-feedback">
                  Pago cancelado. No se ha activado ninguna suscripción.
                </div>
              )}
            </div>
            {estadoSuscripcion?.suscrito ? (
              <span className="status status-finished">Activa</span>
            ) : (
              <button
                className="primary"
                disabled={ocupado}
                onClick={abrirCheckout}
              >
                {accionEnCurso?.includes("Stripe")
                  ? "Abriendo Stripe..."
                  : "Probar suscripción"}
              </button>
            )}
          </div>
        </section>
      )}

      {simulacroId === null && (
        <nav className="main-tabs">
          <button
            className={seccion === "SIMULACROS" ? "tab active" : "tab"}
            onClick={() => setSeccion("SIMULACROS")}
          >
            Simulacros
          </button>
          <button
            className={seccion === "TESTS" ? "tab active" : "tab"}
            onClick={() => setSeccion("TESTS")}
          >
            Tests
          </button>
        </nav>
      )}

      {(error || mensaje || accionEnCurso) && (
        <div className="feedback-stack" role="status" aria-live="polite">
          {error && (
            <div className="error feedback-message">
              <div className="feedback-text">{error}</div>
              <button
                type="button"
                className="feedback-close"
                aria-label="Cerrar mensaje"
                onClick={() => setError("")}
              >
                ×
              </button>
            </div>
          )}
          {mensaje && (
            <div className="success feedback-message">
              <div className="feedback-text">{mensaje}</div>
              <button
                type="button"
                className="feedback-close"
                aria-label="Cerrar mensaje"
                onClick={() => setMensaje("")}
              >
                ×
              </button>
            </div>
          )}
          {accionEnCurso && (
            <div className="working feedback-message">
              <div className="feedback-text">{accionEnCurso}</div>
            </div>
          )}
        </div>
      )}

      {simulacroId !== null && preguntas.length > 0 && (
        <section className="card">
          <h2>Documentos de la prueba</h2>
          <p className="muted">
            Los dos documentos se generan a partir de la copia congelada de esta
            prueba. Puedes descargarlos aunque no hayas corregido la prueba en la
            aplicación, por ejemplo para realizarla y corregirla en papel.
          </p>
          <div className="actions">
            <button
              className="secondary"
              disabled={ocupado}
              onClick={descargarPdfPreguntas}
            >
              {ocupado && accionEnCurso === "Generando PDF de preguntas..."
                ? "Generando PDF..."
                : "Descargar PDF de preguntas"}
            </button>

            <button
              className="secondary"
              disabled={ocupado}
              onClick={descargarPdfSoluciones}
            >
              {ocupado && accionEnCurso === "Generando PDF de soluciones..."
                ? "Generando PDF..."
                : "Descargar PDF de soluciones"}
            </button>
          </div>
        </section>
      )}

      {resultado && (
        <section className="card">
          <h2>Resultado</h2>
          <button
            className="secondary"
            disabled={ocupado}
            onClick={modificarRespuestas}
            style={{ marginBottom: 16 }}
          >
            {ocupado && accionEnCurso === "Preparando modificación de respuestas..."
              ? "Preparando..."
              : "Modificar respuestas"}
          </button>
          <div className="result-grid">
            <div><strong>{resultado.nota.toFixed(2)}</strong><span>Nota</span></div>
            <div><strong>{resultado.aciertos}</strong><span>Aciertos</span></div>
            <div><strong>{resultado.fallos}</strong><span>Fallos</span></div>
            <div><strong>{resultado.no_contestadas}</strong><span>No contestadas</span></div>
            <div><strong>{resultado.puntos.toFixed(3)}</strong><span>Puntos</span></div>
            <div><strong>{formatearTiempo(resultado.tiempo_correccion_segundos)}</strong><span>Tiempo empleado</span></div>
          </div>
        </section>
      )}

      {resultado && resultadoAcumulado && (
        <section className="card">
          <h2>Rendimiento acumulado de la convocatoria</h2>
          {resultadoAcumulado.simulacros <= 0 ? (
            <p className="muted">
              Todavía no existen pruebas corregidas para mostrar estadísticas acumuladas.
            </p>
          ) : (
            <>
              <p className="muted">
                Las tablas siguientes corresponden a todos los{" "}
                {resultadoAcumulado.tipo_prueba === "TEST" ? "tests" : "simulacros"}{" "}
                corregidos que se conservan actualmente en esta convocatoria, no
                únicamente a la prueba abierta. Si se modifica o elimina una prueba,
                los resultados se recalculan automáticamente.
              </p>

              <p>
                <strong>Datos acumulados:</strong>{" "}
                {resultadoAcumulado.simulacros}{" "}
                {resultadoAcumulado.tipo_prueba === "TEST" ? "tests" : "simulacros"} ·{" "}
                {resultadoAcumulado.preguntas} preguntas ·{" "}
                {resultadoAcumulado.contestadas} contestadas ·{" "}
                {resultadoAcumulado.no_contestadas} no contestadas.
              </p>

              <h3>Resultados acumulados por tema</h3>
              <div style={{ overflowX: "auto" }}>
                <table>
                  <thead>
                    <tr>
                      <th>Tema</th>
                      <th>Preguntas</th>
                      <th>% acumulado</th>
                      <th>Aciertos</th>
                      <th>% aciertos</th>
                      <th>Fallos</th>
                      <th>% fallos</th>
                      <th>No contestadas</th>
                    </tr>
                  </thead>
                  <tbody>
                    {resultadoAcumulado.temas.map((tema) => (
                      <tr key={`${tema.parte}-${tema.numero_tema}-${tema.titulo}`}>
                        <td>{tema.parte} {tema.numero_tema}. {tema.titulo}</td>
                        <td>{tema.preguntas}</td>
                        <td>{tema.porcentaje_convocatoria.toFixed(1)} %</td>
                        <td>{tema.aciertos}</td>
                        <td>{tema.porcentaje_aciertos.toFixed(1)} %</td>
                        <td>{tema.fallos}</td>
                        <td>{tema.porcentaje_fallos.toFixed(1)} %</td>
                        <td>{tema.no_contestadas}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="muted">
                El porcentaje acumulado indica el peso de cada tema sobre todas las
                preguntas analizadas. Los porcentajes de aciertos y fallos se calculan
                sobre el total de preguntas de ese tema.
              </p>

              <h3>Resultados acumulados por ley o norma</h3>
              <div style={{ overflowX: "auto" }}>
                <table>
                  <thead>
                    <tr>
                      <th>Ley o norma</th>
                      <th>Preguntas</th>
                      <th>% acumulado</th>
                      <th>Aciertos</th>
                      <th>% aciertos</th>
                      <th>Fallos</th>
                      <th>% fallos</th>
                      <th>No contestadas</th>
                    </tr>
                  </thead>
                  <tbody>
                    {resultadoAcumulado.normas.map((norma) => (
                      <tr key={norma.norma}>
                        <td>{norma.norma}</td>
                        <td>{norma.preguntas}</td>
                        <td>{norma.porcentaje_convocatoria.toFixed(1)} %</td>
                        <td>{norma.aciertos}</td>
                        <td>{norma.porcentaje_aciertos.toFixed(1)} %</td>
                        <td>{norma.fallos}</td>
                        <td>{norma.porcentaje_fallos.toFixed(1)} %</td>
                        <td>{norma.no_contestadas}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="muted">
                Las preguntas jurídicas se agrupan por la ley o norma congelada en
                cada prueba. Las preguntas de informática aparecen agrupadas como
                «Informática».
              </p>

              {resultadoAcumulado.seguridad.length > 0 && (
                <>
                  <h3>Resultados acumulados por nivel de seguridad</h3>
                  <div style={{ overflowX: "auto" }}>
                    <table>
                      <thead>
                        <tr>
                          <th>Seguridad</th>
                          <th>Contestadas</th>
                          <th>Aciertos</th>
                          <th>% aciertos</th>
                          <th>Fallos</th>
                          <th>% fallos</th>
                        </tr>
                      </thead>
                      <tbody>
                        {resultadoAcumulado.seguridad.map((seguridad) => (
                          <tr key={seguridad.codigo}>
                            <td>{seguridad.seguridad}</td>
                            <td>{seguridad.contestadas}</td>
                            <td>{seguridad.aciertos}</td>
                            <td>{seguridad.porcentaje_aciertos.toFixed(1)} %</td>
                            <td>{seguridad.fallos}</td>
                            <td>{seguridad.porcentaje_fallos.toFixed(1)} %</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <p className="muted">
                    Los porcentajes se calculan únicamente sobre las preguntas
                    contestadas en pruebas en las que se valoró la seguridad.
                  </p>
                </>
              )}
            </>
          )}
        </section>
      )}

      {resultado && resultadoAcumulado && resultadoAcumulado.simulacros > 0 && (
        <section className="card">
          <h2>Análisis acumulado de la convocatoria</h2>
          <p className="muted">
            El análisis utiliza todas las pruebas corregidas del mismo tipo que
            la prueba abierta y que se conservan actualmente en esta convocatoria,
            no únicamente esta corrección. Si se elimina o modifica una prueba,
            los datos se recalculan.
          </p>
          <p>
            <strong>Datos considerados:</strong>{" "}
            {resultadoAcumulado.simulacros}{" "}
            {resultadoAcumulado.tipo_prueba === "TEST" ? "tests" : "simulacros"} ·{" "}
            {resultadoAcumulado.preguntas} preguntas.
          </p>

          {analisisActual() && (
            <div style={{ marginTop: 18 }}>
              {renderAnalisisRendimiento(analisisActual()!.texto)}
            </div>
          )}

          <button
            className="secondary"
            disabled={ocupado}
            onClick={generarAnalisisRendimiento}
          >
            {ocupado && accionEnCurso === "Analizando los resultados acumulados..."
              ? "Analizando..."
              : analisisActual()
                ? "Regenerar análisis de rendimiento"
                : "Generar análisis de rendimiento"}
          </button>
        </section>
      )}

      {simulacroId === null && seccion === "SIMULACROS" && (
        <section className="card">
          <h2>Mis simulacros</h2>
          {misSimulacros.length === 0 ? (
            <p className="muted">Todavía no hay simulacros guardados.</p>
          ) : (
            <div className="saved-list">
              {misSimulacros.map((simulacro) => (
                <div className="saved-row" key={simulacro.id}>
                  <div className="saved-main">
                    <strong>
                      Nº {simulacro.numero} ·{" "}
                      {simulacro.convocatoria_codigo ?? `Convocatoria ${simulacro.convocatoria_id}`}
                    </strong>
                    <div className="muted">
                      {new Date(simulacro.fecha_generacion).toLocaleString("es-ES")} ·{" "}
                      {simulacro.total_preguntas} preguntas ·{" "}
                      {simulacro.contestadas} contestadas
                    </div>
                  </div>

                  <span
                    className={
                      simulacro.estado === "FINALIZADO"
                        ? "status status-finished"
                        : "status status-pending"
                    }
                  >
                    {simulacro.estado === "FINALIZADO"
                      ? "Corregido"
                      : "Pendiente"}
                  </span>

                  <div className="saved-actions">
                    <button
                      className="secondary"
                      disabled={ocupado}
                      onClick={() => abrirSimulacro(simulacro)}
                    >
                      {simulacro.estado === "FINALIZADO"
                        ? "Ver corrección"
                        : "Continuar"}
                    </button>
                    <button
                      className="danger"
                      disabled={ocupado}
                      onClick={() => eliminarGuardado(simulacro)}
                    >
                      Eliminar
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {simulacroId === null && seccion === "SIMULACROS" && (
        <section className="card">
          <h2>Crear simulacro</h2>

          {convocatorias.map((convocatoria) => (
            <div className="convocatoria" key={convocatoria.id}>
              <strong>{convocatoria.codigo}</strong>
              <div>
                {convocatoria.puesto} · Convocatoria {convocatoria.numero}
              </div>
              <div style={{ marginTop: 10 }}>
                <button
                  className="primary"
                  disabled={ocupado}
                  onClick={() => crear(convocatoria.id)}
                >
                  {ocupado ? "Procesando..." : "Crear simulacro"}
                </button>
              </div>
            </div>
          ))}
        </section>
      )}

      {simulacroId === null && seccion === "TESTS" && (
        <>
          <section className="card">
            <h2>Mis tests</h2>
            {misTests.length === 0 ? (
              <p className="muted">Todavía no hay tests guardados.</p>
            ) : (
              <div className="saved-list">
                {misTests.map((test) => (
                  <div className="saved-row" key={test.id}>
                    <div className="saved-main">
                      <strong>
                        Nº {test.numero} ·{" "}
                        {test.convocatoria_codigo ??
                          `Convocatoria ${test.convocatoria_id}`}
                      </strong>
                      <div className="muted">
                        {new Date(test.fecha_generacion).toLocaleString("es-ES")} ·{" "}
                        {test.total_preguntas} preguntas · {test.contestadas} contestadas
                      </div>
                    </div>
                    <span
                      className={
                        test.estado === "FINALIZADO"
                          ? "status status-finished"
                          : "status status-pending"
                      }
                    >
                      {test.estado === "FINALIZADO" ? "Corregido" : "Pendiente"}
                    </span>
                    <div className="saved-actions">
                      <button
                        className="secondary"
                        disabled={ocupado}
                        onClick={() => abrirSimulacro(test)}
                      >
                        {test.estado === "FINALIZADO"
                          ? "Ver corrección"
                          : "Continuar"}
                      </button>
                      <button
                        className="danger"
                        disabled={ocupado}
                        onClick={() => eliminarGuardado(test)}
                      >
                        Eliminar
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className="card">
            <h2>Construir test</h2>

            <label>Convocatoria</label>
            <select
              className="select"
              value={convocatoriaTestId ?? ""}
              onChange={(e) => {
                setConvocatoriaTestId(Number(e.target.value));
                setTemasSeleccionados([]);
                setNormasSeleccionadas([]);
              }}
            >
              {convocatorias.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.codigo} — {c.puesto}
                </option>
              ))}
            </select>

            <label>Número de preguntas</label>
            <input
              className="number-input"
              type="number"
              min={1}
              value={numeroPreguntasTest}
              onChange={(e) =>
                setNumeroPreguntasTest(Math.max(1, Number(e.target.value)))
              }
            />

            <h3>Generar preguntas por</h3>
            <div className="options">
              <label>
                <input
                  type="radio"
                  checked={modoTest === "TEMA"}
                  onChange={() => setModoTest("TEMA")}
                />{" "}
                Puntos del temario
              </label>
              <label>
                <input
                  type="radio"
                  checked={modoTest === "NORMA"}
                  onChange={() => setModoTest("NORMA")}
                />{" "}
                Ley o norma
              </label>
            </div>

            {modoTest === "TEMA" ? (
              <div className="selection-list">
                {temasTest.map((tema) => (
                  <label key={tema.id} className="selection-item">
                    <input
                      type="checkbox"
                      checked={temasSeleccionados.includes(tema.id)}
                      onChange={() =>
                        toggle(
                          String(tema.id),
                          temasSeleccionados.map(String),
                          (valores) =>
                            setTemasSeleccionados(valores.map(Number))
                        )
                      }
                    />
                    <span>
                      {tema.numero_tema}. {tema.parte} — {tema.titulo}
                    </span>
                  </label>
                ))}
              </div>
            ) : (
              <div className="selection-list">
                {normasTest.map((norma) => (
                  <label key={norma.norma_clave} className="selection-item">
                    <input
                      type="checkbox"
                      checked={normasSeleccionadas.includes(norma.norma_clave)}
                      onChange={() =>
                        toggle(
                          norma.norma_clave,
                          normasSeleccionadas,
                          setNormasSeleccionadas
                        )
                      }
                    />
                    <span>
                      {norma.norma_nombre}
                    </span>
                  </label>
                ))}
              </div>
            )}

            <div style={{ marginTop: 18 }}>
              <button
                className="primary"
                disabled={ocupado}
                onClick={crearTest}
              >
                {ocupado ? "Creando..." : "Crear test"}
              </button>
            </div>
          </section>
        </>
      )}

      {simulacroId !== null && !resultado && (
        <section className="card sticky-actions">
          <div className="simulacro-toolbar">
            <div>
              <strong>{tipoActivo === "TEST" ? "Test" : "Simulacro"} {simulacroId}</strong>
              <div className="muted">
                {evaluarSeguridad
                  ? "Marca respuesta y seguridad en cada pregunta contestada."
                  : "Marca la respuesta de cada pregunta."}
              </div>
            </div>
            <div className="toolbar-actions">
              <button
                className="secondary"
                disabled={ocupado}
                onClick={() => {
                  const volverA = tipoActivo;
                  limpiarSimulacro();
                  setSeccion(volverA === "TEST" ? "TESTS" : "SIMULACROS");
                  setMensaje("");
                  setError("");
                  window.scrollTo({ top: 0, behavior: "smooth" });
                }}
              >
                {tipoActivo === "TEST" ? "Volver a mis tests" : "Volver a mis simulacros"}
              </button>
              <button className="secondary" disabled={ocupado} onClick={guardar}>
                {ocupado && accionEnCurso?.startsWith("Guardando respuestas")
                  ? "Guardando..."
                  : "Guardar respuestas"}
              </button>
              <button className="primary calificar-button" disabled={ocupado} onClick={calificar}>
                {ocupado && accionEnCurso?.includes("calificando")
                  ? "Calificando..."
                  : `Calificar ${tipoActivo === "TEST" ? "test" : "simulacro"}`}
              </button>
            </div>
          </div>
        </section>
      )}

      {simulacroId !== null && !resultado && (
        <section className="card">
          <label style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 10 }}>
            <input
              type="checkbox"
              checked={mostrarCronometro}
              onChange={(event) => setMostrarCronometro(event.target.checked)}
            />
            <span>Mostrar cronómetro</span>
          </label>
          <p className="muted" style={{ marginTop: 0 }}>
            El tiempo se registra igualmente aunque el cronómetro permanezca oculto.
          </p>

          {mostrarCronometro && inicioCorreccionMs !== null && (
            <CronometroCorreccion
              inicioMs={inicioCorreccionMs}
              tiempoPrevio={tiempoPrevioCorreccion}
            />
          )}

          <label style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 18 }}>
            <input
              type="checkbox"
              checked={evaluarSeguridad}
              onChange={(event) =>
                cambiarEvaluacionSeguridad(event.target.checked)
              }
            />
            <span>Evaluar seguridad en las respuestas</span>
          </label>

          {preguntas.map((pregunta) => {
            const local = respuestas[pregunta.simulacro_pregunta_id] ?? {
              respuesta: null,
              seguridad: null,
            };

            const opciones = [
              ["A", pregunta.opcion_a],
              ["B", pregunta.opcion_b],
              ["C", pregunta.opcion_c],
              ["D", pregunta.opcion_d],
            ];

            return (
              <article
                className="question"
                key={pregunta.simulacro_pregunta_id}
              >
                <strong>
                  {pregunta.orden}. {pregunta.parte_nombre ?? ""}
                </strong>
                <p>{pregunta.enunciado}</p>

                <div className="answer-options">
                  {opciones.map(([letra, texto]) => (
                    <label className="answer-line" key={letra}>
                      <input
                        type="radio"
                        name={`respuesta-${pregunta.simulacro_pregunta_id}`}
                        checked={local.respuesta === letra}
                        onChange={() =>
                          establecerRespuesta(
                            pregunta.simulacro_pregunta_id,
                            letra
                          )
                        }
                      />
                      <span>
                        <strong>{letra}.</strong> {texto}
                      </span>
                    </label>
                  ))}
                  <button
                    type="button"
                    className="link-button"
                    onClick={() =>
                      establecerRespuesta(
                        pregunta.simulacro_pregunta_id,
                        null
                      )
                    }
                  >
                    Dejar en blanco
                  </button>
                </div>

                {evaluarSeguridad && local.respuesta && (
                  <div className="security-box">
                    <span>Seguridad:</span>
                    {SEGURIDADES.map(([valor, etiqueta]) => (
                      <label key={valor}>
                        <input
                          type="radio"
                          name={`seguridad-${pregunta.simulacro_pregunta_id}`}
                          checked={local.seguridad === valor}
                          onChange={() =>
                            establecerSeguridad(
                              pregunta.simulacro_pregunta_id,
                              valor
                            )
                          }
                        />{" "}
                        {etiqueta}
                      </label>
                    ))}
                  </div>
                )}
              </article>
            );
          })}

          <div className="row final-actions">
            <button className="secondary" disabled={ocupado} onClick={guardar}>
              {ocupado && accionEnCurso?.startsWith("Guardando respuestas")
                ? "Guardando..."
                : "Guardar respuestas"}
            </button>
            <button className="primary calificar-button" disabled={ocupado} onClick={calificar}>
              {ocupado && accionEnCurso?.includes("calificando")
                ? "Calificando..."
                : `Calificar ${tipoActivo === "TEST" ? "test" : "simulacro"}`}
            </button>
          </div>
        </section>
      )}

      {resultado && (
        <section className="card">
          <div className="row space-between">
            <h2>Corrección</h2>
            <button
              className="secondary"
              onClick={() => {
                limpiarSimulacro();
                setMensaje("");
                setError("");
                window.scrollTo({ top: 0, behavior: "smooth" });
              }}
            >
              {tipoActivo === "TEST" ? "Volver a mis tests" : "Volver a mis simulacros"}
            </button>
          </div>

          {correccion.map((pregunta) => (
            <article
              className={`question correction ${pregunta.resultado.toLowerCase()}`}
              key={pregunta.simulacro_pregunta_id}
            >
              <div className="row space-between">
                <strong>
                  {pregunta.orden}. {pregunta.parte_nombre ?? ""}
                </strong>
                <span className="result-label">
                  {pregunta.resultado === "ACIERTO"
                    ? "Acierto"
                    : pregunta.resultado === "FALLO"
                    ? "Fallo"
                    : "No contestada"}
                </span>
              </div>

              <p>{pregunta.enunciado}</p>
              <p className="option">A. {pregunta.opcion_a}</p>
              <p className="option">B. {pregunta.opcion_b}</p>
              <p className="option">C. {pregunta.opcion_c}</p>
              <p className="option">D. {pregunta.opcion_d}</p>

              <div className="correction-detail">
                <span>
                  Tu respuesta: <strong>{pregunta.respuesta_usuario ?? "—"}</strong>
                </span>
                <span>
                  Correcta: <strong>{pregunta.respuesta_correcta}</strong>
                </span>
                {pregunta.seguridad_usuario && (
                  <span>
                    Seguridad:{" "}
                    <strong>
                      {pregunta.seguridad_usuario.replaceAll("_", " ")}
                    </strong>
                  </span>
                )}
              </div>
            </article>
          ))}
        </section>
      )}
    </main>
  );
}
