"""Series diarias derivadas de TrainingData (T04). Sin features, sin modelos.

Reglas (DECISIONES_DATOS.md, REVISION_CODEX_02.md):
  - calendario natural [primer_dia, corte]; los dias de EXCLUDED_DATES se conservan
    como filas con estado EXCLUIDO_MASCARA y cantidad vacia (no son cero ni cierre);
  - la serie de cada (sku, almacen) EMPIEZA en su primera venta observada: los dias
    previos no se convierten en demanda cero conocida (se desconoce si el producto
    existia o estaba disponible);
  - despues de esa primera observacion, un dia sin venta es CERO_OBSERVADO: venta
    observada cero bajo cobertura valida del archivo. No afirma ausencia de demanda,
    demanda perdida ni stock disponible (la venta puede estar censurada por stock);
  - unidad: cantidad_base (unidad base del articulo); no se mezclan unidades
    entre SKU en ninguna transformacion: el agregado por categoria suma unidades
    base heterogeneas y se rotula como tal;
  - categoria: catalogo al corte (catalog.py); categoria_original no se modifica.
"""
from __future__ import annotations

import gzip
import hashlib
import io

import numpy as np
import pandas as pd

from .catalog import lookup
from .training_access import TrainingData

VENTA, CERO, MASCARA = "VENTA_OBSERVADA", "CERO_OBSERVADO", "EXCLUIDO_MASCARA"
SIN_COBERTURA = "SIN_REGISTROS_DIA"   # dia no enmascarado sin ninguna linea: no se convierte en cero
NO_USABLE = (MASCARA, SIN_COBERTURA)
SBC_ADI, SBC_CV2 = 1.32, 0.49   # umbrales de Syntetos-Boylan (clasificacion de intermitencia)
SERIES_COLUMNS = ["fecha", "sku", "almacen", "categoria_corte", "estado", "cantidad_base",
                  "n_lineas", "importe_centimos", "dias_desde_primera_obs"]
CATEGORY_COLUMNS = ["fecha", "categoria_corte", "estado", "cantidad_base_suma_heterogenea",
                    "n_lineas", "n_sku_con_venta", "importe_centimos"]


def sales_frame(data: TrainingData) -> pd.DataFrame:
    rows = []
    for r in data.sales:
        imp = r["importe"].to_decimal() if r.get("importe") is not None else None
        rows.append((r["fecha"], r["sku"], r["almacen"], float(r["cantidad_base"]),
                     None if imp is None else int(imp * 100), r.get("unidad_base", ""),
                     r.get("categoria_original", "")))
    df = pd.DataFrame(rows, columns=["fecha", "sku", "almacen", "qty", "centimos", "unidad", "cat_orig"])
    df["fecha"] = pd.to_datetime(df["fecha"])
    return df


def pair_daily(data: TrainingData, df: pd.DataFrame | None = None) -> pd.DataFrame:
    """Serie diaria densa por (sku, almacen) desde su primera venta hasta el corte."""
    df = sales_frame(data) if df is None else df
    cal = pd.DatetimeIndex(pd.to_datetime(list(data.calendar)))
    masked = {pd.Timestamp(d) for d in data.excluded_days}
    uncovered = set(cal) - masked - set(df["fecha"].unique())
    agg = (df.groupby(["sku", "almacen", "fecha"], sort=True)
             .agg(cantidad_base=("qty", "sum"), n_lineas=("qty", "size"), importe_centimos=("centimos", "sum"))
             .reset_index())
    first = agg.groupby(["sku", "almacen"])["fecha"].min().rename("primera_obs").reset_index()
    pos = {d: i for i, d in enumerate(cal)}
    first["i0"] = first["primera_obs"].map(pos)
    lens = len(cal) - first["i0"].to_numpy()
    idx = np.repeat(np.arange(len(first)), lens)
    offs = np.concatenate([np.arange(n) for n in lens])
    grid = first.iloc[idx].reset_index(drop=True)
    grid["fecha"] = cal[grid["i0"].to_numpy() + offs]
    grid["dias_desde_primera_obs"] = offs
    out = grid.merge(agg, on=["sku", "almacen", "fecha"], how="left")
    is_mask = out["fecha"].isin(masked)
    no_cov = out["fecha"].isin(uncovered)
    out["estado"] = np.where(is_mask, MASCARA, np.where(no_cov, SIN_COBERTURA,
                                                       np.where(out["cantidad_base"].notna(), VENTA, CERO)))
    out.loc[out["estado"] == CERO, ["cantidad_base", "n_lineas", "importe_centimos"]] = 0.0
    out.loc[is_mask | no_cov, ["cantidad_base", "n_lineas", "importe_centimos"]] = np.nan
    out["categoria_corte"] = out["sku"].map(lambda s: lookup(data.catalog, s))
    out["fecha"] = out["fecha"].dt.strftime("%Y-%m-%d")
    for c in ("n_lineas", "importe_centimos"):
        out[c] = out[c].astype("Int64")
    return out[SERIES_COLUMNS].sort_values(["sku", "almacen", "fecha"], kind="stable").reset_index(drop=True)


