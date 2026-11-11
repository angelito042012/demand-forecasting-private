export type PlanSnapshotKind = 'INFORMADO' | 'RECONSTRUIDO';

export interface PlanConfirmation { code: string; status: string; text: string; products?: string[] }

export interface StockSnapshot {
  snapshot_id: string; kind?: string; version?: number; status?: string;
  as_of_local: string; warehouse?: { id: string; name: string } | string;
  base_count?: { snapshot_id?: string; as_of_local?: string } | null;
  movements?: { from_local?: string; closing_local?: string; last_movement_local?: string } | null;
  counts?: { products?: number; discrepancies?: number } | null;
  rule?: string;
  confirmations?: PlanConfirmation[];
}

export interface StockItem {
  producto_id: string; producto: string; categoria?: string; unidad_reporte?: string; unidad_descripcion?: string | null;
  libre: number | null;
  base_count?: number | null;
  movements?: { entradas_cierre?: number; salidas_cierre?: number; entradas_ultimo_mov?: number; salidas_ultimo_mov?: number } | null;
  reconstructed_at_last_movement?: number | null;
  system_stock_at_last_movement?: number | null;
  system_reserved?: number | null;
  discrepancy: { difference: number; compared_at_local?: string } | null;
}

export interface StockPage {
  snapshot: StockSnapshot | null; items: StockItem[]; page: number; page_size: number; total: number; has_more: boolean;
  unavailable_reason?: string | null;
}
