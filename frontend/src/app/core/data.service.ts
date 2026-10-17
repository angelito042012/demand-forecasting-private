import { Injectable, signal } from '@angular/core';
import { Observable, of, throwError, timer } from 'rxjs';
import { delay, map, switchMap } from 'rxjs/operators';
import { ForecastRow, HealthInfo, ImportRecord, Provenance, RecommendationRow, RunRecord } from './models';

/** Escenario de demostración seleccionable para ver los estados de UI. */
export type MockScenario = 'data' | 'empty' | 'error' | 'slow';

export interface Result<T> {
  data: T;
  provenance: Provenance;
}

/**
 * Servicio de datos con MOCKS de contrato. No llama a la API real.
 * Todo lo que devuelve es DEMO_MOCK: valores ficticios, no son resultados reales.
 */
@Injectable({ providedIn: 'root' })
export class DataService {
  readonly scenario = signal<MockScenario>('data');

  private failure(msg: string): Observable<never> {
    return timer(300).pipe(switchMap(() => throwError(() => new Error(msg))));
  }

  private list<T>(data: T[]): Observable<Result<T[]>> {
    const s = this.scenario();
    if (s === 'error') return this.failure('Fallo simulado (mock): API no disponible');
    const payload = s === 'empty' ? [] : data;
    return of({ data: payload, provenance: 'DEMO_MOCK' as Provenance }).pipe(delay(s === 'slow' ? 2500 : 300));
  }

  imports(): Observable<Result<ImportRecord[]>> {
    return this.list<ImportRecord>([
      { id: 'demo-imp-1', filename: 'ejemplo_demo.xlsx', status: 'accepted', rows_total: 0, rows_accepted: 0, rows_rejected: 0, errors: [] },
      { id: 'demo-imp-2', filename: 'ejemplo_malformado_demo.xlsx', status: 'rejected', rows_total: 0, rows_accepted: 0, rows_rejected: 0, errors: ['Fecha inválida (ejemplo ficticio)'] },
    ]);
  }

  runs(): Observable<Result<RunRecord[]>> {
    return this.list<RunRecord>([
      { run_id: 'demo-run-1', status: 'completed', cutoff: '2026-01-31', completed_at: '2026-02-02T08:00:00-05:00' },
      { run_id: 'demo-run-2', status: 'failed', cutoff: '2026-02-28', completed_at: null },
    ]);
  }

  forecasts(): Observable<Result<ForecastRow[]>> {
    // Cantidades nulas a propósito: el mock solo valida la forma del contrato.
    return this.list<ForecastRow>([
      { run_id: 'demo-run-1', entity: 'DEMO-SKU-A', target_date: '2026-02-01', quantity: 0, model: 'demo' },
      { run_id: 'demo-run-1', entity: 'DEMO-SKU-B', target_date: '2026-02-01', quantity: 0, model: 'demo' },
    ]);
  }

  recommendations(): Observable<Result<RecommendationRow[]>> {
    return this.list<RecommendationRow>([
      {
        sku: 'DEMO-SKU-A', stock: 0, in_transit: 0, horizon_days: 7, order_qty: 0,
        reason: 'Ejemplo de forma del contrato', provenance: 'SYNTHETIC_NOT_REAL_INVENTORY', scenario_id: 'reference_v1',
      },
    ]);
  }

  health(): Observable<Result<HealthInfo>> {
    const s = this.scenario();
    if (s === 'error') return this.failure('Fallo simulado (mock): sin respuesta de /health');
    return of({ status: 'ok', api_version: 'mock' } as HealthInfo).pipe(
      delay(s === 'slow' ? 2500 : 300),
      map((data) => ({ data, provenance: 'DEMO_MOCK' as Provenance })),
    );
  }
}
