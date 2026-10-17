from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path, Query

from backend.app.data import published
from backend.app.data.common import RUN_ID_RE, Db, Page, PageSize, User, strict_params

router = APIRouter(tags=["backtests"])


@router.get("/backtests", dependencies=[Depends(strict_params("run_id"))])
def list_backtests(_: User, db: Db, page: Page = 1, page_size: PageSize = 50,
                   run_id: Annotated[str | None, Query(pattern=RUN_ID_RE)] = None):
    return published.list_backtests(db, run_id, page, page_size)


@router.get("/backtests/{backtest_id}", dependencies=[Depends(strict_params("view"))])
def get_backtest(backtest_id: Annotated[str, Path(pattern=RUN_ID_RE)], _: User, db: Db,
                 view: Literal["predictive", "simulation", "all"] = "all"):
    return published.get_backtest(db, backtest_id, view)
