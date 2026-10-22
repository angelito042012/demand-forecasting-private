"""T20 §3: plan con existencia reconstruida (snapshot RECONSTRUIDO, corte de ventas 20/10, decision 21/10).

Caso a mano (m = 2/dia, reserva 7 dias, minimo 1, multiplo 1, mes 2026-11, existencia de cierre 20/10):
* producto con 10 unidades, plazo 7: el primer dia simulado es el 21/10; 10 -> 8 -> 6 -> 4 -> 2 -> 0 (25/10) y faltan 2 el 26 y 27
  (faltante 4, consumido 10); llega el 28/10 con S=0; del 28/10 al 30/11 hay 34 dias: necesidad 34*2 + 7*2 = 82.
* plazo 14: llega el 04/11; 14 dias previos consumen 10 y pierden 18; del 04/11 al 30/11 hay 27 dias: 27*2 + 14 = 68.
* producto con 40: plazo 7 => S = 40-14 = 26, compra 82-26 = 56; plazo 14 => S = 40-28 = 12, compra 68-12 = 56.
"""
from __future__ import annotations

from datetime import date, timedelta
from fractions import Fraction as F

import pytest

from pipeline.plan import engine, store
from tests.plan import helpers_plan as h
from tests.publish.helpers import temp_db

pytestmark = pytest.mark.mongo


@pytest.fixture()
def db():
    with temp_db() as database:
        h.seed_all(database)
        h.seed_v2(database)
        yield database


def gen_v2(db, **kw):
    raw = {**h.RAW_V2, **kw.pop("raw", {})}
    return store.generate_plan(db, raw, **kw)


def res(db, plan_id, pid):
    return db.plan_results.find_one({"plan_id": plan_id, "producto_id": pid}, {"_id": 0})


def head(db, plan_id):
    return db.plan_runs.find_one({"plan_id": plan_id}, {"_id": 0})


# ------------------------------------------------------------------ seleccion del snapshot
def test_default_snapshot_is_reconstructed_current_else_informed(db):
    sn = store.get_snapshot(db)
    assert sn["snapshot_id"] == h.REC_SNAPSHOT_ID and store.snapshot_kind(sn) == "RECONSTRUIDO"
    assert store.count_date_of(sn) == date(2026, 10, 20)
    assert store.get_snapshot(db, h.SNAPSHOT_ID)["snapshot_id"] == h.SNAPSHOT_ID           # el informado, por id
    assert store.snapshot_kind(store.get_snapshot(db, h.SNAPSHOT_ID)) == "INFORMADO"
    assert len(store.snapshot_items(db, h.REC_SNAPSHOT_ID)) == 7                           # 1000005 (sin cantidad) no existe en v2
    assert len(store.snapshot_items(db, h.SNAPSHOT_ID)) == 8
    db.inventory_reconstructed_snapshots.update_one({}, {"$set": {"status": "staging"}})
    assert store.get_snapshot(db)["snapshot_id"] == h.SNAPSHOT_ID                          # staging es invisible: vuelve el informado
    assert store.get_snapshot(db, h.REC_SNAPSHOT_ID) is None
    db.inventory_reconstructed_snapshots.update_one({}, {"$set": {"status": "superseded"}})
    assert store.get_snapshot(db)["snapshot_id"] == h.SNAPSHOT_ID                          # solo `current` es el predeterminado
    assert store.get_snapshot(db, h.REC_SNAPSHOT_ID)["snapshot_id"] == h.REC_SNAPSHOT_ID  # superseded se lee por id
    db.inventory_reconstructed_snapshots.delete_many({})
    assert store.get_snapshot(db)["snapshot_id"] == h.SNAPSHOT_ID


# ------------------------------------------------------------------ prueba clave: 21/10 sin omitir ni duplicar dias
def test_first_simulated_day_is_21_oct_and_no_day_is_skipped_or_duplicated(db):
    pid = gen_v2(db)["plan_id"]
    hd = head(db, pid)
    assert hd["snapshot"]["snapshot_id"] == h.REC_SNAPSHOT_ID and hd["snapshot"]["as_of_local"] == "2026-10-20T23:59:59-05:00"
    assert hd["dates"]["count_date"] == "2026-10-20" and hd["dates"]["sales_cutoff"] == "2026-10-20"
    assert hd["dates"]["decision_date"] == "2026-10-21"
    for pr in ("1000001", "1000002", "1000003", "1000004", "1000007"):
        doc = res(db, pid, pr)
        for lead, arrival in (("7", "2026-10-28"), ("14", "2026-11-04")):
            sc = doc["scenarios"][lead]
            assert sc["arrival_date"] == arrival and sc["decision_date"] == "2026-10-21"
            days = [r["fecha"] for r in sc["series"]]
            assert days[0] == "2026-10-21" and days[-1] == "2026-11-30"
            assert len(days) == len(set(days)) == 41                                      # 11 dias de octubre + 30 de noviembre
            exp = [(date(2026, 10, 21) + timedelta(days=k)).isoformat() for k in range(41)]
            assert days == exp                                                           # consecutivos, sin saltos ni repetidos
            assert {"2026-10-31", "2026-11-01"} <= set(days)                              # el cambio de mes tampoco omite dias
            rows = {r["fecha"]: r for r in sc["series"]}
            assert rows["2026-10-21"]["inicio"] == str(doc["count_stock"]["libre"])        # inicio del 21/10 = existencia de cierre
            for a, b in zip(sc["series"], sc["series"][1:], strict=False):
                assert F(a["fin"]) == F(b["inicio"])                                      # el cierre de un dia es el inicio del siguiente
            ev = {e["type"]: e for e in sc["events"]}
            assert ev["CONTEO"]["date"] == "2026-10-20" and ev["DECISION_ORDEN"]["date"] == "2026-10-21"
            assert ev["LLEGADA_ORDEN"]["date"] == arrival


