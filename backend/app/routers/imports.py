from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from backend.app.data import observed
from backend.app.data.common import (
    HEX32_RE,
    MES_RE,
    Db,
    Page,
    PageSize,
    User,
    strict_params,
)

router = APIRouter(tags=["imports"])


@router.get("/imports", dependencies=[Depends(strict_params("mes"))])
def list_imports(_: User, db: Db, page: Page = 1, page_size: PageSize = 50,
                 mes: Annotated[str | None, Query(pattern=MES_RE)] = None):
    return observed.list_imports(db, mes, page, page_size)


@router.get("/imports/{import_id}", dependencies=[Depends(strict_params())])
def get_import(import_id: Annotated[str, Path(pattern=HEX32_RE)], _: User, db: Db):
    return observed.get_import(db, import_id)
