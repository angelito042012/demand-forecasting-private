from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from backend.app.data import published
from backend.app.data.common import (
    RUN_ID_RE,
    SKU_RE,
    Db,
    Page,
    PageSize,
    User,
    safe_text,
    strict_params,
)

router = APIRouter(tags=["forecasts"])


@router.get("/forecasts", dependencies=[Depends(strict_params(
    "run_id", "level", "sku", "categoria", "cohorte", "from", "to", "sort"))])
def list_forecasts(_: User, db: Db, page: Page = 1, page_size: PageSize = 50,
                   run_id: Annotated[str | None, Query(pattern=RUN_ID_RE)] = None,
                   level: Literal["sku", "categoria"] = "sku",
                   sku: Annotated[str | None, Query(pattern=SKU_RE)] = None,
                   categoria: Annotated[str | None, Query(max_length=100)] = None,
                   cohorte: Literal["primaria", "historia_corta"] | None = None,
                   from_: Annotated[date | None, Query(alias="from")] = None, to: date | None = None,
                   sort: Annotated[str | None, Query(max_length=20)] = None):
    return published.list_forecasts(db, run_id=run_id, level=level, sku=sku,
                                    categoria=safe_text(categoria, "categoria"), cohorte=cohorte,
                                    frm=from_, to=to, sort=sort, page=page, page_size=page_size)
