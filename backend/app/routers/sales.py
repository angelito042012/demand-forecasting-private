from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from backend.app.data import observed
from backend.app.data.common import Db, User, safe_text, strict_params

router = APIRouter(tags=["sales"])


@router.get("/sales/summary", dependencies=[Depends(strict_params("from", "to", "group_by", "categoria"))])
def sales_summary(_: User, db: Db, from_: Annotated[date | None, Query(alias="from")] = None,
                  to: date | None = None, group_by: Literal["day", "month", "category"] = "month",
                  categoria: Annotated[str | None, Query(max_length=100)] = None):
    return observed.sales_summary(db, from_, to, group_by, safe_text(categoria, "categoria"))
