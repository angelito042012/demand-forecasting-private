"""Handlers de los trabajos de la cola (T10 §4): `import_excel` y `generate_run`.

Un handler recibe un `JobContext` (sin acceso HTTP) y devuelve el resultado PUBLICO del trabajo. Reglas:
  * antes de cada etapa larga se comprueba la propiedad (`ctx.check`): si se perdio, `LostOwnership` y el handler
    se detiene sin escribir;
  * los errores de datos se elevan como `JobFailure(code, mensaje, retryable=False)`; los transitorios (Mongo no
    disponible, E/S) los clasifica `classify` como reintentables;
  * los mensajes son saneados (sin rutas, URI ni trazas) antes de llegar al documento del trabajo.
"""
from __future__ import annotations

import re
import threading
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from pymongo.errors import (
    ConnectionFailure,
    ExecutionTimeout,
    PyMongoError,
    WTimeoutError,
)

from pipeline.data import importer, month_lock
from pipeline.data.importer import import_workbook, read_rows, sha256_file
from pipeline.data.sources import approved_sources
from pipeline.generate.baseline import generate_and_publish
from pipeline.generate.config import PROJECT_ROOT, GenerationError, load_t10_config
from pipeline.jobs import queue
from pipeline.jobs.xlsx_check import XlsxRejected, inspect_xlsx
from pipeline.publish.protocol import LostOwnership as PublishLostOwnership
from pipeline.publish.protocol import PublishInProgressError, PublishValidationError
from pipeline.publish.schema import SchemaError
from pipeline.publish.source import SourceVerificationError

REMEDIATION_DOC = "docs/REMEDIACION_FUENTES.md"
_NAME = re.compile(r"^([0-9a-f]{64})\.xlsx$")
_SHA = re.compile(r"^[0-9a-f]{64}$")
_PATHS = re.compile(r"(?:[A-Za-z]:[\\/][^\s'\"]*|(?<![\w/])/(?:[A-Za-z_.-][\w.-]*/)+[\w.-]+|\\\\[^\s'\"]+)")
_URI = re.compile(r"mongodb(?:\+srv)?://\S+", re.IGNORECASE)


class JobFailure(Exception):
    """Fallo controlado del trabajo con codigo estable. `retryable=False` = error permanente (datos/entrada)."""

    def __init__(self, code: str, message: str, *, retryable: bool = False):
        self.code, self.message, self.retryable = code, message, retryable
        super().__init__(message)


def safe_message(text: str, limit: int = 300) -> str:
    """Quita rutas locales y URI de un mensaje antes de publicarlo en el trabajo."""
    return _PATHS.sub("<ruta>", _URI.sub("<uri>", str(text)))[:limit]


def classify(exc: BaseException) -> tuple[str, str, bool]:
    """(codigo, mensaje saneado, reintentable) de cualquier excepcion del handler."""
    if isinstance(exc, JobFailure):
        return exc.code, exc.message[:300], exc.retryable       # mensajes propios: redactados sin datos internos
    if isinstance(exc, GenerationError):
        return exc.code, exc.message[:300], exc.retryable
    if isinstance(exc, PublishInProgressError):
        return "PUBLICACION_EN_CURSO", "Otra publicación de la misma corrida sigue en curso; se reintentará.", True
    if isinstance(exc, PublishLostOwnership):
        return "PUBLICACION_CONCURRENTE", "Otro intento tomó la publicación de la corrida; se reintentará.", True
    if isinstance(exc, PublishValidationError):
        return "PUBLICACION_INVALIDA", "La validación de la corrida generada falló; no se publicó.", False
    if isinstance(exc, (SchemaError, SourceVerificationError)):
        return "ARTEFACTO_INVALIDO", "Un documento o artefacto no cumple el esquema o la verificación.", False
    if isinstance(exc, importer.IncompatibleSchemaError):
        return "ESQUEMA_INCOMPATIBLE", "La base contiene documentos de un esquema anterior.", False
    if isinstance(exc, (importer.ImportWriteError, importer.ImportInvariantError)):
        return "IMPORTACION_FALLIDA", safe_message(f"La importación no pudo completarse: {exc}"), False
    if isinstance(exc, (ConnectionFailure, ExecutionTimeout, WTimeoutError)):
        return "BASE_DE_DATOS_NO_DISPONIBLE", "La base de datos no está disponible; se reintentará.", True
    if isinstance(exc, PyMongoError):
        return "ERROR_BASE_DE_DATOS", f"Error de la base de datos ({type(exc).__name__}).", False
    if isinstance(exc, OSError):
        return "ERROR_DE_ENTRADA_SALIDA", "Error de lectura o escritura de archivos; se reintentará.", True
    return "ERROR_INTERNO", f"Error interno al procesar el trabajo ({type(exc).__name__}).", False


