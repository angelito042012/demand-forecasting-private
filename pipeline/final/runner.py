"""T12: orquestador por fases idempotentes de la evaluacion final (verify -> prepare -> evaluate -> audit -> report).

Garantias:
* `prepare` solo usa `load_training_data` (<= 31/07); jamas toca agosto. Guarda y SELLA (hashes de bytes y de contenido
  logico) paquete RF, predicciones fijas 01-21/08 e inicializacion de la simulacion, y emite `docs/T12_SELLO.json`.
* `evaluate` exige: confirmacion explicita, congelacion intacta (hashes), sello coincidente con los artefactos y, por
  defecto, el sello COMMITEADO en Git antes de leer agosto. Solo entonces llama a
  `load_final_test_sales(..., frozen_selection_confirmed=True)`; deja una intencion registrada antes de leer.
* Cada fase escribe un checkpoint en `estado.json`; un error queda registrado y nunca marca la ejecucion como completa;
  retomar reutiliza artefactos validos (hash) sin volver a seleccionar ni sobreescribir evidencia.
"""
from __future__ import annotations

import dataclasses
import gzip
import hashlib
import json
import platform
import subprocess
import time
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from pipeline.data import daily_series as ds
from pipeline.data.calendar import EXCLUDED_DATES
from pipeline.data.training_access import load_final_test_sales, load_training_data
from pipeline.final import core
from pipeline.final.frozen import (
    ROOT,
    FreezeError,
    load_frozen_config,
    load_frozen_engine,
    verify_freeze,
)
from pipeline.forecast.models import save_bundle
from pipeline.forecast.t05 import _wide

LIMA = ZoneInfo("America/Lima")
VERSION = "t12-1"
SEAL_PATH = ROOT / "docs" / "T12_SELLO.json"
PHASES = ("verificacion", "preparacion", "lectura_agosto", "evaluacion_predictiva", "simulacion", "auditoria", "reporte")


class FinalGateError(RuntimeError):
    """La evaluacion final no puede continuar (sin confirmacion, congelacion alterada o sello no valido)."""


def now_lima() -> str:
    return datetime.now(LIMA).isoformat(timespec="seconds")


def sha_bytes(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str).encode("utf-8")


def git(*args: str) -> str:
    out = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False)
    return out.stdout.strip()


def env_info() -> dict:
    import numpy
    import pandas
    import sklearn
    return {"python": platform.python_version(), "numpy": numpy.__version__, "pandas": pandas.__version__,
            "sklearn": sklearn.__version__, "plataforma": platform.platform()}


def _write_json(path: Path, obj) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)


def _save_npz(path: Path, arrays: dict) -> dict:
    tmp = path.with_name(path.name + ".tmp.npz")
    np.savez(tmp, **arrays)
    tmp.replace(path)
    return {"bytes_sha256": sha_bytes(path), "logical_sha256": core.logical_signature(arrays)}


def _load_npz(path: Path) -> dict:
    with np.load(path, allow_pickle=False) as z:
        return {k: z[k] for k in z.files}


