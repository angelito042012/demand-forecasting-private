# ruff: noqa: ISC004  (texto de informe en listas de lineas)
"""T04: perfil de calidad, diccionario, series diarias marzo-julio y firma del dataset.

Uso: python -m scripts.build_t04 [--db demand_forecasting_v2] [--out artifacts/private/t04]
Lee SOLO a traves de load_training_data (fuentes aprobadas, corte 2026-07-31, sin agosto).
Escribe los datos comerciales en --out (ignorado por Git) y los documentos agregados
(sin lineas individuales) en docs/: T04_PERFIL_CALIDAD.md, T04_DICCIONARIO.md, T04_FIRMA.json.
No entrena ni genera features.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from pipeline.data import daily_series as ds
from pipeline.data.calendar import EXCLUDED_DATES, TIMEZONE
from pipeline.data.importer import get_client, sha256_file
from pipeline.data.training_access import load_training_data

CUTOFF = date(2026, 7, 31)
NEW_PRODUCT_AFTER = date(2026, 3, 29)   # primera venta posterior: producto probablemente nuevo (heuristica)
DOCS = Path("docs")

DICTIONARY = {
    "series_sku_almacen_diaria.csv.gz": [
        ("fecha", "texto YYYY-MM-DD", "Dia natural (America/Lima). Calendario sin comprimir."),
        ("sku", "texto", "ID_ARTICULO del Excel."),
        ("almacen", "texto", "ID_ALMACEN del Excel (en marzo-julio solo existe '1')."),
        ("categoria_corte", "texto", "Categoria del catalogo versionado al corte 2026-07-31 (DESCONOCIDA si no hay). categoria_original no se modifica en la base."),
        ("estado", "VENTA_OBSERVADA | CERO_OBSERVADO | EXCLUIDO_MASCARA | SIN_REGISTROS_DIA", "VENTA_OBSERVADA: hay al menos una linea de venta. CERO_OBSERVADO: sin venta desde la primera observacion del par; es un cero de venta observada, NO prueba ausencia de demanda ni stock disponible. EXCLUIDO_MASCARA: 03/04, 12/04 y 07/06 de 2026; cantidad vacia, fuera de entrenamiento y metricas. SIN_REGISTROS_DIA: dia no enmascarado sin ninguna linea en las fuentes; cantidad vacia, no es cero (no ocurre en marzo-julio). Ambos estados se conservan en el agregado por categoria."),
        ("cantidad_base", "decimal", "Suma de CANTIDAD_UM_BASE de lineas de venta (TIPO_DOC distinto de 7, importe > 0). Unidad base (todas UND en marzo-julio). Vacio en EXCLUIDO_MASCARA. Excluye notas de credito."),
        ("n_lineas", "entero", "Numero de lineas de venta del dia (0 en cero observado, vacio si mascara)."),
        ("importe_centimos", "entero", "Suma de TOTAL_LINEA de ventas en centimos de sol (exacto, sin coma flotante)."),
        ("dias_desde_primera_obs", "entero", "0 en la primera venta observada del par; la serie empieza ahi (los dias anteriores no se rellenan)."),
    ],
    "series_categoria_diaria.csv.gz": [
        ("fecha / categoria_corte / estado", "ver arriba", "La serie de cada categoria empieza en su primera venta observada. estado=CERO_OBSERVADO si ninguna linea de la categoria ese dia."),
        ("cantidad_base_suma_heterogenea", "decimal", "Suma de cantidades en unidad base de SKU distintos; orientativa, no comparable en volumen fisico."),
        ("n_lineas, n_sku_con_venta, importe_centimos", "entero", "Lineas, SKU distintos con venta e importe del dia."),
    ],
    "intermitencia_sku_almacen.csv": [
        ("dias, dias_con_venta, unidades", "numerico", "Sobre dias no enmascarados desde la primera observacion."),
        ("adi", "decimal", "Intervalo medio entre demandas = dias / dias_con_venta."),
        ("cv2", "decimal", "Coeficiente de variacion al cuadrado de tamanos no nulos (vacio con una sola venta)."),
        ("proporcion_ceros", "decimal", "Ceros observados / dias."),
        ("clase_sbc", "texto", "Syntetos-Boylan: ADI<1,32 y CV2<0,49 SUAVE; ADI<1,32 y CV2>=0,49 ERRATICA; ADI>=1,32 y CV2<0,49 INTERMITENTE; resto IRREGULAR_LUMPY; UNA_SOLA_VENTA aparte. Descriptivo, no selecciona modelos."),
    ],
}


def _git(*args) -> str:
    try:
        return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout.strip()
    except Exception:  # noqa: BLE001 - la firma debe generarse aunque Git no responda
        return "desconocido"


def _q(s: pd.Series, qs=(0, .1, .25, .5, .75, .9, 1)) -> dict:
    return {f"p{int(q * 100)}": round(float(s.quantile(q)), 2) for q in qs}


def profile(data, df, pairs, cats, inter, db) -> dict:
    cal = [d.isoformat() for d in data.calendar]
    mask = {d.isoformat() for d in EXCLUDED_DATES}
    by_day = df.groupby(df["fecha"].dt.strftime("%Y-%m-%d")).size()
    no_sales = [d for d in cal if d not in by_day.index and d not in mask]
    df["mes"] = df["fecha"].dt.strftime("%Y-%m")
    months = {}
    for m, g in df.groupby("mes"):
        month_days = [d for d in cal if d.startswith(m)]
        months[m] = {"lineas": len(g), "sku": int(g["sku"].nunique()), "unidades": float(g["qty"].sum()),
                     "importe": round(float(g["centimos"].sum()) / 100, 2),
                     "dias_calendario": len(month_days),
                     "dias_con_venta": int(sum(1 for d in month_days if d in by_day.index)),
                     "dias_sin_registro_no_mascara": [d for d in month_days if d not in by_day.index and d not in mask],
                     "dias_enmascarados": [d for d in month_days if d in mask]}
    first = pairs.loc[pairs["dias_desde_primera_obs"] == 0].copy()
    first["f"] = pd.to_datetime(first["fecha"])
    hist = (pd.Timestamp(CUTOFF) - first["f"]).dt.days + 1
    first_by_month = first["f"].dt.strftime("%Y-%m").value_counts().sort_index().to_dict()
    nuevos = int((first["f"] > pd.Timestamp(NEW_PRODUCT_AFTER)).sum())
    non_mask = pairs[~pairs["estado"].isin(ds.NO_USABLE)]
    zero_share = float((non_mask["estado"] == ds.CERO).mean())
    long_hist = first.loc[hist >= 56, ["sku", "almacen"]]
    nm_long = non_mask.merge(long_hist, on=["sku", "almacen"])
    cls = inter["clase_sbc"].value_counts().to_dict()
    units_by_cls = (inter.groupby("clase_sbc")["unidades"].sum() / inter["unidades"].sum()).round(4).to_dict()
    cat_per_sku = df.groupby("sku")["cat_orig"].nunique()
    cat_mismatch = int(sum(1 for s, c in zip(df["sku"], df["cat_orig"], strict=True)
                           if data.catalog.get(s) != c))
    credit_months = {g["_id"]: {"lineas": g["n"], "importe": float(g["s"].to_decimal())}
                     for g in db.credit_notes.aggregate([
                         {"$match": {"fecha": {"$lte": CUTOFF.isoformat()}}},
                         {"$group": {"_id": "$mes", "n": {"$sum": 1}, "s": {"$sum": "$importe"}}}])}
    return {
        "fuentes": {"manifiesto": list(data.sources.manifest), "meses_requeridos": list(data.sources.required_months),
                    "problemas": list(data.sources.issues)},
        "totales": {"lineas_venta": len(df), "filas_omitidas_por_mascara": data.omitted_excluded_rows,
                    "sku": int(df["sku"].nunique()), "pares_sku_almacen": len(first),
                    "almacenes": sorted(df["almacen"].unique().tolist()),
                    "categorias_catalogo": len(set(data.catalog.values())),
                    "dias_calendario": len(cal), "dias_enmascarados": len(data.excluded_days),
                    "dias_sin_registro_no_mascara": no_sales,
                    "filas_en_dias_enmascarados_omitidas": data.omitted_excluded_rows},
        "meses": months,
        "unidades": {"unidad_base": df["unidad"].value_counts().to_dict(),
                     "cantidades_no_enteras": int((df["qty"] % 1 != 0).sum()),
                     "cantidad_por_linea": _q(df["qty"]), "sku_con_varias_unidades": int((df.groupby("sku")["unidad"].nunique() > 1).sum())},
        "primera_observacion": {"pares_por_mes": first_by_month,
                                "primera_venta_posterior_al_29_marzo": nuevos,
                                "historia_dias": _q(hist), "historia_menor_28": int((hist < 28).sum()),
                                "historia_menor_56": int((hist < 56).sum()),
                                "historia_al_menos_90": int((hist >= 90).sum())},
        "series_densas": {"filas_par_dia": len(pairs), "venta_observada": int((pairs["estado"] == ds.VENTA).sum()),
                          "cero_observado": int((pairs["estado"] == ds.CERO).sum()),
                          "excluido_mascara": int((pairs["estado"] == ds.MASCARA).sum()),
                          "proporcion_cero_observado_dias_usables": round(zero_share, 4),
                          "proporcion_cero_en_pares_con_historia_al_menos_56": round(float((nm_long["estado"] == ds.CERO).mean()), 4),
                          "filas_categoria_dia": len(cats)},
        "intermitencia": {"pares_por_clase": cls, "participacion_unidades_por_clase": units_by_cls,
                          "adi": _q(inter["adi"]), "proporcion_ceros": _q(inter["proporcion_ceros"]),
                          "dias_con_venta": _q(inter["dias_con_venta"])},
        "categorias": {"sku_con_mas_de_una_categoria_original": int((cat_per_sku > 1).sum()),
                       "lineas_con_categoria_original_distinta_a_catalogo_corte": cat_mismatch,
                       "sku_desconocida": int(sum(1 for v in data.catalog.values() if v == "DESCONOCIDA")),
                       "lineas_sin_categoria": int((df["cat_orig"] == "").sum()),
                       "sku_16140041": data.catalog.get("16140041")},
        "notas_credito_informativas_hasta_corte": credit_months,
    }


def render_profile(p: dict, sig: dict) -> str:
    t, s, ser, it, pr = p["totales"], p["fuentes"], p["series_densas"], p["intermitencia"], p["primera_observacion"]
    L = ["# T04 Perfil de calidad (marzo-julio 2026)", "",
         f"Generado el {sig['generado_lima']} (America/Lima). Dataset: `{sig['fingerprint_entrenamiento'][:16]}...` "
         "(firma completa en T04_FIRMA.json). Solo marzo-julio; agosto no se uso. Cifras agregadas medidas por "
         "scripts/build_t04.py; nada aqui es un resultado de modelo.", "",
         "## Fuentes y cobertura", "",
         f"- Fuentes aprobadas usadas: {len(s['manifiesto'])} ({', '.join(m['archivo'] for m in s['manifiesto'])}); "
         f"meses requeridos {', '.join(s['meses_requeridos'])}; problemas de fuente: {len(s['problemas'])}.",
         f"- Lineas de venta: {t['lineas_venta']}; SKU: {t['sku']}; pares SKU-almacen: {t['pares_sku_almacen']}; "
         f"almacenes: {t['almacenes']}; categorias en catalogo al corte: {t['categorias_catalogo']}.",
         f"- Calendario natural: {t['dias_calendario']} dias, {t['dias_enmascarados']} enmascarados (03/04, 12/04, 07/06). "
         f"Filas de venta omitidas por mascara: {t['filas_omitidas_por_mascara']}. "
         f"Dias sin ningun registro y no enmascarados: {t['dias_sin_registro_no_mascara'] or 'ninguno'}. "
         f"Filas en dias enmascarados: {t['filas_en_dias_enmascarados_omitidas']} (filas de venta fechadas en dias enmascarados halladas en la base).", "",
         "| Mes | Lineas | SKU | Unidades | Importe (S/) | Dias con venta / calendario | Sin registro (no masc.) | Enmascarados |",
         "|---|---|---|---|---|---|---|---|"]
    for m, v in p["meses"].items():
        L.append(f"| {m} | {v['lineas']} | {v['sku']} | {v['unidades']:.0f} | {v['importe']:.2f} | "
                 f"{v['dias_con_venta']}/{v['dias_calendario']} | {v['dias_sin_registro_no_mascara'] or '-'} | {v['dias_enmascarados'] or '-'} |")
    L += ["", "## Unidades", "",
          f"- unidad_base: {p['unidades']['unidad_base']}; cantidades no enteras: {p['unidades']['cantidades_no_enteras']}; "
          f"SKU con varias unidades: {p['unidades']['sku_con_varias_unidades']}. Cantidad por linea: {p['unidades']['cantidad_por_linea']}.", "",
          "## Inicio de historia por producto", "",
          f"- Primera venta observada por mes (pares): {pr['pares_por_mes']}. Se desconoce la historia previa a marzo: las series "
          "con primera venta en las primeras semanas pueden estar truncadas por la izquierda, no ser productos nuevos.",
          f"- Pares con primera venta posterior al 29/03 (probables altas, heuristica): {pr['primera_venta_posterior_al_29_marzo']}.",
          f"- Dias de historia hasta el corte (cuantiles): {pr['historia_dias']}; <28 dias: {pr['historia_menor_28']}; "
          f"<56 dias: {pr['historia_menor_56']}; >=90 dias: {pr['historia_al_menos_90']}.", "",
          "## Ceros e intermitencia", "",
          f"- Series densas: {ser['filas_par_dia']} filas par-dia = {ser['venta_observada']} con venta + {ser['cero_observado']} "
          f"cero observado + {ser['excluido_mascara']} enmascaradas. Proporcion de cero observado sobre dias usables: "
          f"{ser['proporcion_cero_observado_dias_usables']}; en pares con >=56 dias de historia: "
          f"{ser['proporcion_cero_en_pares_con_historia_al_menos_56']}.",
          "- Un cero observado es venta observada cero desde la primera observacion; la venta puede estar censurada por "
          "stock desconocido, asi que no se interpreta como ausencia de demanda.",
          f"- Clase Syntetos-Boylan (pares): {it['pares_por_clase']}; participacion de unidades por clase: "
          f"{it['participacion_unidades_por_clase']}.",
          f"- ADI (cuantiles): {it['adi']}; proporcion de ceros: {it['proporcion_ceros']}; dias con venta: {it['dias_con_venta']}.", "",
          "## Categorias", "",
          f"- SKU con mas de una categoria original en marzo-julio: {p['categorias']['sku_con_mas_de_una_categoria_original']}; "
          f"lineas cuya categoria original difiere del catalogo al corte: "
          f"{p['categorias']['lineas_con_categoria_original_distinta_a_catalogo_corte']}; lineas sin categoria: "
          f"{p['categorias']['lineas_sin_categoria']}; SKU 16140041 en catalogo: {p['categorias']['sku_16140041']}.", "",
          "## Notas de credito (informativo, fuera del objetivo)", "",
          f"Hasta el corte: {p['notas_credito_informativas_hasta_corte']}. Separadas de ventas brutas; no implican devolucion fisica.", "",
          "## Limites", "",
          "- Un unico almacen y una unica unidad base en este periodo: no se ha probado manejo multialmacen ni de equivalencias.",
          "- Cobertura de 5 meses: no permite estacionalidad anual; el patron semanal si es observable.",
          "- La serie por categoria suma unidades heterogeneas (solo orientativa).",
          "- No hay inventario real: no se puede separar demanda de venta censurada por faltante."]
    return "\n".join(L) + "\n"


def render_dictionary() -> str:
    L = ["# T04 Diccionario de datos derivados", "",
         "Archivos en `artifacts/private/t04/` (ignorados por Git; contienen datos comerciales). Origen: ventas aprobadas de "
         "`demand_forecasting_v2` con corte 2026-07-31 via `load_training_data`. Hash en T04_FIRMA.json.", ""]
    for f, cols in DICTIONARY.items():
        L += [f"## {f}", "", "| Campo | Tipo | Significado |", "|---|---|---|"]
        L += [f"| {c} | {t} | {d} |" for c, t, d in cols] + [""]
    L += ["## Campos de origen (coleccion sales, esquema v2)", "",
          "linea_id (identidad normalizada), fecha, sku, almacen, cantidad_original/unidad_original, equivalencia, cantidad_base/unidad_base, "
          "precio_unitario_original, importe (Decimal128), categoria_original, doc_hash, pedido_id, sources (procedencia: archivo, sha256, fila), "
          "tipo_doc. Notas de credito (TIPO_DOC=7) viven en credit_notes y no entran en el objetivo.", "",
          "## Transformaciones", "",
          "1. Seleccion de ventas con fuente aprobada, fecha <= 2026-07-31 (R04). 2. Agregacion por (sku, almacen, dia) con suma de cantidad_base. "
          "3. Malla densa desde la primera venta de cada par hasta el corte. 4. Ceros observados tras la primera venta; mascara de 3 dias sin cero ni "
          "compresion. 5. Categoria del catalogo al corte. Sin imputacion, sin escalado, sin features, sin rezagos."]
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="demand_forecasting_v2")
    ap.add_argument("--out", type=Path, default=Path("artifacts/private/t04"))
    args = ap.parse_args(argv)
    db = get_client()[args.db]
    data = load_training_data(db, CUTOFF)
    df = ds.sales_frame(data)
    pairs = ds.pair_daily(data, df)
    cats = ds.category_daily(pairs)
    inter = ds.intermittency(pairs)
    args.out.mkdir(parents=True, exist_ok=True)
    files = {"series_sku_almacen_diaria.csv.gz": pairs, "series_categoria_diaria.csv.gz": cats}
    manifest = {}
    for name, frame in files.items():
        (args.out / name).write_bytes(ds.to_csv_gz_bytes(frame))
        manifest[name] = {"filas": len(frame), "sha256_archivo": sha256_file(args.out / name),
                          "sha256_contenido": ds.content_sha256(frame)}
    inter.to_csv(args.out / "intermitencia_sku_almacen.csv", index=False, lineterminator="\n", float_format="%.10g")
    manifest["intermitencia_sku_almacen.csv"] = {
        "filas": len(inter), "sha256_archivo": sha256_file(args.out / "intermitencia_sku_almacen.csv")}
    sig = {
        "dataset": "T04_series_diarias_marzo_julio_2026",
        "generado_lima": datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y-%m-%d %H:%M"),
        "base_de_datos": args.db, "corte": CUTOFF.isoformat(),
        "fingerprint_entrenamiento": data.fingerprint,
        "parametros": {"mascara": sorted(d.isoformat() for d in EXCLUDED_DATES),
                       "meses_requeridos": list(data.sources.required_months),
                       "inicio_serie": "primera venta observada por (sku, almacen)", "cero": "observado tras primera venta",
                       "sbc_adi": ds.SBC_ADI, "sbc_cv2": ds.SBC_CV2, "umbral_probable_alta": NEW_PRODUCT_AFTER.isoformat(),
                       "unidad": "cantidad_base", "agosto_usado": False},
        "fuentes": list(data.sources.manifest), "archivos": manifest,
        "codigo": {"git_commit": _git("rev-parse", "HEAD"), "git_sucio": bool(_git("status", "--porcelain")),
                   "python": sys.version.split()[0], "pandas": pd.__version__, "numpy": np.__version__},
    }
    prof = profile(data, df, pairs, cats, inter, db)
    DOCS.joinpath("T04_FIRMA.json").write_text(json.dumps(sig, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    DOCS.joinpath("T04_PERFIL_CALIDAD.md").write_text(render_profile(prof, sig), encoding="utf-8")
    DOCS.joinpath("T04_DICCIONARIO.md").write_text(render_dictionary(), encoding="utf-8")
    DOCS.joinpath("T04_PERFIL_CALIDAD.json").write_text(json.dumps(prof, ensure_ascii=False, indent=2, default=str) + "\n",
                                                        encoding="utf-8")
    print(json.dumps({"fingerprint": data.fingerprint, "archivos": manifest}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