@dataclass
class JobContext:
    db: object
    claim: queue.Claim
    cfg: dict
    uploads_dir: Path
    lease_seconds: int = 60
    lost: threading.Event = field(default_factory=threading.Event)
    stage_hook: object = None            # solo pruebas: callable(etapa) llamado durante la publicacion
    activate_run: bool = False

    def check(self) -> None:
        """Lanza LostOwnership si el latido detecto la perdida o si la propiedad ya no es nuestra."""
        if self.lost.is_set() or not queue.still_owner(self.db, self.claim):
            self.lost.set()
            raise queue.LostOwnership(self.claim.job_id)

    def progress(self, stage: str, progress: dict | None = None) -> None:
        """Etapa y conteos REALES; renueva el lease y verifica propiedad (CAS)."""
        queue.heartbeat(self.db, self.claim, lease_seconds=self.lease_seconds, stage=stage, progress=progress)

    def guard(self) -> None:
        """`extra_guard` del publicador: renueva el lease del trabajo y exige seguir siendo el dueno."""
        if self.lost.is_set():
            raise queue.LostOwnership(self.claim.job_id)
        queue.heartbeat(self.db, self.claim, lease_seconds=self.lease_seconds)


# ------------------------------------------------------------------ import_excel
def _resolve_upload(ctx: JobContext, job_input: dict) -> tuple[Path, str]:
    sha = str(job_input.get("upload_sha256", ""))
    rel = str(job_input.get("upload_path", ""))
    if not _SHA.match(sha):
        raise JobFailure("ENTRADA_INVALIDA", "El trabajo no contiene un sha256 válido.")
    root = ctx.uploads_dir.resolve()
    if not rel or Path(rel).is_absolute() or ".." in Path(rel).parts or "/" in rel or "\\" in rel:
        raise JobFailure("ARCHIVO_NO_DISPONIBLE", "La ruta interna del archivo no es válida.")
    m = _NAME.match(rel)
    if m is None or m.group(1) != sha:
        raise JobFailure("ARCHIVO_NO_DISPONIBLE", "El nombre interno del archivo no corresponde a su sha256.")
    path = (root / rel).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise JobFailure("ARCHIVO_NO_DISPONIBLE", "El archivo cargado no está disponible en el almacén privado.")
    return path, sha


def _month_taken(month: str, state: str = "approved") -> str:
    why = {"approved": "ya tiene una fuente aprobada distinta",
           "importing": "está siendo importado desde otra fuente",
           "partial": "tiene una importación parcial de otra fuente que no se libera automáticamente"}.get(
        state, "ya está reservado por otra fuente")
    return (f"El mes {month} {why}. No se importó ni se aprobó el archivo (queda en cuarentena en el almacén "
            f"privado). Siga {REMEDIATION_DOC}.")


def _close_reservation(db, resv, fence, *, approved: bool = False, failed: bool = False) -> None:
    """Cierra la reserva del mes segun el resultado. Aprobada => `approved`; con conflictos => se libera (la fuente
    no queda aprobada); fallo sin escrituras => se libera; fallo con escrituras => `partial` (no se libera)."""
    try:
        if failed:
            if fence.wrote:
                month_lock.finish(db, resv, "partial")
            else:
                month_lock.release(db, resv)
        elif approved:
            month_lock.finish(db, resv, "approved")
        else:
            month_lock.release(db, resv)
    except (month_lock.LostReservation, PyMongoError):
        pass            # otro intento ya la retomo (o la base cayo): el lease vence y se recupera


