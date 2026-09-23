from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from psycopg.rows import dict_row

from app.agent_auth import AgenteAutenticado, exigir_agente
from app.postgres import conectar_postgres


router = APIRouter(prefix="/api/v1/agent", tags=["agent"])


class HeartbeatRequest(BaseModel):
    version: str | None = Field(default=None, max_length=80)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EstadoJobRequest(BaseModel):
    estado: str
    resultado: dict[str, Any] | None = None
    error_texto: str | None = Field(default=None, max_length=10000)


ESTADOS_AGENTE = {"EJECUTANDO", "ESPERANDO_CONFIRMACION", "COMPLETADO", "ERROR", "INTERRUMPIDO"}


@router.post("/heartbeat")
def heartbeat(
    payload: HeartbeatRequest,
    agente: AgenteAutenticado = Depends(exigir_agente),
) -> dict[str, Any]:
    ahora = datetime.now(timezone.utc)
    with conectar_postgres() as con, con.cursor() as cur:
        cur.execute(
            """
            UPDATE public.admin_agents
            SET ultimo_heartbeat_at=%s, version=%s, metadata=%s::jsonb, updated_at=%s
            WHERE id=%s AND activo=true
            """,
            (ahora, payload.version, __import__("json").dumps(payload.metadata), ahora, agente.id),
        )
    return {"ok": True, "agente_id": str(agente.id), "heartbeat_at": ahora}


@router.post("/jobs/claim")
def reclamar_job(
    agente: AgenteAutenticado = Depends(exigir_agente),
) -> dict[str, Any] | None:
    ahora = datetime.now(timezone.utc)
    with conectar_postgres() as con, con.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT id
            FROM public.admin_jobs
            WHERE estado='PENDIENTE'
            ORDER BY creado_at
            LIMIT 1
            FOR UPDATE SKIP LOCKED
            """
        )
        pendiente = cur.fetchone()
        if pendiente is None:
            return None

        cur.execute(
            """
            UPDATE public.admin_jobs
            SET estado='RECOGIDO', agente_id=%s, recogido_at=%s, updated_at=%s
            WHERE id=%s AND estado='PENDIENTE'
            RETURNING id, tipo, parametros, estado, requiere_confirmacion, confirmado_at, resultado, creado_at
            """,
            (agente.id, ahora, ahora, pendiente["id"]),
        )
        job = cur.fetchone()
        cur.execute(
            """
            INSERT INTO public.admin_job_events
                (job_id, evento, actor_tipo, agente_id, detalle)
            VALUES (%s, 'RECOGIDO', 'AGENTE', %s, '{}'::jsonb)
            """,
            (job["id"], agente.id),
        )

    return {**job, "id": str(job["id"])}


@router.post("/jobs/{job_id}/estado")
def actualizar_estado_job(
    job_id: UUID,
    payload: EstadoJobRequest,
    agente: AgenteAutenticado = Depends(exigir_agente),
) -> dict[str, Any]:
    nuevo = payload.estado.strip().upper()
    if nuevo not in ESTADOS_AGENTE:
        raise HTTPException(status_code=400, detail="Estado no permitido para el agente.")

    ahora = datetime.now(timezone.utc)
    with conectar_postgres() as con, con.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT id, estado, agente_id, requiere_confirmacion, confirmado_at
            FROM public.admin_jobs
            WHERE id=%s
            FOR UPDATE
            """,
            (job_id,),
        )
        job = cur.fetchone()
        if job is None:
            raise HTTPException(status_code=404, detail="Trabajo no encontrado.")
        if job["agente_id"] != agente.id:
            raise HTTPException(status_code=403, detail="Trabajo asignado a otro agente.")

        anterior = job["estado"]

        # ACK idempotente de estados terminales: si el agente envió el
        # resultado y perdió la respuesta HTTP, puede repetir la notificación
        # sin reejecutar el trabajo ni crear un segundo evento.
        terminales = {"COMPLETADO", "ERROR", "INTERRUMPIDO"}
        # ACK idempotente de EJECUTANDO: si el backend aceptó el inicio pero
        # se perdió la respuesta HTTP, el agente puede repetir exactamente
        # esa notificación. Esto NO devuelve el job a PENDIENTE ni autoriza
        # una segunda ejecución local.
        if anterior == nuevo and nuevo == "EJECUTANDO":
            return {
                "id": str(job["id"]),
                "estado": anterior,
                "idempotente": True,
            }
        if anterior == nuevo and nuevo in terminales:
            return {
                "id": str(job["id"]),
                "estado": anterior,
                "idempotente": True,
            }

        permitidas = {
            "RECOGIDO": {"EJECUTANDO", "ERROR", "INTERRUMPIDO"},
            "EJECUTANDO": {"ESPERANDO_CONFIRMACION", "COMPLETADO", "ERROR", "INTERRUMPIDO"},
        }
        if nuevo == "ESPERANDO_CONFIRMACION":
            if not job["requiere_confirmacion"]:
                raise HTTPException(status_code=409, detail="El trabajo no requiere confirmación.")
            if job["confirmado_at"] is not None:
                raise HTTPException(status_code=409, detail="El trabajo ya fue confirmado; no puede volver a revisión.")
            if payload.resultado is None:
                raise HTTPException(status_code=400, detail="La revisión debe incluir un resultado antes de solicitar confirmación.")
        if nuevo not in permitidas.get(anterior, set()):
            raise HTTPException(
                status_code=409,
                detail=f"Transición no permitida: {anterior} -> {nuevo}.",
            )

        iniciado_at = ahora if nuevo == "EJECUTANDO" else None
        finalizado_at = ahora if nuevo in {"COMPLETADO", "ERROR", "INTERRUMPIDO"} else None
        cur.execute(
            """
            UPDATE public.admin_jobs
            SET estado=%s,
                resultado=COALESCE(%s::jsonb, resultado),
                error_texto=COALESCE(%s, error_texto),
                iniciado_at=COALESCE(iniciado_at, %s),
                finalizado_at=COALESCE(finalizado_at, %s),
                updated_at=%s
            WHERE id=%s
            RETURNING id, estado, iniciado_at, finalizado_at
            """,
            (
                nuevo,
                __import__("json").dumps(payload.resultado) if payload.resultado is not None else None,
                payload.error_texto,
                iniciado_at,
                finalizado_at,
                ahora,
                job_id,
            ),
        )
        actualizado = cur.fetchone()
        cur.execute(
            """
            INSERT INTO public.admin_job_events
                (job_id, evento, actor_tipo, agente_id, detalle)
            VALUES (%s, %s, 'AGENTE', %s, '{}'::jsonb)
            """,
            (job_id, nuevo, agente.id),
        )

    return {**actualizado, "id": str(actualizado["id"])}
