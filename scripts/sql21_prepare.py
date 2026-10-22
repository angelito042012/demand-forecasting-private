"""Preparacion y conciliacion de solo lectura contra SYDESOFT_2 (SQL Server restaurado) y octubre.xlsx - 21/10/2026.

Solo ejecuta SELECT mediante `sqlcmd -E` (autenticacion de Windows). No escribe en SQL Server, no importa nada en la
aplicacion y no sustituye el plan vigente. Escribe CSV/JSON en `--out` (por defecto artifacts/private/sql21_prep/).
No extrae datos personales (sin clientes, usuarios ni proveedores).

Uso: python -m scripts.sql21_prepare [--server Rogelio] [--db SYDESOFT_2]
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
from collections import Counter, defaultdict
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import openpyxl

from pipeline.plan.normalize import FIELDS, normalize_book, sha256_file

DATOS = Path("C:/Users/rogel/Documents/Datos")
COUNT_CSV = Path("artifacts/private/conteo_recibido_20261018_v2/conteo_reportado.csv")
COUNT_AT = "20261018 17:00:00"
LAST_FULL_DAY = date(2026, 10, 20)
D = Decimal


class Sql:
    def __init__(self, server: str, db: str):
        self.server, self.db = server, db

    def rows(self, sql: str) -> list[list[str]]:
        assert sql.lstrip().upper().startswith(("SELECT", "WITH")), "solo lectura"
        r = subprocess.run(["sqlcmd", "-S", self.server, "-E", "-C", "-d", self.db, "-l", "15", "-W", "-s", "|", "-h", "-1", "-Q",
                            "SET NOCOUNT ON; " + sql], capture_output=True, text=True, encoding="cp1252", check=False)
        if r.returncode:
            raise RuntimeError("sqlcmd fallo: " + r.stderr[:200])
        return [line.split("|") for line in r.stdout.splitlines() if line.strip()]


def dec(v) -> Decimal:
    return D(str(v)).quantize(D("0.0001")) if v not in (None, "", "NULL") else D(0)


def write_csv(path: Path, header: list[str], rows: list[list]) -> None:
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


# ------------------------------------------------------------------ 1. ventas Excel vs SQL por registros
def excel_lines(name: str):
    ws = openpyxl.load_workbook(DATOS / name, read_only=True, data_only=True)["Hoja1"]
    it = ws.iter_rows(min_row=2, values_only=True)
    hdr = [str(h) for h in next(it)]
    ix = {h: i for i, h in enumerate(hdr)}
    for row in it:
        if row[ix["ID_PEDIDO"]] is None:
            continue
        g = dict(zip(hdr, row, strict=False)).__getitem__
        d = g("FECHA")
        yield {"pedido": str(int(g("ID_PEDIDO"))), "tipo": str(int(g("TIPO_DOC"))).zfill(2), "doc": str(g("SERIE_NUMERO")),
               "fecha": (d.date() if isinstance(d, datetime) else d).isoformat(), "art": str(g("ID_ARTICULO")).strip(),
               "alm": str(g("ID_ALMACEN")).strip().zfill(3), "cant": dec(g("CANTIDAD")), "precio": dec(g("PRECIO")),
               "dscto": dec(g("DSCTO")), "total": dec(g("TOTAL_LINEA")), "um": str(g("ID_UM")).strip(), "eq": dec(g("EQUIVALENCIA"))}


def sql_lines(sql: Sql, lo: str, hi: str):
    q = ("SELECT CAST(v.ID_PEDIDO AS varchar(20)), v.ID_TIPO_DOCUMENTO, ISNULL(s.SER_SERIE, '') + '-' + v.VEN_NUMERO_DOC, CONVERT(varchar(10), v.VEN_FECHA_DOCUMENTO, 23), "
         "d.ID_ARTICULO, d.ID_ALMACEN, d.DET_VEN_CANTIDAD, d.DET_VEN_PRECIO, d.DET_VEN_DSCTO, d.DET_VEN_TOTAL, d.ID_UM, d.DET_VEN_EQUIVALENCIA, "
         "CONVERT(varchar(19), v.VEN_FECHA_DOCUMENTO, 120) "
         f"FROM VENTA v JOIN DETALLE_VENTA d ON d.ID_VENTA = v.ID_VENTA LEFT JOIN SERIE s ON s.ID_SERIE = v.ID_SERIE WHERE v.VEN_ESTADO = 2 AND v.VEN_FECHA_DOCUMENTO >= '{lo}' "
         f"AND v.VEN_FECHA_DOCUMENTO < '{hi}'")
    for r in sql.rows(q):
        yield {"pedido": r[0], "tipo": r[1].zfill(2), "doc": r[2], "fecha": r[3], "art": r[4], "alm": r[5].zfill(3), "cant": dec(r[6]),
               "precio": dec(r[7]), "dscto": dec(r[8]), "total": dec(r[9]), "um": r[10], "eq": dec(r[11]), "_ts": r[12]}


def key(r: dict, code_map: dict[str, str]) -> tuple:
    sign = r["tipo"] == "07"          # el libro guarda la nota de credito en negativo; SQL en positivo: se compara el valor absoluto
    f = (lambda x: abs(x)) if sign else (lambda x: x)
    return (r["pedido"], r["tipo"], r["doc"], r["fecha"], code_map.get(r["art"], r["art"]), r["alm"], f(r["cant"]), f(r["precio"]),
            f(r["dscto"]), f(r["total"]), r["um"], r["eq"])


def compare_sales(sql: Sql, out: Path, code_map: dict[str, str]) -> dict:
    res = {}
    for name, lo, hi, last in (("setiembre.xlsx", "20260901", "20261001", "2026-09-30"), ("octubre.xlsx", "20261001", "20261021", "2026-10-20")):
        xl = Counter(key(r, code_map) for r in excel_lines(name))
        sq = Counter(key(r, code_map) for r in sql_lines(sql, lo, hi))
        only_x, only_s = xl - sq, sq - xl
        docs_x, docs_s = Counter(), Counter()
        for k, n in xl.items():
            docs_x[(k[0], k[1], k[2])] += n
        for k, n in sq.items():
            docs_s[(k[0], k[1], k[2])] += n
        res[name] = {"lineas_excel": sum(xl.values()), "lineas_sql": sum(sq.values()), "registros_distintos_excel": len(xl),
                     "registros_distintos_sql": len(sq), "solo_excel": sum(only_x.values()), "solo_sql": sum(only_s.values()),
                     "multiplicidad_maxima_excel": max(xl.values()), "documentos_excel": len(docs_x), "documentos_sql": len(docs_s),
                     "documentos_con_distinto_numero_de_lineas": sum(1 for k in set(docs_x) | set(docs_s) if docs_x[k] != docs_s[k]),
                     "ultimo_dia": last, "coincide": not only_x and not only_s}
        if only_x or only_s:
            write_csv(out / f"diferencias_ventas_{name[:-5]}.csv", ["lado", "n", "clave"],
                      [["solo_excel", n, k] for k, n in only_x.items()] + [["solo_sql", n, k] for k, n in only_s.items()])
    return res


# ------------------------------------------------------------------ 2. codigos
def codes(sql: Sql, code_map_out: dict[str, str]) -> dict:
    arts = [r[0] for r in sql.rows("SELECT ID_ARTICULO FROM DM_ARTICULOS")]
    stripped = defaultdict(list)
    for a in arts:
        stripped[a.lstrip("0") or "0"].append(a)
    collisions = {k: v for k, v in stripped.items() if len(v) > 1}
    excel_codes = set()
    for name in ("marzo", "abril", "mayo", "junio", "julio", "agosto", "setiembre", "octubre"):
        ws = openpyxl.load_workbook(DATOS / f"{name}.xlsx", read_only=True, data_only=True)["Hoja1"]
        it = ws.iter_rows(min_row=2, values_only=True)
        hdr = [str(h) for h in next(it)]
        i = hdr.index("ID_ARTICULO")
        excel_codes.update(str(r[i]).strip() for r in it if r[i] is not None)
    missing, ambiguous = [], []
    for c in excel_codes:
        cands = stripped.get(c.lstrip("0") or "0", [])
        if not cands:
            missing.append(c)
        elif len(cands) > 1:
            ambiguous.append(c)
        else:
            code_map_out[cands[0]] = c            # codigo SQL -> codigo original de los libros
    non_num = [a for a in arts if not a.isdigit()]
    return {"articulos_sql": len(arts), "longitudes": dict(Counter(len(a) for a in arts)), "no_numericos": non_num,
            "colisiones_al_quitar_ceros": collisions, "codigos_distintos_en_libros_mar_oct": len(excel_codes),
            "codigos_de_libros_sin_articulo_en_sql": sorted(missing), "codigos_de_libros_ambiguos": sorted(ambiguous)}


def count_rows() -> dict[str, dict]:
    with open(COUNT_CSV, encoding="utf-8-sig") as f:
        return {r["producto_id"]: r for r in csv.DictReader(f)}


# ------------------------------------------------------------------ 3. conciliacion de los 50
def reconcile(sql: Sql, out: Path) -> dict:
    cnt = count_rows()
    sql_id = {c: c.zfill(8) for c in cnt}
    inn = ",".join(f"'{v}'" for v in sql_id.values())
    stock = {r[0]: (dec(r[1]), dec(r[2])) for r in sql.rows(
        f"SELECT ID_ARTICULO, STOCK_CANTIDAD, STOCK_CANTRESERVADA FROM INV_STOCK_ARTICULOS WHERE ID_ALMACEN = '001' AND ID_ARTICULO IN ({inn})")}
    mov = defaultdict(list)
    for r in sql.rows("SELECT ID_ARTICULO, CONVERT(varchar(19), KAR_FECHA, 120), KAR_CONCEPTO, KAR_ECANTIDAD, KAR_SCANTIDAD, "
                      "KAR_EQUIVALENCIA, ID_VENTA, ID_COMPRA FROM KARDEX WHERE ID_ALMACEN = '001' AND KAR_FECHA > '" + COUNT_AT + "' "
                      f"AND ID_ARTICULO IN ({inn})"):
        mov[r[0]].append({"ts": r[1], "conc": r[2], "e": dec(r[3]), "s": dec(r[4]), "eq": dec(r[5]), "venta": r[6], "compra": r[7]})
    before_same_day = {r[0]: dec(r[1]) for r in sql.rows(
        f"SELECT ID_ARTICULO, SUM(KAR_SCANTIDAD - KAR_ECANTIDAD) FROM KARDEX WHERE ID_ALMACEN = '001' AND KAR_FECHA >= '20261018' "
        f"AND KAR_FECHA <= '{COUNT_AT}' AND ID_ARTICULO IN ({inn}) GROUP BY ID_ARTICULO")}
    nonvalid = {r[0]: int(r[1]) for r in sql.rows(
        "SELECT k.ID_ARTICULO, COUNT(*) FROM KARDEX k JOIN VENTA v ON v.ID_VENTA = k.ID_VENTA WHERE k.ID_ALMACEN = '001' "
        f"AND k.KAR_FECHA > '{COUNT_AT}' AND v.VEN_ESTADO <> 2 AND k.ID_ARTICULO IN ({inn}) GROUP BY k.ID_ARTICULO")}
    rows, summary = [], Counter()
    for pid, c in cnt.items():
        sid = sql_id[pid]
        libre = dec(c["cantidad_libre_reportada"])
        ms = mov.get(sid, [])
        by = defaultdict(lambda: [D(0), D(0)])
        for m in ms:
            by[m["conc"]][0] += m["e"]
            by[m["conc"]][1] += m["s"]
        ent_all, sal_all = sum((m["e"] for m in ms), D(0)), sum((m["s"] for m in ms), D(0))
        ent20 = sum((m["e"] for m in ms if m["ts"][:10] <= LAST_FULL_DAY.isoformat()), D(0))
        sal20 = sum((m["s"] for m in ms if m["ts"][:10] <= LAST_FULL_DAY.isoformat()), D(0))
        recon_cut, recon_20 = libre + ent_all - sal_all, libre + ent20 - sal20
        sis, res = stock[sid]
        diff = sis - recon_cut
        state = "COINCIDE" if diff == 0 else "DISCREPANTE"
        summary[state] += 1
        last = max((m["ts"] for m in ms), default="")
        rows.append([pid, sid, c["producto"], libre, dec(c["cantidad_reservada_reportada"]), len(ms),
                     by["VENTA"][1], by["NOTA CREDITO VENTA"][0], by["COMPRA"][0], by["ENTRADA/INVENTARIO"][0], by["SALIDA/INVENTARIO"][1],
                     ent_all, sal_all, recon_20, recon_cut, sis, res, diff, state, last, before_same_day.get(sid, D(0)), nonvalid.get(sid, 0)])
    hdr = ["producto_id_original", "id_articulo_sql", "producto", "conteo_libre_18_10_17h", "conteo_reservada", "movimientos_posteriores",
           "ventas_salidas", "notas_credito_entradas", "compras_entradas", "ajuste_entradas", "ajuste_salidas", "entradas_totales",
           "salidas_totales", "existencia_reconstruida_al_20_10", "existencia_reconstruida_al_ultimo_movimiento", "stock_sistema",
           "reservado_sistema", "diferencia_sistema_menos_reconstruida", "estado", "ultimo_movimiento_del_producto",
           "salidas_netas_18_10_antes_del_conteo", "movimientos_posteriores_con_documento_no_vigente"]
    write_csv(out / "conciliacion_50_productos.csv", hdr, rows)
    return {"productos": len(rows), **summary, "suma_diferencias_discrepantes": str(sum((r[17] for r in rows), D(0))),
            "discrepantes": [[r[0], str(r[17])] for r in rows if r[18] == "DISCREPANTE"]}


# ------------------------------------------------------------------ 4. compras 11452 y 11455
def purchases(sql: Sql, out: Path, group: set[str]) -> dict:
    head = sql.rows("SELECT ID_COMPRA, CONVERT(varchar(19), COM_FECHA, 120), CONVERT(varchar(19), COM_FECHA_RECEPCION, 120), "
                    "CONVERT(varchar(19), COM_FECHA_REGISTRA, 120), CONVERT(varchar(19), COM_FECHA_CONTABLE, 120), COM_ESTADO "
                    "FROM COMPRA WHERE ID_COMPRA IN (11452, 11455)")
    hmap = {r[0]: r for r in head}
    lines = sql.rows("SELECT d.ID_COMPRA, d.ID_DETALLE_COMPRA, d.ID_ARTICULO, a.ART_DESCRIPCION, d.ID_UM, d.DET_COM_CANTIDAD, d.DET_COM_EQUIVALENCIA, "
                     "d.ID_ALMACEN FROM DETALLE_COMPRA d JOIN DM_ARTICULOS a ON a.ID_ARTICULO = d.ID_ARTICULO WHERE d.ID_COMPRA IN (11452, 11455) "
                     "ORDER BY d.ID_COMPRA, d.ID_DETALLE_COMPRA")
    kard = defaultdict(list)
    for r in sql.rows("SELECT ID_COMPRA, ID_ARTICULO, ID_KARDEX, CONVERT(varchar(19), KAR_FECHA, 120), KAR_CONCEPTO, KAR_ECANTIDAD, KAR_EQUIVALENCIA, ID_ALMACEN "
                      "FROM KARDEX WHERE ID_COMPRA IN (11452, 11455)"):
        kard[(r[0], r[1])].append(r)
    out_rows = []
    for ln in lines:
        h = hmap[ln[0]]
        ks = kard.get((ln[0], ln[2]), [])
        out_rows.append([ln[0], h[1], h[2], h[3], h[4], h[5], ln[1], ln[2], ln[2].lstrip("0"), ln[3], ln[4], dec(ln[5]), dec(ln[6]),
                         dec(ln[5]) * dec(ln[6]), ln[7], "SI" if ln[2].lstrip("0") in group else "NO",
                         ";".join(k[2] for k in ks), ";".join(k[3] for k in ks), ";".join(k[4] for k in ks), sum((dec(k[5]) * dec(k[6]) for k in ks), D(0))])
    hdr = ["id_compra", "fecha_compra", "fecha_recepcion_registrada", "fecha_registro", "fecha_contable", "estado", "id_detalle", "id_articulo_sql",
           "codigo_original", "descripcion", "unidad", "cantidad", "equivalencia", "cantidad_base", "almacen", "en_los_50_productos",
           "id_kardex", "fecha_kardex", "concepto_kardex", "kardex_entrada_base_total_del_producto_en_la_compra"]
    write_csv(out / "compras_11452_11455_para_consultar.csv", hdr, out_rows)
    per = defaultdict(lambda: [D(0), D(0)])
    for r in out_rows:
        per[(r[0], r[7])][0] += r[13]
    for (c, a), ks in kard.items():
        per[(c, a)][1] = sum((dec(k[5]) * dec(k[6]) for k in ks), D(0))
    return {"cabeceras": head, "lineas": len(lines), "lineas_en_los_50": sum(1 for r in out_rows if r[15] == "SI"),
            "productos_distintos": len(per), "productos_donde_lineas_de_compra_igualan_la_entrada_del_kardex": sum(1 for v in per.values() if v[0] == v[1]),
            "almacenes_de_las_lineas": sorted({r[14] for r in out_rows})}


# ------------------------------------------------------------------ 5. datos preparados
def prepare_sales(sql: Sql, out: Path) -> dict:
    digest = sha256_file(DATOS / "octubre.xlsx")
    recs, summ = normalize_book(DATOS / "octubre.xlsx", digest, Counter(), window=(date(2026, 10, 1), LAST_FULL_DAY))
    write_csv(out / "ventas_octubre_01_20_normalizadas.csv", FIELDS, [[r[f] for f in FIELDS] for r in recs])
    partial = sorted(sql_lines(sql, "20261021", "20261022"), key=lambda r: (r["_ts"], r["doc"]))
    write_csv(out / "ventas_20261021_parcial_sql.csv",
              ["fecha", "hora_documento", "tipo_documento", "documento", "producto_id_sql", "almacen", "unidad", "cantidad", "equivalencia", "total"],
              [[r["fecha"], r["_ts"][11:], r["tipo"], r["doc"], r["art"], r["alm"], r["um"], r["cant"], r["eq"], r["total"]] for r in partial])
    last = max((r["_ts"] for r in partial), default="")
    return {"octubre_normalizado": summ, "parcial_21_lineas": len(partial), "parcial_21_ultima_hora_documento": last[11:]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", default="Rogelio")
    ap.add_argument("--db", default="SYDESOFT_2")
    ap.add_argument("--out", default="artifacts/private/sql21_prep")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    sql = Sql(a.server, a.db)
    code_map: dict[str, str] = {}
    report: dict = {"generado": datetime.now().isoformat(timespec="seconds"), "solo_lectura": True,
                    "ultimo_dia_completo": LAST_FULL_DAY.isoformat(),
                    "libros": {n: sha256_file(DATOS / n) for n in ("setiembre.xlsx", "octubre.xlsx")}}
    report["codigos"] = codes(sql, code_map)
    report["ventas_excel_vs_sql"] = compare_sales(sql, out, code_map)
    group = set(count_rows())
    report["conciliacion"] = reconcile(sql, out)
    report["compras_11452_11455"] = purchases(sql, out, group)
    report["datos_preparados"] = prepare_sales(sql, out)
    (out / "informe.json").write_text(json.dumps(report, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "datos_preparados"}, ensure_ascii=False, indent=1, default=str)[:6000])


if __name__ == "__main__":
    main()
