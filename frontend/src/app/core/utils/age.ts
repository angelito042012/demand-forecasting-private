/** Umbral de antigüedad: supuesto de UI (7 días), no una regla del contrato. */
export const STALE_DAYS = 7;

/** La antigüedad oficial la entrega el servidor (`age_days_at_view`); aquí solo se decide el aviso. */
export function isStaleAge(ageDaysAtView: number | null | undefined): boolean {
  return ageDaysAtView === null || ageDaysAtView === undefined || ageDaysAtView > STALE_DAYS;
}
