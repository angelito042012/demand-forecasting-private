from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path

from backend.app.auth.deps import CurrentUser, require_admin
from backend.app.data import jobs as jobs_repo
from backend.app.data.common import HEX32_RE, Db, Page, PageSize, strict_params

router = APIRouter(tags=["jobs"])
Admin = Annotated[CurrentUser, Depends(require_admin)]


@router.get("/jobs", dependencies=[Depends(strict_params("status", "type"))])
def list_jobs(_: Admin, db: Db, page: Page = 1, page_size: PageSize = 50,
              status: Literal["queued", "running", "completed", "failed"] | None = None,
              type: Literal["import_excel", "generate_run", "generate_plan"] | None = None):
    return jobs_repo.list_jobs(db, page, page_size, status, type)


@router.get("/jobs/{job_id}", dependencies=[Depends(strict_params())])
def get_job(job_id: Annotated[str, Path(pattern=HEX32_RE)], _: Admin, db: Db):
    return jobs_repo.get_job(db, job_id)
