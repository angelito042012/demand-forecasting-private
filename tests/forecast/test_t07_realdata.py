"""T07 integracion con los seis Excel reales en una base temporal (RUN_REALDATA=1). No lee agosto."""
import json
import os
from pathlib import Path

import numpy as np
import pytest

from pipeline.data.importer import import_folder
from scripts import run_t07 as r
from tests.data.conftest import db  # noqa: F401  (fixture compartida)

SRC = Path(r"C:\Users\rogel\Documents\Datos")
pytestmark = [pytest.mark.mongo, pytest.mark.realdata,
              pytest.mark.skipif(not SRC.exists() or os.environ.get("RUN_REALDATA") != "1", reason="requiere RUN_REALDATA=1")]
CFG = json.loads(Path("config/t07_config.json").read_text(encoding="utf-8"))


def _sig(res):
    rev = res["sim_rep"]["revisiones"]
    return {"init": res["sim_rep"]["hash_inicializacion"], "hashes": {x["dia"]: x["hash_pronostico"] for x in rev},
            "rf": res["pred"]["predicciones"].groupby("fold")["pred_rf_distribuido"].apply(lambda s: s.fillna(-1).round(9).tolist()).to_dict(),
            "n": res["sim_rep"]["universo_skus"]}


def test_same_universe_no_august_no_future_leak_and_conservation(db):  # noqa: F811
    import_folder(SRC, db)
    base = r.compute(db, CFG, "sha", None)
    # mismo universo y escenario inicial entre politicas; conservacion y identidad de valor ya verificadas por el motor
    pols = {p: base["sim"][(7, 7, p)]["total"] for p in r.POLICIES}
    assert len({v["skus"] for v in pols.values()}) == 1 and len({v["stock_inicial_unidades"] for v in pols.values()}) == 1
    assert len({v["demanda_proxy_elegible_unidades"] for v in pols.values()}) == 1
    assert max(abs(m["identidad_valor"]) for m in base["sim"].values()) < 1e-6
    assert len(base["sim"]) == 27 and max(r_ for r_ in (x["fecha"] for x in base["world"]["D"].sales)) <= "2026-07-31"
    dates = base["sim_rep"]["revisiones"]
    assert next(x["dia"] for x in dates) == "2026-06-01" and [x["dia"] for x in dates][-1] == "2026-07-27"
    s0 = _sig(base)
    # 1) cambiar ventas posteriores al 10/07 no altera pronosticos de origenes <= 10/07 ni los folds G1-G4
    db.sales.update_many({"fecha": {"$gt": "2026-07-10"}}, [{"$set": {"cantidad_base": {"$multiply": ["$cantidad_base", 3]}}}])
    s1 = _sig(r.compute(db, CFG, "sha", None))
    for d, h in s0["hashes"].items():
        assert (s1["hashes"][d] == h) == (d <= "2026-07-10"), d
    assert s1["rf"] == s0["rf"] and s1["init"] == s0["init"]
    # 2) cambiar todo desde el 01/06: el escenario inicial (stock, medias, costos) y G1 no cambian
    db.sales.update_many({"fecha": {"$gt": "2026-05-31", "$lte": "2026-07-10"}},
                         [{"$set": {"cantidad_base": {"$multiply": ["$cantidad_base", 2]}}}])
    s2 = _sig(r.compute(db, CFG, "sha", None))
    assert s2["init"] == s0["init"] and s2["n"] == s0["n"] and s2["rf"]["G1"] == s0["rf"]["G1"]
    assert all(s2["hashes"][d] != s0["hashes"][d] for d in s0["hashes"])
    assert not np.array_equal(np.array(s2["rf"]["G4"]), np.array(s0["rf"]["G4"]))
