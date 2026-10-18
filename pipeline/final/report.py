# ruff: noqa: ISC004
"""T12: reporte versionable (sin datos comerciales por entidad) a partir de los artefactos privados ya calculados.

El texto de lectura se genera con las cifras reales y las reglas de lectura congeladas: no contiene conclusiones
escritas de antemano ni promete umbrales."""
from __future__ import annotations

import json
from pathlib import Path

from pipeline.final import core
from pipeline.final.runner import (
    ROOT,
    FinalGateError,
    StateFile,
    env_info,
    git,
    now_lima,
    sha_bytes,
)

POL = core.POLICIES


def _f(v, nd=3):
    return "n/e" if v is None else (f"{v:.{nd}f}" if isinstance(v, float) else str(v))


def _rec(recs, cohorte, metodo, vista):
    return next((r for r in recs if (r["cohorte"], r["metodo"], r["vista"]) == (cohorte, metodo, vista)), None)


def primary_reading(pred: dict, rule: dict) -> dict:
    """Hallazgo primario: WAPE acumulado H14, SKU, cohorte primaria, universo comun; RF vs promedio_28 y control cero."""
    g = lambda m, k="WAPE": (_rec(pred["sku"], "primaria", m, "acum14") or {}).get(k)
    wr, wc, w0 = g("promedio_28"), g("rf_distribuido"), g("cero")
    rel = None if (not wr or wc is None) else (wr - wc) / wr
    obs, bias = g("rf_distribuido", "unidades_observadas"), g("rf_distribuido", "sesgo_acumulado")
    brel = None if not obs else bias / obs
    return {"WAPE_promedio_28": wr, "WAPE_rf_distribuido": wc, "WAPE_cero": w0, "mejora_relativa_rf_vs_promedio_28": rel,
            "sesgo_relativo_rf": brel, "sesgo_relativo_promedio_28": (None if not g("promedio_28", "unidades_observadas")
                                                                      else g("promedio_28", "sesgo_acumulado") / g("promedio_28", "unidades_observadas")),
            "referencia_sesgo_abs": rule["sesgo_relativo_maximo_abs"], "n": g("promedio_28", "n"),
            "regla_tres_folds": "no aplicable: un solo bloque; RF no puede declararse ganador por la prueba final"}


