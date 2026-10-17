import { DASH, fmtDate, fmtDec, fmtInt, fmtPct, fmtPen, fmtPp, FmtPipe } from './format';
import { calcSteps, fraction } from './reco-calc';
import { recoOk } from '../testing/fixtures';
import { realRecoDetail } from '../testing/real-shapes';

describe('formato numérico es-PE', () => {
  it('unidades enteras: el error de redondeo no se ve', () => {
    expect(fmtInt(4.9999999994)).toBe('5');
    expect(fmtInt(46.00000000400001)).toBe('46');
    expect(fmtInt(1284.5357)).toBe('1,285');
    expect(fmtInt(0)).toBe('0');
  });
  it('un valor que redondea a cero no lleva signo', () => {
    expect(fmtInt(-0.2)).toBe('0');
    expect(fmtInt(-0.2, true)).toBe('0');
    expect(fmtPen(-0.001)).toBe('0.00 PEN');
  });
  it('medias y pronósticos con hasta 3 decimales y sin ceros sobrantes', () => {
    expect(fmtDec(0.3571428571)).toBe('0.357');
    expect(fmtDec(2.5)).toBe('2.5');
    expect(fmtDec(4.999999999400001)).toBe('5');
    expect(fmtDec(0.23890344311377246, 2)).toBe('0.24');
  });
  it('PEN con 2 decimales y moneda', () => {
    expect(fmtPen(42.25)).toBe('42.25 PEN');
    expect(fmtPen(5)).toBe('5.00 PEN');
    expect(fmtPen(321543.72250000003)).toBe('321,543.72 PEN');
  });
  it('porcentajes con 1 decimal y puntos porcentuales con signo', () => {
    expect(fmtPct(0.6681037512594016)).toBe('66.8 %');
    expect(fmtPct(1)).toBe('100.0 %');
    expect(fmtPct(-0.056390230988152726, true)).toBe('-5.6 %');
    expect(fmtPp(-0.03992595890250472)).toBe('-4.0 pp');
  });
  it('valores ausentes o no finitos se muestran como guion, nunca como 0', () => {
    expect(fmtInt(null)).toBe(DASH);
    expect(fmtInt(undefined)).toBe(DASH);
    expect(fmtDec(NaN)).toBe(DASH);
    expect(fmtPen(null)).toBe(DASH);
    expect(fmtPct(undefined)).toBe(DASH);
  });
  it('fechas de negocio AAAA-MM-DD a DD/MM/AAAA', () => {
    expect(fmtDate('2026-07-10')).toBe('10/07/2026');
    expect(fmtDate(null)).toBe(DASH);
  });
  it('el pipe delega en las funciones', () => {
    const p = new FmtPipe();
    expect(p.transform(4.9999999994, 'int')).toBe('5');
    expect(p.transform(42.25, 'pen')).toBe('42.25 PEN');
    expect(p.transform(0.5, 'pct')).toBe('50.0 %');
  });
});

describe('cálculo de pedido: presentación a partir de señales exactas', () => {
  const base = { ...recoOk, on_hand: 5, in_transit: 4, position: 9, horizon_days: 14, safety_days: 7 };

  it('12 unidades en 28 días útiles = 3/7 por día; objetivo 9 sin inflar por redondeo', () => {
    const c = calcSteps({ ...base, sum_28: 12, days_28: 28, mean_28_exact: '3/7', mean_28: 0.4285714286, forecast_14d: 5.9999999996, safety: 3.0000000002, target: 9, order_qty: 0, order_value_assumed: 0 })!;
    expect(c.mode).toBe('exact');
    expect(c.steps[3].text).toBe('12 unidades en 28 días útiles = 3/7 por día');
    expect(c.steps[4].text).toContain('= 6 unidades');
    expect(c.steps[5].text).toContain('= 3 unidades');
    expect(c.steps[6].value).toBe(9);
    expect(c.steps[7].value).toBe(0);
    expect(c.check).toEqual({ position: true, target: true, order: true });
  });
  it('suma 4 en 28 días: 1/7 por día, objetivo 3 y pedido 2 con posición 1', () => {
    const c = calcSteps({ ...base, on_hand: 1, in_transit: 0, position: 1, sum_28: 4, days_28: 28, mean_28_exact: null, mean_28: 0.1428571429, forecast_14d: 2, safety: 1, target: 3, order_qty: 2 })!;
    expect(c.steps[3].text).toBe('4 unidades en 28 días útiles = 1/7 por día');
    expect(c.steps[6].value).toBe(3);
    expect(c.steps[7].value).toBe(2);
    expect(c.check.target).toBe(true);
  });
  it('si el objetivo publicado difiere del exacto, lo marca como incoherente', () => {
    const c = calcSteps({ ...base, sum_28: 12, days_28: 28, mean_28: 0.4285714286, forecast_14d: 6, safety: 3, target: 10, order_qty: 1 })!;
    expect(c.check.target).toBe(false);
  });
  it('cero ventas en la ventana: media 0 y objetivo 0', () => {
    const c = calcSteps({ ...base, on_hand: 0, in_transit: 0, position: 0, sum_28: 0, days_28: 28, mean_28: 0, forecast_14d: 0, safety: 0, target: 0, order_qty: 0 })!;
    expect(c.steps[3].text).toBe('0 unidades en 28 días útiles = 0 por día');
    expect(c.steps[6].value).toBe(0);
  });
  it('corrida antigua sin sum_28: usa los valores publicados con presentación ≤ 3 decimales', () => {
    const c = calcSteps(realRecoDetail)!;
    expect(c.mode).toBe('published');
    const txt = c.steps.map((s) => s.text).join(' | ');
    expect(txt).not.toContain('4.9999999994');
    expect(txt).not.toContain('4.99999');
    expect(c.steps[3].text).toContain('0.357');
    expect(c.steps[1].text).toContain('19 pedidas − 17 recibidas');
    expect(c.steps[8].text).toContain('42.25 PEN');
  });
  it('fracciones reducidas', () => {
    expect(fraction(12, 28)).toBe('3/7');
    expect(fraction(28, 28)).toBe('1');
    expect(fraction(0, 28)).toBe('0');
  });
});
