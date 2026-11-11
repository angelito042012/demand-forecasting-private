export type GroupBy = 'day' | 'month' | 'category';

export interface SalesSummary {
  provenance: 'OBSERVED_EXCEL';
  unit: string;
  currency: string;
  from: string;
  to: string;
  items: { key: string; lineas_venta: number; unidades: number; importe_pen: number }[];
  notas_credito: { lineas: number; importe_pen: number };
  excluded_days: { fecha: string; motivo: string }[];
}