def category_daily(pairs: pd.DataFrame) -> pd.DataFrame:
    """Agregado diario por categoria al corte, desde la primera venta de la categoria.
    Suma cantidades en unidad base heterogenea: solo orientativo, no comparable entre SKU."""
    cal = sorted(pairs["fecha"].unique())
    first = pairs.loc[pairs["estado"] == VENTA].groupby("categoria_corte")["fecha"].min()
    sold = pairs.loc[pairs["estado"] == VENTA]
    g = sold.groupby(["categoria_corte", "fecha"]).agg(
        cantidad_base_suma_heterogenea=("cantidad_base", "sum"), n_lineas=("n_lineas", "sum"),
        n_sku_con_venta=("sku", "nunique"), importe_centimos=("importe_centimos", "sum")).reset_index()
    masked = set(pairs.loc[pairs["estado"].isin(NO_USABLE), "fecha"])
    rows = [(c, d) for c, f in first.items() for d in cal if d >= f]
    grid = pd.DataFrame(rows, columns=["categoria_corte", "fecha"])
    out = grid.merge(g, on=["categoria_corte", "fecha"], how="left")
    is_mask = out["fecha"].isin(masked)
    out["estado"] = np.where(is_mask, MASCARA, np.where(out["n_lineas"].notna(), VENTA, CERO))
    num = ["cantidad_base_suma_heterogenea", "n_lineas", "n_sku_con_venta", "importe_centimos"]
    out.loc[out["estado"] == CERO, num] = 0
    out.loc[is_mask, num] = np.nan
    for c in ("n_lineas", "n_sku_con_venta", "importe_centimos"):
        out[c] = out[c].astype("Int64")
    return out[CATEGORY_COLUMNS].sort_values(["categoria_corte", "fecha"], kind="stable").reset_index(drop=True)


def intermittency(pairs: pd.DataFrame, by=("sku", "almacen")) -> pd.DataFrame:
    """ADI, CV2 de tamanos no nulos y clase Syntetos-Boylan sobre dias NO enmascarados
    desde la primera observacion. Descriptivo; no se usa para seleccionar modelos."""
    use = pairs.loc[~pairs["estado"].isin(NO_USABLE)].copy()
    use["pos"] = use["cantidad_base"].astype(float) > 0
    use["q_pos"] = np.where(use["pos"], use["cantidad_base"].astype(float), np.nan)
    use["q2"] = use["q_pos"] ** 2
    g = use.groupby(list(by)).agg(dias=("pos", "size"), dias_con_venta=("pos", "sum"),
                                  unidades=("cantidad_base", "sum"), media_pos=("q_pos", "mean"),
                                  media_pos2=("q2", "mean")).reset_index()
    g["adi"] = g["dias"] / g["dias_con_venta"]
    var = (g["media_pos2"] - g["media_pos"] ** 2).clip(lower=0)
    g["cv2"] = np.where(g["dias_con_venta"] > 1, var / g["media_pos"] ** 2, np.nan)
    g["proporcion_ceros"] = 1 - g["dias_con_venta"] / g["dias"]
    cls = np.select(
        [g["dias_con_venta"] == 1, (g["adi"] < SBC_ADI) & (g["cv2"] < SBC_CV2),
         (g["adi"] < SBC_ADI) & (g["cv2"] >= SBC_CV2), (g["adi"] >= SBC_ADI) & (g["cv2"] < SBC_CV2)],
        ["UNA_SOLA_VENTA", "SUAVE", "ERRATICA", "INTERMITENTE"], default="IRREGULAR_LUMPY")
    g["clase_sbc"] = cls
    return g.drop(columns=["media_pos2"])


def to_csv_gz_bytes(df: pd.DataFrame) -> bytes:
    """CSV gzip determinista (mtime=0, saltos de linea LF, floats con repr minimo)."""
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as gz:
        gz.write(df.to_csv(index=False, lineterminator="\n", float_format="%.10g").encode("utf-8"))
    return buf.getvalue()


def content_sha256(df: pd.DataFrame) -> str:
    """Hash del CONTENIDO (CSV canonico sin comprimir), independiente de la compresion."""
    return hashlib.sha256(df.to_csv(index=False, lineterminator="\n",
                                    float_format="%.10g").encode("utf-8")).hexdigest()


__all__ = [
    "CERO",
    "MASCARA",
    "NO_USABLE",
    "SIN_COBERTURA",
    "VENTA",
    "category_daily",
    "content_sha256",
    "intermittency",
    "pair_daily",
    "sales_frame",
    "to_csv_gz_bytes",
]
