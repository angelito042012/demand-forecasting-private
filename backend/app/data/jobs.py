"""Trabajos (T10 §2-3): encolado desde la API y lectura saneada. La API nunca ejecuta el trabajo."""
from __future__ import annotations

import re
from datetime import date, datetime

from backend.app.errors import ApiError, page_response
from pipeline.jobs import queue
from pipeline.jobs.keys import generate_run_key

from .common import HEX32_RE, RUN_ID_RE, iso_utc

_ID = re.compile(HEX32_RE)
_RUN = re.compile(RUN_ID_RE)
SORT = [("created_at", -1), ("job_id", 1)]


def _clean(value):
    """Fechas a ISO UTC en cualquier nivel del documento publico."""
    if isinstance(value, datetime):
        return iso_utc(value)
    if isinstance(value, dict):
        return {str(k): _clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(v) for v in value]
    return value


def links_for(result) -> dict:
    links: dict = {}
    if isinstance(result, dict):
        iid, rid = result.get("import_id"), result.get("run_id")
        if isinstance(iid, str) and _ID.match(iid):
            links["import"] = f"/imports/{iid}"
        if isinstance(rid, str) and _RUN.match(rid):
            links["run"] = f"/runs/{rid}"
        pid = result.get("plan_id")
        if isinstance(pid, str) and _RUN.match(pid):
            links["plan"] = f"/plans/{pid}"
    return links


def view(doc: dict) -> dict:
    out = _clean(queue.public_job(doc))
    out["links"] = links_for(doc.get("result"))
    return out


def list_jobs(db, page: int, page_size: int, status: str | None, job_type: str | None) -> dict:
    q: dict = {}
    if status:
        q["status"] = status
    if job_type:
        q["type"] = job_type
    total = db[queue.COLLECTION].count_documents(q)
    docs = list(db[queue.COLLECTION].find(q, {"_id": 0}).sort(SORT).skip((page - 1) * page_size).limit(page_size))
    return page_response([view(d) for d in docs], total, page, page_size)


def get_job(db, job_id: str) -> dict:
    doc = db[queue.COLLECTION].find_one({"job_id": job_id}, {"_id": 0})
    if doc is None:
        raise ApiError(404, "NO_ENCONTRADO", "Trabajo no encontrado.")
    return view(doc)


# ---------------------------------------------------------------- encolado
def enqueue_import(db, *, sha256: str, size_bytes: int, month: str, label: str, upload_name: str,
                   created_by: str) -> tuple[dict, bool]:
    queue.ensure_indexes(db)
    job_input = {"upload_sha256": sha256, "upload_path": upload_name, "size_bytes": size_bytes,
                 "month": month, "label": label}
    public = {"label": label, "size_bytes": size_bytes, "sha256_short": sha256[:12], "month": month}
    return queue.enqueue(db, "import_excel", job_input, f"import:{sha256}", created_by, public=public)


def enqueue_generate(db, *, origin: date, horizon_days: int, method: str, generator: str,
                     idempotency_header: str | None, created_by: str) -> tuple[dict, bool]:
    queue.ensure_indexes(db)
    # misma funcion de clave que usa el temporizador: una sola definicion de identidad del trabajo
    key = generate_run_key(db, origin, horizon_days, method, idempotency_header, generator)
    job_input = {"origin": origin.isoformat(), "horizon_days": horizon_days, "method": method}
    return queue.enqueue(db, "generate_run", job_input, key, created_by, public=dict(job_input))