def test_hand_case_small_numbers(db):
    pid = gen_v2(db)["plan_id"]
    a = res(db, pid, "1000003")                                   # existencia 10, m = 2
    assert a["forecast"]["daily_exact"] == "2" and a["forecast"]["window_start"] == "2026-09-23"
    s7, s14 = a["scenarios"]["7"], a["scenarios"]["14"]
    assert (s7["purchase_qty"], s14["purchase_qty"]) == (82, 68)
    assert (s7["consumed_before_arrival"], s7["shortage_before_arrival"], s7["stock_at_arrival"]) == ("10", "4", "0")
    assert (s14["consumed_before_arrival"], s14["shortage_before_arrival"], s14["stock_at_arrival"]) == ("10", "18", "0")
    ser = {r["fecha"]: r for r in s7["series"]}
    assert [ser[d]["fin"] for d in ("2026-10-21", "2026-10-22", "2026-10-23", "2026-10-24", "2026-10-25")] == ["8", "6", "4", "2", "0"]
    assert (ser["2026-10-26"]["faltante"], ser["2026-10-27"]["faltante"]) == ("2", "2")
    assert (ser["2026-10-28"]["inicio"], ser["2026-10-28"]["recepciones"], ser["2026-10-28"]["fin"]) == ("0", "82", "80")
    assert s7["breakdown"]["total_need"] == "82" and s7["end_stock"] == "14"
    b = res(db, pid, "1000001")                                   # existencia 40
    assert (b["scenarios"]["7"]["purchase_qty"], b["scenarios"]["14"]["purchase_qty"]) == (56, 56)
    assert (b["scenarios"]["7"]["stock_at_arrival"], b["scenarios"]["14"]["stock_at_arrival"]) == ("26", "12")
    assert res(db, pid, "1000002")["scenarios"]["7"]["purchase_qty"] == 0
    assert head(db, pid)["counts"]["products"] == 7


def test_engine_hand_case_without_database():
    c = engine.calc_scenario(m=F(2), libre=10, count_date=date(2026, 10, 20), decision_date=date(2026, 10, 21), lead=7,
                             reserve_days=7, min_order=1, order_multiple=1, month_start=date(2026, 11, 1),
                             month_end=date(2026, 11, 30), kind="RECONSTRUIDO")
    assert c["rows"][0].day == date(2026, 10, 21) and c["rows"][0].inicio == 10 and c["arrival_date"] == date(2026, 10, 28)
    assert c["qty"] == 82
    d = engine.calc_scenario(m=F(2), libre=10, count_date=date(2026, 10, 20), decision_date=date(2026, 10, 21), lead=14,
                             reserve_days=7, min_order=1, order_multiple=1, month_start=date(2026, 11, 1),
                             month_end=date(2026, 11, 30))
    assert d["arrival_date"] == date(2026, 11, 4) and d["qty"] == 68


