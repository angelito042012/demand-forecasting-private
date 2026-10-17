from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path

from backend.app.data import published
from backend.app.data.common import RUN_ID_RE, Db, Page, PageSize, User, strict_params

router = APIRouter(tags=["runs"])


@router.get("/runs", dependencies=[Depends(strict_params("status"))])
def list_runs(_: User, db: Db, page: Page = 1, page_size: PageSize = 50,
              status: Literal["completed"] = "completed"):
    return published.list_runs(db, page, page_size)


@router.get("/runs/{run_id}", dependencies=[Depends(strict_params())])
def get_run(run_id: Annotated[str, Path(pattern=RUN_ID_RE)], _: User, db: Db):
    return published.get_run(db, run_id)
