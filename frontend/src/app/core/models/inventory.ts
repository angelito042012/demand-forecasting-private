export type ReportedView = 'all' | 'with_stock' | 'no_stock';

export interface ReportedUnknown { code: string; detail: string }

export interface ReportedSnapshot {
  snapshot_id: string;
  version: number;
  status: string;
  as_of_local: string;
  as_of_utc?: string;
  timezone: string;
  warehouse: { id: string; name: string };
  nature?: string;
  independent_verification: boolean;
  source?: { file?: string; sha256_short?: string };
  confirmations?: unknown;
  counts: { items: number; with_stock: number; no_stock: number };
  declared_unknowns?: ReportedUnknown[];
  context?: { sales_history_end?: string | null };
  imported_at?: string;
}

export interface ReportedItem {
  producto_id: string;
  producto: string;
  categoria?: string;
  unidad_reporte?: string;
  unidad_descripcion?: string | null;
  libre: number | null;
  reservada: number | null;
  no_vendible: number | null;
  fisica_total?: number | null;
}

export interface ReportedInventoryPage {
  snapshot: ReportedSnapshot | null;
  items: ReportedItem[];
  page: number;
  page_size: number;
  total: number;
  has_more: boolean;
  view_counts?: { all: number; with_stock: number; no_stock: number };
  provenance?: string;
  disclaimer?: string;
  unavailable_reason?: string;
}

export interface ReportedSnapshotRef {
  snapshot_id: string; version: number; status: string; as_of_local: string;
  warehouse: { id: string; name: string }; source?: { sha256_short?: string }; imported_at?: string;
}