class StateFile:
    """Estado y checkpoints de las siete fases (`estado.json`). Lo comparten el runner y las fases que no usan MongoDB
    (auditoria y reporte): inicio/fin/error/intentos de cada fase y `completa` solo si las siete estan completas."""

    def __init__(self, out_dir: Path):
        self.out = Path(out_dir)
        self.out.mkdir(parents=True, exist_ok=True)
        self.state_path = self.out / "estado.json"
        self.state = (json.loads(self.state_path.read_text(encoding="utf-8")) if self.state_path.exists()
                      else {"version": VERSION, "fases": {}, "eventos": [], "completa": False})

    def _save(self) -> None:
        _write_json(self.state_path, self.state)

    def event(self, fase: str, mensaje: str, **extra) -> None:
        self.state["eventos"].append({"t": now_lima(), "fase": fase, "mensaje": mensaje, **extra})
        self._save()

    def _begin(self, fase: str) -> None:
        f = self.state["fases"].setdefault(fase, {})
        f.update({"estado": "en_curso", "inicio": now_lima(), "intentos": f.get("intentos", 0) + 1})
        f.pop("error", None)
        self.state["completa"] = False
        self._save()

    def _end(self, fase: str, **extra) -> None:
        self.state["fases"][fase].update({"estado": "completa", "fin": now_lima(), **extra})
        self.state["completa"] = all(self.state["fases"].get(p, {}).get("estado") == "completa" for p in PHASES)
        self._save()

    def _fail(self, fase: str, exc: BaseException | str) -> None:
        f = self.state["fases"].setdefault(fase, {})
        msg = exc if isinstance(exc, str) else f"{type(exc).__name__}: {str(exc)[:300]}"
        f.update({"estado": "error", "fin": now_lima(), "error": msg})
        self.state["completa"] = False
        self._save()

    def done(self, fase: str) -> bool:
        return self.state["fases"].get(fase, {}).get("estado") == "completa"

    def correction(self, motivo: str, **extra) -> None:
        """Registra una correccion tecnica POSTERIOR (sin tocar fechas ni hashes de las fases originales)."""
        self.state.setdefault("correcciones", []).append({"t": now_lima(), "git_commit_base": git("rev-parse", "HEAD"),
                                                           "motivo": motivo, **extra})
        self._save()