def render(pred: dict, sim: dict, man: dict, state: dict, aud: dict, cfg: dict) -> str:
    rule = {"sesgo_relativo_maximo_abs": 0.25}
    pr = primary_reading(pred, rule)
    L = ["# T12 Resultados: evaluación final de agosto bajo selección congelada", "",
         f"**{core.LABEL}.** Generado el {now_lima()} (America/Lima). Selección congelada: `config/seleccion_congelada.json` "
         f"(sha256 `{man['seleccion_congelada_sha256']}`), sin cambios. Predicciones iniciales selladas antes de leer agosto "
         f"(sello `{man['sello_sha256']}`). Un solo bloque (01–21/08, origen 31/07); **no hay umbrales prometidos** y los resultados "
         "desfavorables y el control cero se conservan. No demuestra impacto en inventario real de la empresa.", "",
         "## Hallazgo primario", "",
         f"WAPE acumulado H=14, SKU-almacén, cohorte primaria, universo común (n={pr['n']}): "
         f"**promedio_28 {_f(pr['WAPE_promedio_28'], 4)}**, RF categoría distribuido {_f(pr['WAPE_rf_distribuido'], 4)}, "
         f"control cero {_f(pr['WAPE_cero'], 4)}. Mejora relativa de RF frente a promedio_28: {_f(pr['mejora_relativa_rf_vs_promedio_28'], 4)} "
         f"(positiva = RF mejor). Sesgo/observado: RF {_f(pr['sesgo_relativo_rf'], 3)}, promedio_28 {_f(pr['sesgo_relativo_promedio_28'], 3)} "
         f"(referencia |sesgo|/obs ≤ 0,25). {pr['regla_tres_folds']}. El método operativo no se modifica por este resultado.", ""]
    for lvl, title, meths in (("sku", "SKU-almacén", core.SKU_METHODS), ("categoria", "Categoría (promedio_28 = suma de pronósticos SKU)", core.CAT_METHODS)):
        for cohort in ("primaria", "historia_corta"):
            for view in ("acum10", "acum14", "acum21", "diaria"):
                L += [f"### {title}: {cohort}, universo común, {view}", "",
                      "| Método | n | MAE | RMSE | WAPE | Sesgo (pred−obs) | Unidades obs. | Sub/Sobre | MAPE (cobertura de reales > 0) | R² |",
                      "|---|---|---|---|---|---|---|---|---|---|"]
                for m in meths:
                    x = _rec(pred[lvl], cohort, m, view)
                    if x and x.get("n"):
                        L.append(f"| {m} | {x['n']} | {_f(x['MAE'])} | {_f(x['RMSE'])} | {_f(x['WAPE'], 4)} | {_f(x['sesgo_acumulado'], 1)} | "
                                 f"{x['unidades_observadas']:.0f} | {x['prop_subpronostico']:.3f}/{x['prop_sobrepronostico']:.3f} | "
                                 f"{_f(x['MAPE'], 4)} ({x['MAPE_cobertura_reales_positivos']:.3f}) | {_f(x['R2'])} |")
                L.append("")
    u, n = pred["universo"], pred["nuevos_sku"]
    L += ["### Cobertura y universo", "",
          f"- SKU conocidos al 31/07: {u['sku_conocidos']} (primaria {u['primaria']}); categorías: {u['categorias']}. "
          f"Días evaluables del bloque: {pred['dias_evaluables']}/21; no evaluables: {pred['dias_no_evaluables'] or 'ninguno'}.",
          f"- SKU nuevos con venta en el bloque (primera venta posterior al 31/07), aparte y sin historia/categoría inventadas: "
          f"{n['skus_nuevos_con_venta_en_bloque']} SKU, {n['unidades_nuevos_evaluables']:.0f} unidades "
          f"(universo conocido: {n['unidades_conocidos_evaluables']:.0f} unidades; cobertura de unidades {_f(n['cobertura_unidades_universo_conocido'], 4)}).", ""]
    for c in pred["cobertura"]["sku"]:
        L.append(f"- Universo común SKU {c['cohorte']}: {c.get('comunes', '-')} de {c.get('entidades', c.get('entidades_con_prediccion', '-'))} entidades.")
    rep = sim["reporte"]
    L += ["", "## Simulación secuencial 01–31/08 (" + core.LABEL + ")", "",
          f"Universo fijo al 31/07: {rep['universo_skus']} SKU ({rep['primaria_inicial']} primaria, {rep['historia_corta_inicial']} historia corta). "
          f"Excluidos por ser nuevos: {rep['excluidos_nuevos_skus']} SKU con {rep['excluidos_nuevos_unidades_proxy']:.0f} unidades de demanda proxy. "
          f"Costos (fuente del precio): {rep['costos']}. Fallbacks RF→promedio_28 (filas): {rep['fallback_rf_a_promedio_filas']}. "
          f"Días sin demanda conocida: {rep['dias_sin_demanda_conocida'] or 'ninguno'}. Revisiones al final de los días 1, 8, 15, 22 y 29 con matrices truncadas; "
          "costos, holding (20 %/365), lead time y seguridad son supuestos; demanda proxy exógena.", "",
          "### Escenario principal L=7, S=7 (total)", "",
          "| Política | Demanda elegible | Atendidas | Perdidas | Fill rate | Tasa días-SKU con faltante | Stock medio/día | Stock final | Pedidos (uds.) | Tránsito final | Holding sup. | Compras desembolsadas sup. | Costo consumido sup. |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    R = sim["resultados"]
    for pol in POL:
        t = R[f"L7_S7|{pol}"]["total"]
        L.append(f"| {pol} | {t['demanda_proxy_elegible_unidades']:.0f} | {t['atendidas_unidades']:.0f} | {t['perdidas_unidades']:.0f} | {_f(t['fill_rate'], 4)} | "
                 f"{_f(t['tasa_dias_sku_con_faltante'], 4)} | {t['stock_medio_unidades_por_dia']:.0f} | {t['stock_final_unidades']:.0f} | {t['pedidos_unidades']:.0f} | "
                 f"{t['transito_final_unidades']:.0f} | {t['holding_supuesto']:.0f} | {t['compras_desembolsadas_supuesto']:.0f} | {t['costo_consumido_supuesto']:.0f} |")
    L += ["", "### Las 27 combinaciones (total): fill rate / perdidas / stock medio / compras desembolsadas (supuesto)", "",
          "| L | S | " + " | ".join(POL) + " |", "|---|---|" + "---|" * 3]
    for Lt in (3, 7, 14):
        for S in (0, 7, 14):
            cells = []
            for pol in POL:
                t = R[f"L{Lt}_S{S}|{pol}"]["total"]
                cells.append(f"{_f(t['fill_rate'], 4)} / {t['perdidas_unidades']:.0f} / {t['stock_medio_unidades_por_dia']:.0f} / {t['compras_desembolsadas_supuesto']:.0f}")
            L.append(f"| {Lt} | {S} | " + " | ".join(cells) + " |")
    d = sim["diferencias"]
    L += ["", "### Diferencias frente a referencia fija y promedio_28 (L=7, S=7, total)", "",
          "| Política | vs | Δ fill rate | Δ perdidas (abs; rel) | Δ stock medio (rel) | Δ compras (rel) | Δ valor stock final (rel) |", "|---|---|---|---|---|---|---|"]
    for pol in POL:
        for ref in ("referencia_fija", "promedio_28"):
            if pol == ref:
                continue
            x = d[f"L7_S7|{pol}|vs_{ref}|total"]
            L.append(f"| {pol} | {ref} | {_f(x['fill_rate']['abs'], 4)} | {_f(x['perdidas_unidades']['abs'], 0)}; {_f(x['perdidas_unidades']['rel'], 3)} | "
                     f"{_f(x['stock_medio_unidades_por_dia']['rel'], 3)} | {_f(x['compras_desembolsadas_supuesto']['rel'], 3)} | {_f(x['valor_stock_final_supuesto']['rel'], 3)} |")
    L += ["", "### Servicio frente a inventario: rf_categoria_distribuido vs promedio_28, nueve escenarios (total)", "",
          "| L | S | Δ fill rate | Δ stock medio (rel) | Δ compras (rel) | Δ perdidas (rel) |", "|---|---|---|---|---|---|"]
    for Lt in (3, 7, 14):
        for S in (0, 7, 14):
            x = d[f"L{Lt}_S{S}|rf_categoria_distribuido|vs_promedio_28|total"]
            L.append(f"| {Lt} | {S} | {_f(x['fill_rate']['abs'], 4)} | {_f(x['stock_medio_unidades_por_dia']['rel'], 3)} | "
                     f"{_f(x['compras_desembolsadas_supuesto']['rel'], 3)} | {_f(x['perdidas_unidades']['rel'], 3)} |")
    L += ["", "Una ventaja de servicio acompañada de más stock o más compras no se presenta como mejora; el desembolso y el costo consumido se muestran por separado y "
          "no se calcula ahorro ni utilidad.", "", "### Escenario principal por cohorte inicial", "",
          "| Cohorte | Política | Demanda elegible | Fill rate | Perdidas | Stock medio/día | Compras desembolsadas |", "|---|---|---|---|---|---|---|"]
    for part in ("primaria", "historia_corta"):
        for pol in POL:
            t = R[f"L7_S7|{pol}"][part]
            L.append(f"| {part} | {pol} | {t['demanda_proxy_elegible_unidades']:.0f} | {_f(t['fill_rate'], 4)} | {t['perdidas_unidades']:.0f} | "
                     f"{t['stock_medio_unidades_por_dia']:.0f} | {t['compras_desembolsadas_supuesto']:.0f} |")
    L += ["", "### Revisiones: pesos y conservación categoría→SKU", "", "| Origen | Cat. peso 28d / hist. / uniforme | Conservación | Hash del pronóstico |", "|---|---|---|---|"]
    for v in rep["revisiones"]:
        w = v["pesos"]
        L.append(f"| {v['dia']} | {w['categorias_peso_28d']}/{w['categorias_fallback_historico']}/{w['categorias_fallback_uniforme']} | "
                 f"{v['conservacion_cat_a_sku']:.1e} | `{v['hash_pronostico'][:16]}` |")
    L += ["", "## Verificaciones y auditoría", "",
          f"- Auditoría separada (recomputa desde predicciones selladas y reales guardados, sin reentrenar): **{'aprobada' if aud['ok'] else 'NO aprobada'}**; "
          f"{aud['simulacion']['combinaciones']} combinaciones con balances re-verificados; identidad de valor máx. {sim['identidad_valor_max_abs']:.2e}.",
          f"- Sello anterior a la lectura de agosto: {aud['sello_anterior_a_lectura_agosto']}. Fingerprint de entrenamiento: `{man['fingerprint_entrenamiento']}`.",
          "- Fases de cálculo: " + ", ".join(f"{k}={v.get('estado')}" for k, v in state["fases"].items() if k not in ("auditoria", "reporte")) + ".", "",
          "## Limitaciones", "",
          "- Un solo bloque de 21 días: sin intervalo de confianza ni prueba de tres folds; los resultados no son extrapolables por sí solos.",
          "- Demanda proxy = ventas observadas, posiblemente censuradas por stock real desconocido; sin backorders.",
          "- Inventario, costos, holding, lead time y seguridad son supuestos; no hay MOQ ni proveedores reales; un almacén.",
          "- Catálogo de categorías al 31/07, sin corregirlo con agosto; SKU nuevos informados aparte.",
          "- La simulación no demuestra impacto en la MYPE ni autoriza compras. El paquete es local y privado: no está publicado ni desplegado."]
    return "\n".join(L) + "\n"


def build_manifest(out: Path, man: dict, state: dict, aud: dict) -> dict:
    files = {}
    for n in ("preparacion/predicciones_fijas.npz", "preparacion/inicializacion_sim.npz", "preparacion/rf_categoria_T12.joblib",
              "reales_bloque.npz", "ventas_agosto_min.csv.gz", "predictivo.json", "simulacion.json", "simulacion_series.npz", "auditoria.json"):
        p = out / n
        if p.exists():
            files[n] = {"bytes_sha256": sha_bytes(p), "bytes": p.stat().st_size}
    return {"version": "t12-1", "generado_lima": now_lima(), "git_commit": git("rev-parse", "HEAD"), "entorno": env_info(),
            "sello_sha256": man["sello_sha256"], "seleccion_congelada_sha256": man["seleccion_congelada_sha256"],
            "documento_congelado_sha256": man["documento_congelado_sha256"], "config_t07_sha256": man["config_t07_sha256"],
            "motor_congelado_sha256": man["motor_congelado_sha256"], "codigo_vivo_no_coincide": man["codigo_vivo_no_coincide"],
            "fingerprint_entrenamiento": man["fingerprint_entrenamiento"], "fuentes": man["fuentes"], "semilla_rf": man["semilla_rf"],
            "agosto": {k: state["fases"]["lectura_agosto"].get(k) for k in ("filas", "primera", "ultima", "unidades", "bytes_sha256", "inicio", "fin")},
            "fases": state["fases"], "eventos": state["eventos"], "auditoria_ok": aud["ok"],
            "artefactos_privados": files, "etiqueta": core.LABEL, "publicado": False, "desplegado": False,
            "nota": "Los artefactos con datos y modelos permanecen en artifacts/private/final (fuera de Git)."}


def _write_text_atomic(path: Path, text: str) -> None:
    """Escritura atomica: archivo temporal en el mismo directorio y reemplazo."""
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _dump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=1, default=str) + "\n"


