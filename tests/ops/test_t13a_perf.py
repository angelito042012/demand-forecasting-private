"""R15: el medidor de rendimiento debe usar nearest-rank y NO aprobar tandas incompletas. Sin servicios: clientes sinteticos."""
from __future__ import annotations

import httpx
import pytest

from scripts import t13a_perf as p


class Resp:
    def __init__(self, status=200, size=10):
        self.status_code, self.content = status, b"x" * size


class Ok:
    def get(self, url):
        return Resp(200)


class Boom:
    def get(self, url):
        raise httpx.ConnectError("caido")


class Http500:
    def get(self, url):
        return Resp(500)


def test_nearest_rank_valores_conocidos():
    v20 = [float(i) for i in range(1, 21)]  # 1..20
    v100 = [float(i) for i in range(1, 101)]
    assert p.percentile(v20, 0.95) == 19.0   # ceil(0.95*20)=19.a
    assert p.percentile(v100, 0.95) == 95.0  # ceil(0.95*100)=95.a
    assert p.percentile(v20, 0.50) == 10.0
    assert p.percentile([5.0], 0.95) == 5.0
    assert p.percentile(list(reversed(v20)), 0.95) == 19.0  # no depende del orden de entrada


def test_cero_muestras_no_lanza_y_no_aprueba():
    assert p.percentile([], 0.95) is None
    r = p.summarize([[], []], [[], []], 20)
    assert r["completa"] is False and r["p50_ms"] is None and r["p95_ms"] is None and r["max_ms"] is None
    assert p.summarize([], [], 20)["completa"] is False


def test_tanda_sana_es_completa():
    r, m = p.run_level([Ok(), Ok(), Ok()], lambda i: f"/x?{i}", n_medidas=20, n_calentamiento=2)
    assert r["completa"] is True and r["medidas_ok"] == 60 and r["errores"] == 0 and r["por_sesion"] == [20, 20, 20]
    assert len(m["latencias_ms"]) == 3 and all(len(x) == 20 for x in m["latencias_ms"])


def test_un_hilo_que_falla_se_contabiliza_y_no_aprueba():
    r, _ = p.run_level([Ok(), Boom()], lambda i: "/x", n_medidas=20, n_calentamiento=1)
    assert r["completa"] is False
    assert r["medidas_ok"] == 20 and r["esperadas"] == 40 and r["errores"] >= 20
    assert "ConnectError" in " ".join(r["detalle_errores"])


def test_estado_no_200_cuenta_como_error():
    r, _ = p.run_level([Ok(), Http500()], lambda i: "/x", n_medidas=5, n_calentamiento=0)
    assert r["completa"] is False and r["errores"] == 5 and "estado 500" in r["detalle_errores"]


def test_tanda_vacia_no_lanza():
    r, _ = p.run_level([], lambda i: "/x")
    assert r["completa"] is False and r["p95_ms"] is None


def test_timeout_total_de_arranque(monkeypatch):
    def caido(*a, **k):
        raise httpx.ConnectError("no responde")
    monkeypatch.setattr(httpx, "get", caido)
    assert p.wait_health("https://x", verify=True, timeout_s=0.6) is None


def test_login_fallido_cierra_el_cliente(monkeypatch):
    cerrados = []

    class FakeClient:
        def __init__(self, **k):
            self.k = k

        def post(self, *a, **k):
            return Resp(401)

        def close(self):
            cerrados.append(True)
    monkeypatch.setattr(httpx, "Client", FakeClient)
    with pytest.raises(RuntimeError):
        p.login("https://x", {"username": "u", "password": "p"}, verify=True)
    assert cerrados == [True]


def test_tls_se_verifica_por_defecto(monkeypatch):
    vistos = {}

    class FakeClient:
        def __init__(self, **k):
            vistos.update(k)

        def post(self, *a, **k):
            return Resp(200)
    monkeypatch.setattr(httpx, "Client", FakeClient)
    p.login("https://x", {"username": "u", "password": "p"}, verify=True)
    assert vistos["verify"] is True
