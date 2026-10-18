import unittest
from datetime import date
from decimal import Decimal as D

from scripts.prepare_academic_data import (
    build_inventory,
    choose_group,
    classify,
    initial_minimum,
)


class PreparationTests(unittest.TestCase):
    def raw(self, **changes):
        r = {'FECHA': date(2026, 3, 1), 'CANTIDAD': 12, 'EQUIVALENCIA': 1,
                 'CANTIDAD_UM_BASE': 12, 'TOTAL_LINEA': 20, 'ESTADO': 'ACTIVO',
                 'VEN_ESTADO': 'ACTIVO', 'ID_ARTICULO': 1, 'ID_ALMACEN': 1, 'UM_BASE': 'UND', 'TIPO_DOC': 1}
        r.update(changes)
        return r

    def test_zero_price_keeps_units(self):
        self.assertEqual(classify('compras', self.raw(TOTAL_LINEA=0))[0], 'COMPRA_SIN_CARGO_REGISTRADO')

    def test_negative_purchase_is_quarantined(self):
        self.assertEqual(classify('compras', self.raw(TOTAL_LINEA=-2))[0], 'CUARENTENA')

    def test_inconsistent_conversion_is_not_repaired(self):
        self.assertEqual(classify('ventas', self.raw(CANTIDAD=.01, CANTIDAD_UM_BASE=0))[1], 'CONVERSION_NO_COINCIDE')

    def test_credit_stays_separate(self):
        self.assertEqual(classify('ventas', self.raw(TIPO_DOC=7, CANTIDAD=-1, CANTIDAD_UM_BASE=-1, TOTAL_LINEA=-2))[0], 'CREDITO')

    def row(self, month, kind='VENTA', qty=1, sku='1', occurrence=1):
        return {'fecha': date(2026, month, 1), 'clasificacion': kind, 'cantidad': D(qty),
                    'producto_id': sku, 'producto': 'Producto', 'categoria': 'Categoria', 'almacen': '1',
                    'unidad': 'UND', 'ocurrencia': occurrence}

    def test_selection_ignores_future(self):
        rows = [self.row(m, sku=s) for s in ('1', '2') for m in range(3, 8)]
        rows += [self.row(m, 'COMPRA', sku=s) for s in ('1', '2') for m in (3, 4)]
        before = choose_group(rows, 1)
        after = choose_group(rows + [self.row(9, qty=99999, sku='2')], 1)
        self.assertEqual(before, after)

    def test_opening_minimum_respects_order(self):
        self.assertEqual(initial_minimum({date(2026,3,1):D(-5), date(2026,3,2):D(10)}), D(5))

    def test_credits_not_physical_and_copies_retained(self):
        key = ('1','1','UND')
        rows = [self.row(3, qty=10), self.row(4,'COMPRA',3), self.row(4,'COMPRA',3,occurrence=2), self.row(3,'CREDITO',-4)]
        summary, daily = build_inventory(rows,{key},{key:{'producto':'Producto','categoria':'Categoria'}})
        s = summary[0]
        self.assertEqual(s['saldo_inicial_minimo_calculado'],D(10))
        self.assertEqual(s['saldo_final_calculado'],D(6))
        self.assertEqual(s['saldo_final_alternativo_sin_segundas_copias'],D(3))
        self.assertIsNone(s['conteo_fisico'])
        self.assertEqual(len(daily),214)
        self.assertTrue(all(not r['conteo_fisico_verificado'] for r in daily))


if __name__ == '__main__':
    unittest.main()
