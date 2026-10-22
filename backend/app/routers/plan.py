"""T19 §6 — API del plan de compra. Lectura: lector y administrador. Escritura: solo administrador con sesion + CSRF."""
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from pydantic import BaseModel, ConfigDict, StrictInt

from backend.app.auth.deps import CurrentUser, require_admin, require_csrf
from backend.app.data import plan
from backend.app.data.common import (
    MES_RE,
    RUN_ID_RE,
    SKU_RE,
    Db,
    Page,
    PageSize,
    User,
    safe_text,
    strict_params,
)

router = APIRouter(tags=["plan"])
Status = Annotated[str | None, Query(pattern=r"^(OK|LLEGA_TARDE|NO_LLEGA_A_TIEMPO|NO_CALCULABLE)$")]


class PendingIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    producto_id: str
    units: StrictInt
    arrival_date: str | None = None
    nature: str = "ASUMIDA"


class PlanRequest(BaseModel):
    """Unico contenido que el navegador puede enviar; las reglas y limites los fija el servidor."""
    model_config = ConfigDict(extra="forbid")
    month: str
    decision_date: str
    lead_days: list[StrictInt]
    reserve_days: StrictInt
    min_order: StrictInt
    order_multiple: StrictInt
    pending_orders: list[PendingIn] = []


@router.get("/plans/inputs", dependencies=[Depends(strict_params())])
def plan_inputs(_: User, db: Db):
    return plan.inputs(db)


@router.get("/plans", dependencies=[Depends(strict_params("month"))])
def list_plans(_: User, db: Db, page: Page = 1, page_size: PageSize = 50,
               month: Annotated[str | None, Query(pattern=MES_RE)] = None):
    return plan.list_plans(db, month, page, page_size)


@router.post("/plans", status_code=202, dependencies=[Depends(require_admin), Depends(strict_params())])
def create_plan(body: PlanRequest, db: Db, user: Annotated[CurrentUser, Depends(require_csrf)]):
    """Encola `generate_plan`; el calculo lo hace el worker, no la peticion."""
    return plan.create_plan(db, body.model_dump(), user.username)


@router.get("/plans/{plan_id}", dependencies=[Depends(strict_params())])
def get_plan(plan_id: Annotated[str, Path(pattern=RUN_ID_RE)], _: User, db: Db):
    return plan.get_plan(db, plan_id)


@router.get("/plans/{plan_id}/results", dependencies=[Depends(strict_params("q", "status", "sort"))])
def get_results(plan_id: Annotated[str, Path(pattern=RUN_ID_RE)], _: User, db: Db, page: Page = 1,
                page_size: PageSize = 50, q: Annotated[str | None, Query(max_length=100)] = None,
                status: Status = None, sort: Annotated[str | None, Query(max_length=30)] = None):
    return plan.get_results(db, plan_id, q=safe_text(q, "q"), status=status, sort=sort, page=page, page_size=page_size)


@router.get("/plans/{plan_id}/results/{producto_id}", dependencies=[Depends(strict_params())])
def get_result(plan_id: Annotated[str, Path(pattern=RUN_ID_RE)], producto_id: Annotated[str, Path(pattern=SKU_RE)],
               _: User, db: Db):
    return plan.get_result(db, plan_id, producto_id)


@router.get("/plans/{plan_id}/compare/{other_id}", dependencies=[Depends(strict_params())])
def compare_plans(plan_id: Annotated[str, Path(pattern=RUN_ID_RE)], other_id: Annotated[str, Path(pattern=RUN_ID_RE)],
                  _: User, db: Db):
    """Comparacion producto a producto de dos planes completados (lector y administrador)."""
    return plan.compare(db, plan_id, other_id)
