/** Umbral de antigüedad: supuesto de UI (7 días), no una regla del contrato. */
export const STALE_DAYS = 7;

export function ageDays(iso: string | null, now: Date = new Date()): number | null {
  if (!iso) return null;
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return null;
  return Math.floor((now.getTime() - t) / 86_400_000);
}

export function isStale(iso: string | null, now: Date = new Date()): boolean {
  const d = ageDays(iso, now);
  return d === null || d > STALE_DAYS;
}