# ------------------------------------------------------------------ cabecera, textos y procedencia
def test_header_kind_provenance_confirmations_and_texts(db):
    pid = gen_v2(db)["plan_id"]
    hd = head(db, pid)
    sn = hd["snapshot"]
    assert sn["kind"] == "RECONSTRUIDO" and sn["base_count_as_of_local"] == h.AS_OF
    assert sn["last_movement_local"] == h.LAST_MOVEMENT and sn["discrepancy_products"] == ["1000003"]
    assert hd["provenance"]["initial_stock"] == "EXISTENCIA_RECONSTRUIDA_CIERRE_2026-10-20"
    conf = {c["code"]: c for c in hd["confirmations"]}
    assert list(conf) == ["COMPRAS_11452_11455", "DIFERENCIAS_INVENTARIO"]
    assert all(c["status"] == "PENDIENTE" for c in conf.values())
    assert conf["DIFERENCIAS_INVENTARIO"]["products"] == ["1000003"]
    ass = {a["code"]: a for a in hd["assumptions"]}
    assert ass["PEDIDOS_PENDIENTES"]["text"] == ("No hay pedidos adicionales por recibir registrados en este plan; "
                                                 "se supone que no llegan otros (supuesto, sin confirmar con la empresa).")
    assert "configurados" in ass["PLAZOS"]["text"] and "configurado" in ass["RESERVA"]["text"]
    assert "reconstruida" in ass["SIN_MOVIMIENTOS_TRAS_CONTEO"]["text"] and "18/10" not in ass["SIN_MOVIMIENTOS_TRAS_CONTEO"]["text"]
    assert hd["dataset"]["base_dataset_id"] == h.DATASET_ID and hd["dataset"]["partial"]["used_for_forecast"] is False
    sc = res(db, pid, "1000001")["scenarios"]["7"]
    assert "17:00" not in " ".join(s["text"] for s in sc["explanation"]) and "17:00" not in " ".join(e["note"] for e in sc["events"])
    assert sc["explanation"][0]["label"] == "Existencia inicial (cierre)"
    assert sc["events"][0]["note"] == "Existencia reconstruida al cierre del día"


def test_pending_orders_declared_keep_the_declared_text_and_no_purchases_are_added(db):
    raw = {"pending_orders": [{"producto_id": "1000003", "units": 6, "arrival_date": "2026-10-30", "nature": "REPORTADA"}]}
    pid = gen_v2(db, raw=raw)["plan_id"]
    ass = {a["code"]: a for a in head(db, pid)["assumptions"]}
    assert ass["PEDIDOS_PENDIENTES"]["nature"] == "DECLARADO"
    assert res(db, pid, "1000001")["pending_orders"] == []                              # 11452/11455 nunca se suman solas


def test_stock_provenance_per_product(db):
    pid = gen_v2(db)["plan_id"]
    ok = res(db, pid, "1000001")["stock_provenance"]
    assert ok == {"kind": "RECONSTRUIDO", "base_count": 37, "movements_net_to_closing": 3, "discrepancy": None}
    bad = res(db, pid, "1000003")["stock_provenance"]
    assert bad["base_count"] == 7 and bad["movements_net_to_closing"] == 3
    assert bad["discrepancy"] == {"difference": -3, "system_stock": 7, "reconstructed": 10, "compared_at_local": h.LAST_MOVEMENT}
    assert res(db, pid, "1000004")["stock_provenance"]["movements_net_to_closing"] == 0
    assert res(db, pid, "1000003")["count_stock"] == {"libre": 10, "as_of_local": h.REC_AS_OF}
    # la diferencia NO ajusta cantidades: el stock inicial sigue siendo el reconstruido (10), no el del sistema (7)
    assert res(db, pid, "1000003")["scenarios"]["7"]["series"][0]["inicio"] == "10"


# ------------------------------------------------------------------ retrocompatibilidad v1
def test_v1_plan_keeps_identity_texts_and_has_no_v2_fields(db):
    out = store.generate_plan(db, h.RAW, dataset_id=h.DATASET_ID, snapshot_id=h.SNAPSHOT_ID)
    pid = out["plan_id"]
    assert pid.startswith("plan-2026-11-d20261018-")
    hd = head(db, pid)
    assert hd["snapshot"]["kind"] == "INFORMADO" and "confirmations" not in hd and "last_movement_local" not in hd["snapshot"]
    assert hd["provenance"]["initial_stock"] == f"CONTEO_REPORTADO_{h.AS_OF}"
    ass = {a["code"]: a for a in hd["assumptions"]}
    assert ass["PEDIDOS_PENDIENTES"]["text"] == "En este escenario no llegan otros pedidos (0 asumido; no es un dato informado por la empresa)."
    assert ass["SIN_MOVIMIENTOS_TRAS_CONTEO"]["text"].startswith("No hay movimientos después del conteo del 18/10")
    assert ass["PLAZOS"]["text"] == "Plazos de entrega supuestos en días naturales: 7, 14."
    doc = res(db, pid, "1000001")
    assert "stock_provenance" not in doc
    sc = doc["scenarios"]["7"]
    assert sc["series"][0]["fecha"] == "2026-10-19" and sc["explanation"][0]["label"] == "Stock del conteo"
    assert sc["explanation"][0]["text"] == "Stock libre reportado el 18/10/2026 a las 17:00."
    assert sc["events"][0]["note"] == "Stock libre reportado (17:00)"
    assert store.generate_plan(db, h.RAW, dataset_id=h.DATASET_ID, snapshot_id=h.SNAPSHOT_ID)["action"] == "reused"