def _invalidate_manifest(docs: Path, exc: BaseException) -> None:
    """Un manifiesto previo no puede seguir afirmando un reporte completo si este intento fallo: se marca no valido
    (mejor esfuerzo; el estado de verdad es `estado.json`)."""
    p = Path(docs) / "T12_MANIFIESTO.json"
    try:
        if p.exists():
            m = json.loads(p.read_text(encoding="utf-8"))
            m["valido"] = False
            m.setdefault("fases", {}).setdefault("reporte", {})["estado"] = "error"
            m["error_reporte"] = f"{type(exc).__name__}: {str(exc)[:200]}"
            _write_text_atomic(p, _dump(m))
    except Exception:  # noqa: BLE001, S110 - best effort; no oculta la excepcion original
        pass


def write_report(out: Path, docs: Path = ROOT / "docs") -> dict:
    """Fase `reporte`: exige la auditoria aprobada; TODO el cierre (relectura, resultados, metricas, manifiesto y estado)
    esta bajo control de error. Un fallo en cualquier punto, incluso despues de marcar la fase, deja `reporte=error`,
    `completa=false` y un manifiesto previo marcado no valido; nunca un paquete completo con manifiesto contradictorio."""
    out, docs = Path(out), Path(docs)
    store = StateFile(out)
    store._begin("reporte")
    try:
        if not store.done("auditoria") or not json.loads((out / "auditoria.json").read_text(encoding="utf-8")).get("ok"):
            raise FinalGateError("el reporte exige la auditoria completa y aprobada")
        pred = json.loads((out / "predictivo.json").read_text(encoding="utf-8"))
        sim = json.loads((out / "simulacion.json").read_text(encoding="utf-8"))
        man = json.loads((out / "preparacion" / "manifiesto_preparacion.json").read_text(encoding="utf-8"))
        aud = json.loads((out / "auditoria.json").read_text(encoding="utf-8"))
        cfg = json.loads((ROOT / "config" / "seleccion_congelada.json").read_text(encoding="utf-8"))
        text = render(pred, sim, man, store.state, aud, cfg)
        metrics = {"predictivo": pred, "simulacion": sim, "hallazgo_primario": primary_reading(pred, {"sesgo_relativo_maximo_abs": 0.25}),
                   "auditoria_resumen": {"ok": aud["ok"], "combinaciones": aud["simulacion"]["combinaciones"]}, "etiqueta": core.LABEL}
        _write_text_atomic(docs / "T12_RESULTADOS.md", text)
        _write_text_atomic(docs / "T12_METRICAS.json", _dump(metrics))
        store._end("reporte", resultados_sha256=sha_bytes(docs / "T12_RESULTADOS.md"),
                   metricas_sha256=sha_bytes(docs / "T12_METRICAS.json"))
        # el manifiesto versionado refleja el estado final (siete fases) y se escribe al final, de forma atomica
        manifest = build_manifest(out, man, store.state, aud)
        manifest["correcciones"] = store.state.get("correcciones", [])
        manifest["valido"] = True
        _write_text_atomic(docs / "T12_MANIFIESTO.json", _dump(manifest))
        return manifest
    except BaseException as exc:
        try:
            store._fail("reporte", exc)
        finally:
            _invalidate_manifest(docs, exc)
        raise
