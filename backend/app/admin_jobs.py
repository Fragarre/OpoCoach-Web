from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from psycopg import errors
from psycopg.rows import dict_row

from app.auth import UsuarioAutenticado, exigir_admin
from app.postgres import conectar_postgres


router = APIRouter(prefix="/api/v1/admin/jobs", tags=["admin-jobs"])

# Primera operación permitida. La allowlist crecerá de forma explícita,
# nunca aceptando nombres de comandos o shell enviados por el navegador.
TIPOS_PERMITIDOS = {
    "VALIDACION_COMPLETA",
    "AUDITORIA_BD",
    "AUDITORIA_BANCOS_SELECCION",
    "AUDITORIA_ESTRUCTURA_BANCO",
    "AUDITORIA_MATERIALES_ESTUDIO",
    "AUDITORIA_CORPUS_TEMARIO",
    "AUDITORIA_ESQUEMA_OBSOLETO",
    "INVENTARIO_DENOMINACIONES_NORMAS",
    "AUDITORIA_FUNCIONAL_BANCO",
    "AUDITORIA_CONSISTENCIA_GLOBAL",
}

TIPOS_CON_CONVOCATORIA = {
    "AUDITORIA_FUNCIONAL_BANCO",
    "AUDITORIA_CONSISTENCIA_GLOBAL",
}


class CrearJobRequest(BaseModel):
    tipo: str = Field(min_length=1, max_length=80)
    parametros: dict[str, Any] = Field(default_factory=dict)


def _serializar(row: dict[str, Any]) -> dict[str, Any]:
    return {
        **row,
        "id": str(row["id"]),
        "solicitado_por": str(row["solicitado_por"]),
        "agente_id": str(row["agente_id"]) if row.get("agente_id") else None,
        "confirmado_por": str(row["confirmado_por"]) if row.get("confirmado_por") else None,
    }


@router.get("")
def listar_jobs(
    limite: int = 50,
    _: UsuarioAutenticado = Depends(exigir_admin),
) -> list[dict[str, Any]]:
    limite = max(1, min(limite, 200))
    with conectar_postgres() as con, con.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT *
            FROM public.admin_jobs
            ORDER BY creado_at DESC
            LIMIT %s
            """,
            (limite,),
        )
        return [_serializar(row) for row in cur.fetchall()]


@router.get("/{job_id}")
def obtener_job(
    job_id: UUID,
    _: UsuarioAutenticado = Depends(exigir_admin),
) -> dict[str, Any]:
    with conectar_postgres() as con, con.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT * FROM public.admin_jobs WHERE id=%s", (job_id,))
        job = cur.fetchone()
        if job is None:
            raise HTTPException(status_code=404, detail="Trabajo no encontrado.")

        cur.execute(
            """
            SELECT id, evento, actor_tipo, actor_usuario_id, agente_id, detalle, created_at
            FROM public.admin_job_events
            WHERE job_id=%s
            ORDER BY id
            """,
            (job_id,),
        )
        eventos = []
        for row in cur.fetchall():
            eventos.append(
                {
                    **row,
                    "actor_usuario_id": str(row["actor_usuario_id"]) if row["actor_usuario_id"] else None,
                    "agente_id": str(row["agente_id"]) if row["agente_id"] else None,
                }
            )

    return {**_serializar(job), "eventos": eventos}


@router.post("", status_code=201)
def crear_job(
    payload: CrearJobRequest,
    usuario: UsuarioAutenticado = Depends(exigir_admin),
) -> dict[str, Any]:
    tipo = payload.tipo.strip().upper()
    if tipo not in TIPOS_PERMITIDOS:
        raise HTTPException(status_code=400, detail="Tipo de trabajo no permitido.")

    if tipo in TIPOS_CON_CONVOCATORIA:
        if set(payload.parametros) != {"convocatoria_id"}:
            raise HTTPException(
                status_code=400,
                detail=f"{tipo} requiere únicamente convocatoria_id.",
            )
        convocatoria_id = payload.parametros.get("convocatoria_id")
        if isinstance(convocatoria_id, bool) or not isinstance(convocatoria_id, int) or convocatoria_id <= 0:
            raise HTTPException(
                status_code=400,
                detail="convocatoria_id debe ser un entero positivo.",
            )
    elif payload.parametros:
        raise HTTPException(
            status_code=400,
            detail=f"{tipo} no admite parámetros.",
        )

    # Estas operaciones son de diagnóstico y no modifican la base de datos.
    requiere_confirmacion = False

    try:
        with conectar_postgres() as con, con.cursor(row_factory=dict_row) as cur:
            # Comprobación legible para el caso normal. El índice único parcial
            # uq_admin_jobs_unico_activo es la garantía definitiva ante carreras.
            cur.execute(
                """
                SELECT id
                FROM public.admin_jobs
                WHERE estado IN ('PENDIENTE','RECOGIDO','EJECUTANDO','ESPERANDO_CONFIRMACION')
                LIMIT 1
                """
            )
            existente = cur.fetchone()
            if existente is not None:
                raise HTTPException(
                    status_code=409,
                    detail=f"Ya existe un trabajo activo: {existente['id']}.",
                )

            cur.execute(
                """
                INSERT INTO public.admin_jobs
                    (tipo, parametros, solicitado_por, requiere_confirmacion)
                VALUES (%s, %s::jsonb, %s, %s)
                RETURNING *
                """,
                (tipo, json.dumps(payload.parametros), usuario.id, requiere_confirmacion),
            )
            job = cur.fetchone()

            cur.execute(
                """
                INSERT INTO public.admin_job_events
                    (job_id, evento, actor_tipo, actor_usuario_id, detalle)
                VALUES (%s, 'CREADO', 'USUARIO', %s, '{}'::jsonb)
                """,
                (job["id"], usuario.id),
            )
    except errors.UniqueViolation as exc:
        raise HTTPException(
            status_code=409,
            detail="Ya existe un trabajo administrativo activo.",
        ) from exc

    return _serializar(job)
