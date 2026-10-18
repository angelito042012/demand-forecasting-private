# T11A Acta de restauración (prueba de recuperación de `demand_forecasting_pub`)

> **R13 / T11B complementa esta acta.** Esta prueba cubre solo Mongo; los 18 archivos privados se listaban, no se copiaban. La recuperación integral (Mongo + bundle privado con hash de bytes y lógico, `mongo_ok`/`artefactos_ok`/`recuperacion_integral_ok`) está en `T11B_ACTA_RECUPERACION_INTEGRAL.md`.
> **Mantenimiento antes del export:** un conteo estable no es un snapshot (una mutación con el mismo conteo pasa). Detener API, worker y scheduler de verdad y usar `python -m scripts.backup_restore export-all ... --maintenance-confirmed`, que rechaza si hay escritores activos y exige hash de contenido igual antes/durante/después. El `export` simple conserva solo la consistencia lógica de T11A.

Fecha: 17/10/2026 (America/Lima). Prueba **local** en MongoDB 127.0.0.1 (contenedor `df-mongo-dev`); sin recursos externos ni transferencia de datos. Inventario simulado con supuestos; no corresponde al inventario real de la empresa. Sin filas comerciales ni secretos.

## 1. Comandos ejecutados (en orden)

```
python -m scripts.build_publication_db                       # v2 (solo lectura) -> demand_forecasting_pub
python -m scripts.publish_final --dry-run                    # verificación + capacidad, sin escribir
python -m scripts.publish_final                              # publicado; repetido: sin_cambios
python -m scripts.backup_restore export --db demand_forecasting_pub --out artifacts/private/t11a/backup
restore_db(artifacts/private/t11a/backup -> df_restore_t11a_20261017183220)   # pipeline.publish.archive
(comparación de hash de contenido restaurada vs demand_forecasting_pub; eliminación SOLO de la base temporal)
```

## 2. Export (consistencia y exclusiones)

- Snapshot lógico: sin corridas en `staging` (no hay escritores) y conteo igual antes/después de leer cada colección; si cambia, el export aborta.
- Colecciones exportadas (NDJSON.gz canónico + `indices.json` + `manifiesto.json`): `sales` 86 877, `credit_notes` 560, `forecasts` 234 381, `recommendations` 7 294, `imports` 12, `runs` 3, `backtests` 3, `run_pointer` 1, `import_conflicts` 0, `import_rejects` 0. Excluidas: `sessions`, `users`, `login_*`, `jobs`, `scheduler_ticks` (no existían en la base de publicación).
- Duración 18,91 s; tamaño comprimido total 13 049 693 bytes (12,45 MB); `manifiesto.json` sha256 `fa9561aa6e616a5427f8247843b8be59977472b5ca68f459da92f7be451f434b`; `indices.json` sha256 `cc94230321c404e2…`.
- Manifiesto de artefactos privados: 18 archivos de `artifacts/private/final/` con nombre, sha256 y tamaño (no copiados).

## 3. Restauración y verificación

Base destino `df_restore_t11a_20261017183220` (distinta del origen, inexistente antes). Antes de insertar se comprobó el sha256 de cada archivo del export contra el manifiesto.

| Verificación | Resultado |
|---|---|
| Hash de archivos del export vs manifiesto | correcto (10 colecciones + `indices.json`) |
| Conteo por colección | 10/10 iguales al manifiesto |
| Hash de contenido por colección | 10/10 iguales al manifiesto **y** a `demand_forecasting_pub` |
| Índices por colección (nombre, claves, unicidad, TTL) | idénticos a los exportados |
| Estado de las corridas | `hist-…4ea348836e35` completed, `hist-…52b01cd999dd` superseded, `final-20260731-d587255d87fb` completed |
| `children_ref` y hijos | las 3 corridas legibles tienen todos sus hijos (counts = hallados); la final bajo `final-20260731-d587255d87fb~g1`; 0 hijos huérfanos |
| Puntero activo | `hist-20260710-4ea348836e35` (la final no lo mueve) |
| Colecciones secretas presentes | ninguna |
| **Resultado** | **`ok=true`, 0 problemas** |

Duraciones: restaurar (insertar + índices) **17,91 s**; con verificación completa 24,09 s.

## 4. Tamaños reales medidos sobre la copia restaurada (no el archivo)

`dbstats`/`collstats`: datos **190,57 MB** + índices **23,33 MB** = **213,90 MB** (329 131 objetos); `storageSize` 26,66 MB + índices 23,33 MB = 49,99 MB en disco. Frente a 512 MB de Atlas Free: **41,8 %** (objetivo ≤ 60 %: cumple; margen 93,3 MB). Desglose por colección en `T11A_INVENTARIO_BD.md`.

## 5. Detección de alteraciones (pruebas automáticas, bases sintéticas)

Un archivo del export alterado se rechaza antes de restaurar y no deja datos en el destino; un documento modificado tras restaurar (mismo conteo) se detecta por hash de contenido; un pronóstico borrado y un hijo huérfano se detectan en la comprobación de `children_ref`; restaurar sobre la misma base, sobre una base no vacía o sobre `demand_forecasting_v2/_dev` se rechaza.

## 6. Limpieza y estado final

Se eliminó **solo** `df_restore_t11a_20261017183220`. Se conservan `demand_forecasting_pub` y `artifacts/private/t11a/backup/`. `demand_forecasting_v2` y `demand_forecasting_dev` no se escribieron.
