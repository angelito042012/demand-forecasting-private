from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from backend.app.data import inventory
from backend.app.data.common import (
    RUN_ID_RE,
    Db,
    Page,
    PageSize,
    User,
    safe_text,
    strict_params,
)

router = APIRouter(tags=["inventory"])


@router.get("/inventory/reported", dependencies=[Depends(strict_params("snapshot_id", "q", "view", "sort"))])
def reported_inventory(_: User, db: Db, page: Page = 1, page_size: PageSize = 50,
                       snapshot_id: Annotated[str | None, Query(pattern=RUN_ID_RE)] = None,
                       q: Annotated[str | None, Query(max_length=100)] = None,
                       view: Literal["all", "with_stock", "no_stock"] = "all",
                       sort: Literal["producto_id", "-producto_id", "producto", "-producto", "libre",
                                     "-libre"] | None = None):
    return inventory.get_reported(db, snapshot_id=snapshot_id, q=safe_text(q, "q"), view=view, sort=sort,
                                  page=page, page_size=page_size)


@router.get("/inventory/reported/snapshots", dependencies=[Depends(strict_params())])
def reported_snapshots(_: User, db: Db, page: Page = 1, page_size: PageSize = 50):
    return inventory.list_snapshots(db, page, page_size)
