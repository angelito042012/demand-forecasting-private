// Regresión hallada al probar con la API real: `purchase_qty` llega como ENTERO (0, 8, 60…) o null, no como texto.
import { isZero, purchaseText } from './plan-text';

describe('Planificar compras · tipos reales de la API', () => {
  it('un 0 numérico calculado se rotula «0 (no hace falta comprar)»', () => {
    expect(purchaseText({ purchase_qty: 0 })).toBe('0 (no hace falta comprar)');
    expect(isZero(0)).toBe(true);
    expect(isZero('0')).toBe(true);
  });
  it('un entero positivo se muestra tal cual y null NUNCA se muestra como 0', () => {
    expect(purchaseText({ purchase_qty: 8 })).toBe('8');
    expect(purchaseText({ purchase_qty: 60 })).toBe('60');
    expect(purchaseText({ purchase_qty: null })).toBeNull();
    expect(isZero(null)).toBe(false);
  });
});
