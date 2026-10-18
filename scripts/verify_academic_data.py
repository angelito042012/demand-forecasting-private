"""Read-only verification of exported CSV/XLSX and intact source hashes."""
import csv
import hashlib
import json
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

import openpyxl

ROOT = Path('artifacts/private/datos_preparados_v1')


def read(name):
    with (ROOT / name).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def main():
    manifest = json.loads((ROOT / 'manifest.json').read_text(encoding='utf-8'))
    payload = json.loads((ROOT / 'workbook_payload.json').read_text(encoding='utf-8'))
    all_rows = read('01_normalizados/clasificacion_completa.csv')
    assert len(all_rows) == manifest['source_rows'] == 106525
    assert len({r['registro_id'] for r in all_rows}) == len(all_rows)
    assert Counter(r['clasificacion'] for r in all_rows) == manifest['class_counts']
    amounts = defaultdict(Decimal)
    counts = Counter()
    for r in all_rows:
        amounts[(r['archivo'], r['moneda'])] += Decimal(r['importe'])
        counts[r['archivo']] += 1
    for source in manifest['sources']:
        for directory in (Path(manifest['source_dir']), ROOT / '00_originales'):
            assert hashlib.sha256((directory / source['archivo']).read_bytes()).hexdigest() == source['sha256']
        assert counts[source['archivo']] == source['filas']
        for currency, total in source['importes_por_moneda'].items():
            assert amounts[source['archivo'], currency] == Decimal(total)
    components = ['ventas', 'compras', 'creditos', 'cuarentena']
    ids = [r['registro_id'] for n in components for r in read(f'01_normalizados/{n}.csv')]
    assert len(ids) == len(set(ids)) == 106525
    assert set(ids) == {r['registro_id'] for r in all_rows}
    books = {}
    for file, sheets in [('01_Ventas_grupo.xlsx', [('Ventas', 'sales'), ('Notas_de_credito','credits')]),
                         ('02_Compras_grupo.xlsx', [('Compras','purchases')])]:
        wb = openpyxl.load_workbook(ROOT / '03_excel' / file, read_only=True, data_only=True)
        for name, key in sheets:
            exported = list(wb[name].iter_rows(min_row=5, values_only=True))
            assert len(exported) == len(payload[key])
            for row, original in zip(exported, payload[key]):
                assert str(row[1]) == original['producto_id']
                assert Decimal(str(row[3])) == Decimal(original['cantidad'])
                assert abs(Decimal(str(row[6])) - Decimal(original['importe'])) < Decimal('.000001')
                assert row[0].date().isoformat() == original['fecha']
        books[file] = {name: len(payload[key]) for name, key in sheets}
        wb.close()
    file = '03_Inventario_calculado.xlsx'
    wb = openpyxl.load_workbook(ROOT / '03_excel' / file, read_only=True, data_only=True)
    rows = list(wb['Saldo_calculado'].iter_rows(min_row=5, values_only=True))
    assert len(rows) == 50
    for row, original in zip(rows,payload['stock']):
        for col,key in [(2,'saldo_inicial_minimo_calculado'),(3,'entradas_documentadas'),(4,'salidas_documentadas'),(5,'saldo_final_calculado')]:
            assert Decimal(str(row[col])) == Decimal(original[key]), (col,row,original)
        assert row[6] is None
    daily = list(wb['Balance_diario'].iter_rows(min_row=5, values_only=True))
    assert len(daily) == 10700
    for row, original in zip(daily,payload['daily']):
        assert row[2] + row[3] - row[4] + row[5] == row[6]
        assert Decimal(str(row[6])) == Decimal(original['saldo_fin_dia'])
        assert row[8] is False
    wb.close()
    books[file] = {'Saldo_calculado':50,'Balance_diario':10700}
    wb = openpyxl.load_workbook(ROOT / '03_excel' / '04_Control_y_decisiones.xlsx', read_only=True, data_only=True)
    assert sum(1 for row in wb['Productos'].iter_rows(min_row=5, values_only=True) if row[0] is not None) == 50
    assert sum(1 for row in wb['Incidencias'].iter_rows(min_row=5, values_only=True) if row[0] is not None) == len(payload['issues'])
    assert sum(1 for row in wb['Fuentes'].iter_rows(min_row=5, values_only=True) if row[0] is not None) == 14
    wb.close()
    result = {'verified':True,'original_hashes':14,'rows_reconciled':len(all_rows),
              'classification_unique':True,'xlsx_quantities_amounts_dates_match':True,
              'cached_formulas_match_all_daily_balances':True,'books':books,
              'group_categories':dict(Counter(r['categoria'] for r in payload['products'])),
              'group_stock_totals':{k:str(sum(Decimal(r[k]) for r in payload['stock'])) for k in
                  ['saldo_inicial_minimo_calculado','entradas_documentadas','salidas_documentadas','saldo_final_calculado']}}
    (ROOT/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))


if __name__ == '__main__':
    main()