def import_excel(ctx: JobContext) -> dict:
    inp, cfg = ctx.claim.input, ctx.cfg
    pol, up = cfg["politica_desarrollo"], cfg["subidas"]
    ctx.progress("verificando archivo")
    path, sha = _resolve_upload(ctx, inp)
    month = str(inp.get("month", ""))
    if month not in pol["meses_permitidos_de_carga"]:
        raise JobFailure("FECHAS_FUERA_DE_ALCANCE", "El mes del archivo está fuera de marzo a julio de 2026.")
    if sha256_file(path) != sha:
        raise JobFailure("ARCHIVO_ALTERADO", "El contenido del archivo no coincide con su sha256 registrado.")
    prev = ctx.db.imports.find_one({"sha256": sha, "estado": "completed", "noop": {"$ne": True}})
    if prev is not None:                    # mismo contenido ya importado: sin tocar nada
        return {"outcome": "sin_cambios", "import_id": prev["import_id"], "estado": prev["estado"],
                "mes": prev.get("mes"), "filas_leidas": prev["filas_leidas"], "ventas": prev["ventas_aceptadas"],
                "notas_credito": prev["notas_credito"], "rechazadas": prev["rechazadas"],
                "rechazos_por_motivo": prev.get("rechazos_por_motivo", {}), "insertadas": 0,
                "ya_existentes": prev["ventas_aceptadas"] + prev["notas_credito"],
                "en_conflicto": prev.get("en_conflicto", 0)}
    try:
        inspect_xlsx(path, max_entries=int(up["max_entradas_zip"]), max_expanded=int(up["tam_max_expandido_bytes"]),
                     max_rows=int(up["max_filas_hoja"]), allowed_months=tuple(pol["meses_permitidos_de_carga"]))
    except XlsxRejected as exc:
        if exc.code in ("AGOSTO_RESERVADO", "MES_FUERA_DE_ALCANCE"):
            raise JobFailure("FECHAS_FUERA_DE_ALCANCE", exc.message) from None
        raise JobFailure("ARCHIVO_INVALIDO", f"{exc.code}: {exc.message}") from None
    ctx.check()

    ctx.progress("revisando fechas")
    try:
        rows = read_rows(path)
    except Exception as exc:
        raise JobFailure("ARCHIVO_INVALIDO", "El libro no se puede leer (dañado, truncado o sin encabezados).") from exc
    if len(rows) > int(up["max_filas_hoja"]):
        raise JobFailure("ARCHIVO_INVALIDO", "La hoja excede el número de filas permitido.")
    lo = date.fromisoformat(pol["meses_permitidos_de_carga"][0] + "-01")
    hi = date.fromisoformat(pol["ultimo_dia_de_datos"])
    out_of_scope, in_month, example = 0, 0, None
    for _n, rec in rows:
        f = rec.get("FECHA")
        if isinstance(f, (datetime, date)):
            d = f.date() if isinstance(f, datetime) else f
            if not lo <= d <= hi:
                out_of_scope += 1
                example = example or d.isoformat()
            elif f"{d.year:04d}-{d.month:02d}" == month:
                in_month += 1
    if out_of_scope:
        raise JobFailure("FECHAS_FUERA_DE_ALCANCE",
                         f"El archivo contiene {out_of_scope} filas con fechas fuera de marzo a julio de 2026 "
                         f"(por ejemplo {example}). No se importó nada.")
    if in_month == 0:
        raise JobFailure("MES_NO_COINCIDE", f"Ninguna fila tiene fecha del mes declarado ({month}). No se importó nada.")
    ctx.progress("verificando fuentes", {"filas_leidas": len(rows)})

    for other_sha, imp in approved_sources(ctx.db).items():       # fuente aprobada ANTES de la reserva (historial)
        if imp.get("mes") == month and other_sha != sha:
            raise JobFailure("MES_CON_FUENTE_APROBADA", _month_taken(month))
    ctx.check()

    # T10R R09: exclusion durable por mes ANTES de escribir; el chequeo anterior solo es una salida temprana.
    try:
        resv = month_lock.reserve(ctx.db, month, sha, lease_seconds=max(2 * ctx.lease_seconds, month_lock.LEASE_SECONDS))
    except month_lock.MonthReserved as exc:
        raise JobFailure("MES_CON_FUENTE_APROBADA", _month_taken(month, exc.holder_state)) from None
    except month_lock.ImportInProgress:
        raise JobFailure("IMPORTACION_EN_CURSO", "La misma fuente ya se está importando; se reintentará.",
                         retryable=True) from None
    fence = month_lock.Fence(ctx.db, resv, lease_seconds=max(2 * ctx.lease_seconds, month_lock.LEASE_SECONDS),
                             extra=ctx.check)
    try:
        ctx.progress("importando", {"filas_leidas": len(rows)})
        rep = import_workbook(path, ctx.db, expected_month=month, fence=fence)
        _close_reservation(ctx.db, resv, fence, approved=rep.estado == "completed")
    except month_lock.LostReservation:
        raise JobFailure("IMPORTACION_CONCURRENTE", "Otro intento retomó la importación de este mes; se reintentará.",
                         retryable=True) from None
    except BaseException:
        _close_reservation(ctx.db, resv, fence, failed=True)
        raise
    result = {"outcome": "importado", "import_id": rep.import_id, "estado": rep.estado, "mes": rep.mes,
              "filas_leidas": rep.filas_leidas, "ventas": rep.ventas_aceptadas, "notas_credito": rep.notas_credito,
              "rechazadas": rep.rechazadas, "rechazos_por_motivo": dict(rep.rechazos_por_motivo),
              "insertadas": rep.insertadas, "ya_existentes": rep.ya_existentes, "en_conflicto": rep.en_conflicto}
    if rep.en_conflicto:
        result["advertencia"] = (f"{rep.en_conflicto} líneas quedaron en conflicto y la fuente NO está aprobada "
                                 f"hasta resolverlas ({REMEDIATION_DOC}).")
    return result


# ------------------------------------------------------------------ generate_run
def generate_run(ctx: JobContext) -> dict:
    inp = ctx.claim.input
    try:
        origin = date.fromisoformat(str(inp["origin"]))
        horizon = int(inp["horizon_days"])
        method = str(inp["method"])
    except (KeyError, ValueError, TypeError):
        raise JobFailure("ENTRADA_INVALIDA", "La entrada del trabajo no es válida.") from None
    ctx.check()
    return generate_and_publish(ctx.db, origin, horizon, method, cfg=ctx.cfg, extra_guard=ctx.guard,
                                progress=ctx.progress, stage_hook=ctx.stage_hook, activate_run=ctx.activate_run)


HANDLERS = {"import_excel": import_excel, "generate_run": generate_run}


def default_uploads_dir(cfg: dict | None = None) -> Path:
    return PROJECT_ROOT / (cfg or load_t10_config())["subidas"]["directorio_privado"]