class FinalRun(StateFile):
    def __init__(self, db, out_dir: Path, *, seal_path: Path = SEAL_PATH, require_commit: bool = True):
        super().__init__(out_dir)
        self.db = db
        (self.out / "preparacion").mkdir(exist_ok=True)
        self.seal_path, self.require_commit = Path(seal_path), require_commit
        self.cfg = load_frozen_config()
        self.t07 = json.loads((ROOT / "config" / "t07_config.json").read_text(encoding="utf-8"))
        self.t07_sha = sha_bytes(ROOT / "config" / "t07_config.json")    # igual que T07: hash de bytes del archivo

    # ------------------------------------------------------------------ 1. verificacion
    def verify(self) -> dict:
        self._begin("verificacion")
        try:
            rep = verify_freeze()
            rep["entorno"] = env_info()
            rep["git_commit"] = git("rev-parse", "HEAD")
            _write_json(self.out / "verificacion.json", rep)
            self._end("verificacion", git_commit=rep["git_commit"])
            return rep
        except BaseException as exc:
            self._fail("verificacion", exc)
            raise

    # ------------------------------------------------------------------ 2. preparacion (<= 31/07)
    def prepare(self) -> dict:
        if self.done("preparacion") and self._prep_valid():
            return json.loads((self.out / "preparacion" / "manifiesto_preparacion.json").read_text(encoding="utf-8"))
        self._begin("preparacion")
        try:
            ver = self.verify() if not self.done("verificacion") else json.loads(
                (self.out / "verificacion.json").read_text(encoding="utf-8"))
            core.quiet_warnings()
            D = load_training_data(self.db, core.ORIGIN, start=core.START)
            if D.sales and max(r["fecha"] for r in D.sales) > core.iso(core.ORIGIN):
                raise AssertionError("ventas posteriores al 31/07 en la preparacion")
            world = core.history_world(D)
            t0 = time.perf_counter()
            fixed = core.fixed_predictions(world, self.t07["rf_categoria"], self.t07["cohorte_primaria"], self.t07_sha)
            seg = round(time.perf_counter() - t0, 2)
            sim_in = core.sealed_inputs_for_sim(world, D, self.t07["simulacion"], self.t07["cohorte_primaria"])
            prep = self.out / "preparacion"
            files = {"predicciones_fijas.npz": _save_npz(prep / "predicciones_fijas.npz", fixed["arrays"]),
                     "inicializacion_sim.npz": _save_npz(prep / "inicializacion_sim.npz", sim_in["arrays"])}
            save_bundle(fixed["bundle"], prep / "rf_categoria_T12.joblib")
            files["rf_categoria_T12.joblib"] = {"bytes_sha256": sha_bytes(prep / "rf_categoria_T12.joblib")}
            man = {"version": VERSION, "creado_lima": now_lima(), "git_commit": git("rev-parse", "HEAD"),
                   "git_arbol_limpio_codigo": git("status", "--porcelain", "--", "pipeline", "scripts", "config", "tests") == "",
                   "entorno": env_info(), "semilla_rf": self.t07["rf_categoria"]["parametros"]["random_state"],
                   "origen": core.iso(core.ORIGIN), "bloque": [core.iso(core.BLOCK_START), core.iso(core.BLOCK_END)],
                   "agosto_consultado": False, "reference_v1_consultado": False,
                   "fingerprint_entrenamiento": D.fingerprint, "fuentes": list(D.sources.manifest),
                   "calendario": [world["cal"][0], world["cal"][-1]], "dias_enmascarados": sorted(map(core.iso, EXCLUDED_DATES)),
                   "filas_entrenamiento": len(D.sales), "filas_omitidas_mascara": D.omitted_excluded_rows,
                   "config_t07_sha256": self.t07_sha, "seleccion_congelada_sha256": ver["comprobaciones"]["json_congelado"]["actual"],
                   "documento_congelado_sha256": ver["comprobaciones"]["documento_congelado"]["actual"],
                   "motor_congelado_sha256": ver["comprobaciones"]["motor_congelado_copia"]["actual"],
                   "codigo_vivo_no_coincide": ver["no_coinciden_vivo_y_motivo"], "segundos_rf": seg,
                   "info": {k: fixed["info"][k] for k in ("weight_counts", "conservacion_max_abs_error", "negativos_recortados",
                                                             "n_sku", "n_primaria", "n_conocidos", "n_categorias")},
                   "entrenamiento_rf": fixed["info"]["entrenamiento"], "costos": sim_in["cost_counts"],
                   "archivos": files}
            man["sello_sha256"] = hashlib.sha256(canonical({k: v for k, v in man.items() if k != "creado_lima"})).hexdigest()
            _write_json(prep / "manifiesto_preparacion.json", man)
            seal = {"version": VERSION, "sello_sha256": man["sello_sha256"], "creado_lima": man["creado_lima"],
                    "git_commit_codigo": man["git_commit"], "fingerprint_entrenamiento": D.fingerprint,
                    "archivos": {k: {kk: vv for kk, vv in v.items()} for k, v in files.items()},
                    "agosto_consultado": False,
                    "nota": "Hashes de las predicciones fijas 01-21/08 emitidas con datos <= 31/07, antes de leer agosto."}
            _write_json(self.seal_path, seal)
            self._end("preparacion", sello_sha256=man["sello_sha256"])
            return man
        except BaseException as exc:
            self._fail("preparacion", exc)
            raise

    def _prep_valid(self) -> bool:
        try:
            self._load_sealed()
            return True
        except (FinalGateError, FileNotFoundError, KeyError):
            return False

    def _load_sealed(self) -> tuple[dict, dict, dict]:
        prep = self.out / "preparacion"
        man = json.loads((prep / "manifiesto_preparacion.json").read_text(encoding="utf-8"))
        # el sello se calculo con todos los campos salvo creado_lima y el propio sello: se recalcula igual
        base = {k: v for k, v in man.items() if k not in ("creado_lima", "sello_sha256")}
        if hashlib.sha256(canonical(base)).hexdigest() != man["sello_sha256"]:
            raise FinalGateError("el manifiesto de preparacion fue alterado (sello no coincide)")
        arrays = {}
        for name in ("predicciones_fijas.npz", "inicializacion_sim.npz"):
            p = prep / name
            if sha_bytes(p) != man["archivos"][name]["bytes_sha256"]:
                raise FinalGateError(f"{name}: hash de bytes distinto del sellado")
            data = _load_npz(p)
            if core.logical_signature(data) != man["archivos"][name]["logical_sha256"]:
                raise FinalGateError(f"{name}: contenido logico distinto del sellado")
            arrays[name] = data
        if sha_bytes(prep / "rf_categoria_T12.joblib") != man["archivos"]["rf_categoria_T12.joblib"]["bytes_sha256"]:
            raise FinalGateError("rf_categoria_T12.joblib: hash distinto del sellado")
        return man, arrays["predicciones_fijas.npz"], arrays["inicializacion_sim.npz"]

    # ------------------------------------------------------------------ compuerta antes de leer agosto
    def _gate(self, confirm_frozen: bool) -> tuple[dict, dict, dict]:
        if confirm_frozen is not True:
            raise FinalGateError("agosto es test final: requiere confirmacion explicita de la seleccion congelada")
        try:
            verify_freeze()
        except FreezeError as exc:
            raise FinalGateError(f"congelacion alterada: {exc}") from exc
        if not self.done("preparacion"):
            raise FinalGateError("la preparacion no esta completa: ejecute prepare antes de evaluate")
        man, fixed, sim_in = self._load_sealed()
        if self.require_commit:
            try:
                seal_rel = str(self.seal_path.resolve().relative_to(ROOT)).replace("\\", "/")
            except ValueError as exc:
                raise FinalGateError("el sello debe estar dentro del repositorio y commiteado antes de leer agosto") from exc
            if not git("ls-files", "--error-unmatch", seal_rel) or git("diff", "HEAD", "--stat", "--", seal_rel):
                raise FinalGateError("el sello T12 debe estar commiteado y sin cambios antes de leer agosto")
            if not self.seal_path.is_file() or json.loads(self.seal_path.read_text(encoding="utf-8")).get(
                    "sello_sha256") != man["sello_sha256"]:
                raise FinalGateError("el sello versionado no coincide con el manifiesto de preparacion")
        return man, fixed, sim_in

    # ------------------------------------------------------------------ 3. lectura de agosto
    def _read_august(self) -> list:
        csv = self.out / "ventas_agosto_min.csv.gz"
        f = self.state["fases"].get("lectura_agosto", {})
        if self.done("lectura_agosto") and csv.is_file() and sha_bytes(csv) == f.get("bytes_sha256"):
            df = pd.read_csv(csv, dtype={"sku": str, "almacen": str})
            return [{"fecha": r.fecha, "sku": r.sku, "almacen": r.almacen, "cantidad_base": r.cantidad_base}
                    for r in df.itertuples(index=False)]
        self._begin("lectura_agosto")
        try:
            self.event("lectura_agosto", "INTENCION: leer agosto con load_final_test_sales(frozen_selection_confirmed=True)")
            rows = load_final_test_sales(self.db, frozen_selection_confirmed=True)
            if any(not (core.iso(core.SIM_START) <= r["fecha"] <= core.iso(core.SIM_END)) for r in rows):
                raise AssertionError("la ruta final devolvio fechas fuera de agosto")
            slim = [(r["fecha"], r["sku"], r["almacen"], float(r["cantidad_base"])) for r in rows]
            df = pd.DataFrame(slim, columns=["fecha", "sku", "almacen", "cantidad_base"]).sort_values(
                ["fecha", "sku", "almacen", "cantidad_base"], kind="stable")
            tmp = csv.with_name(csv.name + ".tmp")
            with gzip.open(tmp, "wt", encoding="utf-8", newline="") as fh:
                df.to_csv(fh, index=False, float_format="%.10g")
            tmp.replace(csv)
            self._end("lectura_agosto", filas=len(df), primera=str(df["fecha"].min()) if len(df) else None,
                      ultima=str(df["fecha"].max()) if len(df) else None, bytes_sha256=sha_bytes(csv),
                      unidades=float(df["cantidad_base"].sum()))
            return [{"fecha": r.fecha, "sku": str(r.sku), "almacen": str(r.almacen), "cantidad_base": float(r.cantidad_base)}
                    for r in df.itertuples(index=False)]
        except BaseException as exc:
            self._fail("lectura_agosto", exc)
            raise

    # ------------------------------------------------------------------ 4/5. evaluacion
    def evaluate(self, *, confirm_frozen: bool = False) -> dict:
        man, fixed, sim_in = self._gate(confirm_frozen)
        core.quiet_warnings()
        D = load_training_data(self.db, core.ORIGIN, start=core.START)
        if D.fingerprint != man["fingerprint_entrenamiento"]:
            raise FinalGateError("la historia <= 31/07 cambio desde la preparacion (fingerprint distinto)")
        world = core.history_world(D)
        keys = world["keys"]
        if list(fixed["sku_keys"]) != [f"{k[0]}|{k[1]}" for k in keys]:
            raise FinalGateError("el universo SKU-almacen recalculado no coincide con el sellado")
        aug = self._read_august()
        sales_all = list(D.sales) + aug
        covered = {r["fecha"] for r in sales_all}
        masked = {core.iso(d) for d in EXCLUDED_DATES}
        days = core.block_days()
        eval_days = core.evaluable_days(days, covered, masked)
        if not self.done("evaluacion_predictiva"):
            self._begin("evaluacion_predictiva")
            try:
                act, new = core.block_actuals(keys, aug, days)
                names = list(fixed["cat_names"])
                cpos = {c: i for i, c in enumerate(names)}
                cat_idx = np.array([cpos[c] for c in world["cats"]])
                ev = core.evaluate_predictive(fixed, act, eval_days, cat_idx)
                known_units = float(act[:, eval_days].sum()) if eval_days.any() else 0.0
                nuevos = core.new_sku_report(new, [d for d, e in zip(days, eval_days, strict=True) if e], known_units)
                saved = _save_npz(self.out / "reales_bloque.npz", {"act": act, "eval_days": eval_days, "cat_idx": cat_idx,
                                                                      "dias": np.array(days)})
                pred = {"sku": ev["sku"], "categoria": ev["categoria"], "cobertura": ev["cobertura"], "nuevos_sku": nuevos,
                        "dias_evaluables": int(eval_days.sum()), "dias_no_evaluables": [d for d, e in zip(days, eval_days, strict=True) if not e],
                        "universo": {"sku_conocidos": int(fixed["sku_conocido"].sum()), "primaria": int(fixed["sku_primaria"].sum()),
                                     "categorias": len(names)}}
                _write_json(self.out / "predictivo.json", pred)
                self._end("evaluacion_predictiva", reales=saved, predictivo_sha256=sha_bytes(self.out / "predictivo.json"))
            except BaseException as exc:
                self._fail("evaluacion_predictiva", exc)
                raise
        if not self.done("simulacion"):
            self._simulate(D, world, aug, fixed, sim_in)
        return self.state

    def _simulate(self, D, world: dict, aug: list, fixed: dict, sim_in: dict) -> None:
        self._begin("simulacion")
        try:
            eng = load_frozen_engine()
            sim_cfg = self.t07["simulacion"]
            cal2 = [core.iso(core.START + timedelta(days=i)) for i in range((core.SIM_END - core.START).days + 1)]
            D2 = dataclasses.replace(D, sales=tuple(D.sales) + tuple(aug), calendar=tuple(
                core.START + timedelta(days=i) for i in range(len(cal2))))
            pairs2 = ds.pair_daily(D2)
            keys2, W2 = _wide(pairs2, ["sku", "almacen"], "cantidad_base", cal2)
            pos2 = {k: i for i, k in enumerate(keys2)}
            keys = world["keys"]
            rows = [pos2[k] for k in keys]
            Wu = W2[rows]
            col0 = cal2.index(core.iso(core.ORIGIN)) + 1
            if not np.array_equal(Wu[:, :col0], world["W"], equal_nan=True):
                raise FinalGateError("la matriz <= 31/07 cambio al incorporar agosto (no debe ocurrir)")
            if not np.array_equal(np.nan_to_num(t07_mean(Wu[:, :col0])), sim_in["sim_media_inicial"]):
                raise FinalGateError("la media inicial recalculada no coincide con la sellada")
            n_days = (core.SIM_END - core.SIM_START).days + 1
            known = set(keys)
            new_rows = [i for k, i in pos2.items() if k not in known]
            new_units = float(np.nansum(np.clip(W2[new_rows][:, col0:col0 + n_days], 0, None))) if new_rows else 0.0
            alms = sorted({k[1] for k in keys})

            def progress(j, f):
                self.event("simulacion", f"revision j={j} (origen col {f['origen_columna']}) pronostico listo", hash=f["hash"])
            t0 = time.perf_counter()
            sim = core.sequential_simulation(W=Wu, col0=col0, n_days=n_days, cats=world["cats"], alms=alms,
                                             cost=sim_in["sim_costo_unitario"], mean_init=sim_in["sim_media_inicial"],
                                             prim0=sim_in["sim_primaria_inicial"], rf_cfg=self.t07["rf_categoria"],
                                             sim_cfg=sim_cfg, config_sha=self.t07_sha, eng=eng, progress=progress)
            seg = round(time.perf_counter() - t0, 1)
            results = sim["results"]
            diffs = core.policy_diffs(results, core.KEY_METRICS)
            ident = max(abs(m["identidad_valor"]) for m in results.values())
            if ident >= 1e-6:
                raise AssertionError(f"identidad de valor violada: {ident}")
            arr = {f"{k}__{name}": getattr(v, name) for k, v in sim["arrays"].items()
                   for name in ("on_hand", "served", "lost", "received", "ordered", "pipeline_end", "stock0")}
            arr["demanda"] = sim["demand"]
            arr["costo"] = sim_in["sim_costo_unitario"]
            saved = _save_npz(self.out / "simulacion_series.npz", arr)
            rep = {"universo_skus": len(keys), "primaria_inicial": int(sim_in["sim_primaria_inicial"].sum()),
                   "historia_corta_inicial": int((~sim_in["sim_primaria_inicial"]).sum()),
                   "excluidos_nuevos_skus": len(new_rows), "excluidos_nuevos_unidades_proxy": new_units,
                   "fallback_rf_a_promedio_filas": sim["fallback_rf_filas"], "dias": n_days,
                   "dias_evaluables": int((~np.isnan(sim["demand"])).all(axis=0).sum()),
                   "dias_sin_demanda_conocida": [cal2[col0 + i] for i in range(n_days) if np.isnan(sim["demand"][:, i]).all()],
                   "costos": man_costs(self.out), "segundos": seg,
                   "revisiones": [{"dia": cal2[f["origen_columna"]], "pesos": f["pesos"], "conservacion_cat_a_sku": f["conservacion"],
                                   "hash_pronostico": f["hash"], "entrenamiento": f["entrenamiento"]}
                                  for f in sim["forecasts"].values()]}
            out = {"resultados": {f"L{L}_S{S}|{pol}": mt for (L, S, pol), mt in results.items()}, "diferencias": diffs,
                   "reporte": rep, "identidad_valor_max_abs": ident}
            _write_json(self.out / "simulacion.json", out)
            self._end("simulacion", series=saved, simulacion_sha256=sha_bytes(self.out / "simulacion.json"),
                      identidad_valor_max_abs=ident)
        except BaseException as exc:
            self._fail("simulacion", exc)
            raise


def t07_mean(values: np.ndarray) -> np.ndarray:
    from pipeline.forecast import t07 as t7
    return t7.mean_window(values)


def man_costs(out: Path) -> dict:
    p = out / "preparacion" / "manifiesto_preparacion.json"
    return json.loads(p.read_text(encoding="utf-8")).get("costos", {}) if p.exists() else {}


def utc_now() -> datetime:
    return datetime.now(UTC)


def date_of(s: str) -> date:
    return date.fromisoformat(s)
