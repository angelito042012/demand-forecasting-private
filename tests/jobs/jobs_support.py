"""Ayudas de las pruebas de T10 (trabajos): Excel sinteticos, cola, ejecucion de un trabajo en proceso."""
from __future__ import annotations

import copy
import hashlib
from datetime import date, datetime
from pathlib import Path

from pipeline.generate.config import load_t10_config
from pipeline.jobs import queue
from pipeline.jobs.keys import generate_run_key, import_key
from pipeline.jobs.worker import process_next
from tests.data.conftest import make_row, write_xlsx


def month_rows(month: int, n_sales: int = 10, n_credit: int = 2, *, bad_currency: int = 1, seed: int = 0) -> list:
    """Filas sinteticas de un mes: ventas, notas de credito (TIPO_DOC 7, negativas) y rechazos (moneda)."""
    rows = []
    for i in range(n_sales):
        n = seed * 1000 + i + 1
        q = 2 + i % 3
        rows.append(make_row(ID_PEDIDO=n, SERIE_NUMERO=f"B{month}-{seed}-{n}", ID_ARTICULO=100 + i % 4,
                             FECHA=datetime(2026, month, 1 + i % 20), CANTIDAD=q, CANTIDAD_UM_BASE=q,
                             TOTAL_LINEA=q * 5.5))
    for j in range(n_credit):
        n = seed * 1000 + 500 + j
        rows.append(make_row(ID_PEDIDO=0, TIPO_DOC=7, SERIE_NUMERO=f"NC{month}-{seed}-{n}", ID_ARTICULO=100 + j,
                             FECHA=datetime(2026, month, 5 + j), CANTIDAD=-1, CANTIDAD_UM_BASE=-1,
                             TOTAL_LINEA=-5.5))
    for k in range(bad_currency):
        n = seed * 1000 + 900 + k
        rows.append(make_row(ID_PEDIDO=n, SERIE_NUMERO=f"X{month}-{seed}-{n}", MONEDA="USD",
                             FECHA=datetime(2026, month, 9)))
    return rows


def store_upload(uploads: Path, tmp: Path, rows: list, name: str = "tmp.xlsx") -> tuple[str, int]:
    """Escribe un xlsx sintetico y lo guarda como <sha256>.xlsx en el directorio privado de la prueba."""
    src = write_xlsx(tmp / name, rows)
    data = Path(src).read_bytes()
    return put_bytes(uploads, data)


def put_bytes(uploads: Path, data: bytes) -> tuple[str, int]:
    sha = hashlib.sha256(data).hexdigest()
    uploads.mkdir(parents=True, exist_ok=True)
    (uploads / f"{sha}.xlsx").write_bytes(data)
    return sha, len(data)


def enqueue_import(db, sha: str, size: int, month: str, *, key: str | None = None, upload_path: str | None = None,
                   max_attempts: int = 3) -> dict:
    queue.ensure_indexes(db)
    job, _ = queue.enqueue(
        db, "import_excel", {"upload_sha256": sha, "upload_path": upload_path or f"{sha}.xlsx", "size_bytes": size,
                             "month": month, "label": "prueba"}, key or import_key(sha), "admin",
        max_attempts=max_attempts, public={"label": "prueba", "month": month})
    return job


def enqueue_generate(db, origin: date, *, horizon: int = 21, header: str | None = None, max_attempts: int = 3) -> dict:
    queue.ensure_indexes(db)
    key = generate_run_key(db, origin, horizon, "promedio_28", header)
    job, _ = queue.enqueue(db, "generate_run", {"origin": origin.isoformat(), "horizon_days": horizon,
                                                "method": "promedio_28"}, key, "admin", max_attempts=max_attempts,
                           public={"origin": origin.isoformat()})
    return job


def fast_cfg() -> dict:
    cfg = copy.deepcopy(load_t10_config())
    cfg["cola"]["backoff_base_segundos"] = 0
    return cfg


def run_job(db, uploads: Path, *, cfg: dict | None = None, worker: str = "w-test", stage_hook=None) -> dict | None:
    """Reclama y procesa UN trabajo en proceso (mismo codigo que el worker real). Devuelve el documento final."""
    jid = process_next(db, worker, cfg or fast_cfg(), uploads_dir=uploads, lease_seconds=60, heartbeat_seconds=15,
                       stage_hook=stage_hook)
    return db.jobs.find_one({"job_id": jid}) if jid else None
