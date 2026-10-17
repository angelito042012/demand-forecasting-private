"""R05 (REVISION_CODEX_07): casos documentados por Codex. Esta prueba FALLABA antes de la correccion
(con la media del CSV T07, de 10 cifras significativas, el objetivo de 12040025 salia 10 y no 9; registro en
artifacts/private/t08r/r05_fallo_previo.log) y ahora usa senales exactas (suma y dias)."""
import pytest

from pipeline.publish.builders import build_recommendations

from .helpers import make_catalog, make_signals, needs_artifacts, real_source

pytestmark = [pytest.mark.mongo, needs_artifacts]


def _doc(docs, sku):
    return next(d for d in docs if d["sku"] == sku)


def test_codex_cases_exact_targets():
    src = real_source()
    catalog, _ = make_catalog(src)
    docs = build_recommendations(src, catalog, "rid-repro", make_signals(src))
    a = _doc(docs, "12040025")      # suma28=12, dias=28: objetivo exacto (14+7)*12/28 = 9; posicion 9; pedido 0
    assert (a["target"], a["position"], a["order_qty"]) == (9, 9, 0)
    b = _doc(docs, "12010025")      # suma28=4, dias=28: objetivo 3; posicion 1; pedido 2
    assert (b["target"], b["position"], b["order_qty"]) == (3, 1, 2)
