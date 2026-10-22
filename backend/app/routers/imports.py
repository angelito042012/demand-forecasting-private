from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request
from fastapi.concurrency import run_in_threadpool

from backend.app import uploads
from backend.app.auth.deps import CurrentUser, require_admin, require_csrf_multipart
from backend.app.data import jobs as jobs_repo
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
from backend.app.errors import ApiError

router = APIRouter(tags=["imports"])


@router.get("/imports", dependencies=[Depends(strict_params("mes"))])
def list_imports(_: User, db: Db, page: Page = 1, page_size: PageSize = 50,
                 mes: Annotated[str | None, Query(pattern=MES_RE)] = None):
    return observed.list_imports(db, mes, page, page_size)


@router.post("/imports", status_code=202, dependencies=[Depends(require_admin)],
             openapi_extra={"requestBody": {"required": True, "content": {"multipart/form-data": {"schema": {
                 "type": "object", "required": ["file"],
                 "properties": {"file": {"type": "string", "format": "binary"}}}}}}})
async def upload_import(request: Request, db: Db,
                        user: Annotated[CurrentUser, Depends(require_csrf_multipart)],
                        policy: Annotated[uploads.UploadPolicy, Depends(uploads.get_upload_policy)]):
    """Sube un .xlsx mensual y encola `import_excel`. No ejecuta el importador."""
    uploads.check_declared_length(request.headers.get("content-length"), policy)
    form = await request.form(max_files=1, max_fields=4)
    try:
        file = form.get("file")
        if file is None or not hasattr(file, "read"):
            raise ApiError(422, "ENTRADA_INVALIDA", "Falta el campo de archivo «file».")
        name = getattr(file, "filename", "") or ""
        if not name.lower().endswith(policy.extension):
            raise ApiError(415, "FORMATO_NO_SOPORTADO", "Solo se aceptan archivos con extensión .xlsx.")
        label = uploads.sanitize_label(name)
        tmp, sha256, size = await uploads.save_upload(file, policy)
    finally:
        await form.close()
    final, month = await run_in_threadpool(uploads.validate_and_store, tmp, sha256, policy)
    await run_in_threadpool(uploads.persist_to_store, db, final, sha256, size)
    job, created = await run_in_threadpool(
        lambda: jobs_repo.enqueue_import(db, sha256=sha256, size_bytes=size, month=month, label=label,
                                         upload_name=final.name, created_by=user.username))
    return {"job_id": job["job_id"], "status": job["status"],
            "upload": {"sha256_short": sha256[:12], "size_bytes": size, "month": month, "label": label},
            "reused": not created}


@router.get("/imports/{import_id}", dependencies=[Depends(strict_params())])
def get_import(import_id: Annotated[str, Path(pattern=HEX32_RE)], _: User, db: Db):
    return observed.get_import(db, import_id)
