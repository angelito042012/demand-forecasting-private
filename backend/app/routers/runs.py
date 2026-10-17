from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, Path
from pydantic import BaseModel, ConfigDict

from backend.app import uploads
from backend.app.auth.deps import CurrentUser, require_admin, require_csrf
from backend.app.data import jobs as jobs_repo
from backend.app.data import published
from backend.app.data.common import RUN_ID_RE, Db, Page, PageSize, User, strict_params
from backend.app.errors import ApiError

router = APIRouter(tags=["runs"])


class RunRequest(BaseModel):
    """Unico contenido que el navegador puede enviar; la politica la fija el servidor."""
    model_config = ConfigDict(extra="forbid")
    origin: date
    horizon_days: int = 21
    method: Literal["promedio_28"] = "promedio_28"


@router.get("/runs", dependencies=[Depends(strict_params("status"))])
def list_runs(_: User, db: Db, page: Page = 1, page_size: PageSize = 50,
              status: Literal["completed", "superseded"] | None = None):
    return published.list_runs(db, page, page_size, status)


@router.get("/runs/options", dependencies=[Depends(strict_params())])
def run_options(_: User):
    pol = uploads.load_config()["politica_desarrollo"]
    return {"origin_min": pol["origen_minimo"], "origin_max": pol["origen_maximo"],
            "origin_default": pol["origen_demostracion"], "horizon_max": pol["horizonte_maximo"],
            "methods": list(pol["metodos_permitidos"]), "development_policy": True}


@router.post("/runs", status_code=202, dependencies=[Depends(require_admin)])
def create_run(body: RunRequest, db: Db, user: Annotated[CurrentUser, Depends(require_csrf)],
               idempotency_key: Annotated[str | None, Header(max_length=200)] = None):
    """Encola `generate_run`. No genera ni publica en la peticion."""
    cfg = uploads.load_config()
    pol = cfg["politica_desarrollo"]
    lo, hi = date.fromisoformat(pol["origen_minimo"]), date.fromisoformat(pol["origen_maximo"])
    if not lo <= body.origin <= hi:
        raise ApiError(422, "CORTE_FUERA_DE_RANGO",
                       f"El origen debe estar entre {lo.isoformat()} y {hi.isoformat()}.")
    if not 1 <= body.horizon_days <= int(pol["horizonte_maximo"]):
        raise ApiError(422, "CORTE_FUERA_DE_RANGO",
                       f"El horizonte debe estar entre 1 y {pol['horizonte_maximo']} días.")
    if body.method not in pol["metodos_permitidos"]:
        raise ApiError(422, "ENTRADA_INVALIDA", "Método no permitido.")
    job, created = jobs_repo.enqueue_generate(
        db, origin=body.origin, horizon_days=body.horizon_days, method=body.method,
        generator=cfg["generador"]["version"], idempotency_header=idempotency_key, created_by=user.username)
    return {"job_id": job["job_id"], "status": job["status"], "origin": body.origin.isoformat(),
            "horizon_days": body.horizon_days, "method": body.method, "reused": not created}


@router.get("/runs/{run_id}", dependencies=[Depends(strict_params())])
def get_run(run_id: Annotated[str, Path(pattern=RUN_ID_RE)], _: User, db: Db):
    return published.get_run(db, run_id)
