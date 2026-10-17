import { Recommendation } from './models';

export interface CalcStep { label: string; formula: string; value: number; unit: string }

/**
 * Pasos del cálculo según T08 §5, con los valores que publicó el servidor.
 * No recalcula nada que cambie el resultado: `check` indica si lo publicado es coherente.
 * Devuelve null si la recomendación no tiene inventario simulado (sin_snapshot): nunca se supone stock cero.
 */
export function calcSteps(r: Recommendation): { steps: CalcStep[]; check: { target: boolean; position: boolean; order: boolean } } | null {
  if (r.status !== 'ok') return null;
  const nums = [r.on_hand, r.in_transit, r.position, r.forecast_14d, r.safety, r.target, r.order_qty, r.mean_28];
  if (nums.some((n) => n === null || n === undefined)) return null;
  const u = 'unidad base';
  const steps: CalcStep[] = [
    { label: 'Stock simulado al cierre del ' + r.snapshot_date, formula: 'saldo simulado', value: r.on_hand!, unit: u },
    { label: 'En tránsito (pedidos emitidos − recibidos a esa fecha)', formula: 'pedidos − recepciones', value: r.in_transit!, unit: u },
    { label: 'Posición de inventario', formula: 'stock + tránsito', value: r.position!, unit: u },
    { label: `Pronóstico ${r.horizon_days} días (${r.forecast_from} a ${r.forecast_to}, ${r.model})`, formula: 'suma de 14 pronósticos diarios', value: r.forecast_14d!, unit: u },
    { label: `Stock de seguridad (${r.safety_days} × media de 28 días = ${r.safety_days} × ${r.mean_28})`, formula: `${r.safety_days} × media_28`, value: r.safety!, unit: u },
    { label: 'Objetivo (pronóstico + seguridad, redondeado hacia arriba)', formula: 'ceil(pronóstico + seguridad)', value: r.target!, unit: u },
    { label: 'Pedido sugerido', formula: 'max(0, objetivo − posición)', value: r.order_qty!, unit: u },
  ];
  const check = {
    position: r.on_hand! + r.in_transit! === r.position!,
    target: Math.ceil(Math.round((r.forecast_14d! + r.safety!) * 1e9) / 1e9) === r.target!,
    order: Math.max(0, r.target! - r.position!) === r.order_qty!,
  };
  return { steps, check };
}
