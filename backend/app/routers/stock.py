"""T20 §3 — API de la existencia reconstruida. Solo lectura: lector y administrador."""
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from backend.app.data import stock
from backend.app.data.common import (
    RUN_ID_RE,
    Db,
    Page,
    PageSize,
    User,
    safe_text,
    strict_params,
)

router = APIRouter(tags=["stock"])


@router.get("/stock", dependencies=[Depends(strict_params("snapshot_id", "q", "view", "sort"))])
def get_stock(_: User, db: Db, page: Page = 1, page_size: PageSize = 50,
              snapshot_id: Annotated[str | None, Query(pattern=RUN_ID_RE)] = None,
              q: Annotated[str | None, Query(max_length=100)] = None,
              view: Literal["todos", "discrepancias"] = "todos",
              sort: Literal["producto_id", "-producto_id", "producto", "-producto", "libre", "-libre"] | None = None):
    return stock.get_stock(db, snapshot_id=snapshot_id, q=safe_text(q, "q"), view=view, sort=sort,
                           page=page, page_size=page_size)
