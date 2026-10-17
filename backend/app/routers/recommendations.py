from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path, Query

from backend.app.data import published
from backend.app.data.common import (
    ALMACEN_RE,
    RUN_ID_RE,
    SKU_RE,
    Db,
    Page,
    PageSize,
    User,
    safe_text,
    strict_params,
)

router = APIRouter(tags=["recommendations"])


@router.get("/recommendations", dependencies=[Depends(strict_params(
    "run_id", "categoria", "sku", "status", "only_orders", "sort"))])
def list_recommendations(_: User, db: Db, page: Page = 1, page_size: PageSize = 50,
                         run_id: Annotated[str | None, Query(pattern=RUN_ID_RE)] = None,
                         categoria: Annotated[str | None, Query(max_length=100)] = None,
                         sku: Annotated[str | None, Query(pattern=SKU_RE)] = None,
                         status: Literal["ok", "sin_snapshot"] | None = None,
                         only_orders: bool = False,
                         sort: Annotated[str | None, Query(max_length=20)] = None):
    return published.list_recommendations(db, run_id=run_id, categoria=safe_text(categoria, "categoria"),
                                          sku=sku, status=status, only_orders=only_orders, sort=sort,
                                          page=page, page_size=page_size)


@router.get("/recommendations/{sku}", dependencies=[Depends(strict_params("run_id", "almacen"))])
def get_recommendation(sku: Annotated[str, Path(pattern=SKU_RE)], _: User, db: Db,
                       run_id: Annotated[str | None, Query(pattern=RUN_ID_RE)] = None,
                       almacen: Annotated[str, Query(pattern=ALMACEN_RE)] = "1"):
    return published.get_recommendation(db, sku, run_id, almacen)
