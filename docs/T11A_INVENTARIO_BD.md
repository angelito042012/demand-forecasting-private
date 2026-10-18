# T11A Inventario de la base de publicación `demand_forecasting_pub`

Fecha: 17/10/2026 (America/Lima). Preparación **local** (MongoDB 127.0.0.1, contenedor `df-mongo-dev`); no se creó ningún recurso externo ni se transfirieron datos. Inventario simulado con supuestos; no corresponde al inventario real de la empresa. Datos históricos de marzo a agosto de 2026. Sin filas comerciales ni secretos en este documento. Política: `config/t11_publication.json` (`t11a-1`).

## 1. Qué se creó y cómo

| Paso | Herramienta | Resultado medido |
|---|---|---|
| Copia desde `demand_forecasting_v2` (solo lectura) | `python -m scripts.build_publication_db` | 50,95 s; verificación origen vs copia por colección: conteo y hash de contenido idénticos; `ok=true`, 0 problemas |
| Publicación de la corrida final | `python -m scripts.publish_final` | `publicado` (6,99 s); segunda ejecución `sin_cambios`; `activate_run=False` |
| Exportación | `python -m scripts.backup_restore export` | 18,91 s; 13 049 693 bytes comprimidos |
| Restauración verificada | `ar.restore_db` (ver `T11A_ACTA_RESTAURACION.md`) | 17,91 s restaurar (24,09 s con verificación) |

La base `demand_forecasting_v2` y `demand_forecasting_dev` no se modificaron (el origen solo se leyó; una prueba compara el hash de todas sus colecciones antes y después sobre un origen sintético). `build_publication_db` se niega a sobrescribir una base existente salvo `--overwrite` y rechaza `demand_forecasting_v2/_dev/admin/local/config` como destino.

## 2. Colecciones de la base nueva (medidas tras restaurar; MB = 1 048 576 bytes)

| Colección | Documentos | Datos (MB) | Índices (MB) | Contenido |
|---|---:|---:|---:|---|
| `sales` | 86 877 | 78,0 | 13,5 | ventas importadas (copia exacta) |
| `credit_notes` | 560 | 0,5 | 0,15 | notas de crédito TIPO_DOC=7 (copia exacta) |
| `imports` | 12 | 0,005 | 0,05 | trazabilidad: completed y noop |
| `import_conflicts`, `import_rejects` | 0 | 0 | 0,01 c/u | vacías (índices creados) |
| `runs` | 3 | 0,015 | 0,09 | 2 históricas + 1 final |
| `forecasts` | 234 381 | 96,7 | 9,1 | 77 343 × 2 históricas + 79 695 final |
| `recommendations` | 7 294 | 14,7 | 0,32 | solo las 2 históricas (3 647 cada una) |
| `backtests` | 3 | 0,6 | 0,05 | 1 por corrida |
| `run_pointer` | 1 | ~0 | 0,01 | puntero nuevo → `hist-20260710-4ea348836e35` |
| `month_reservations` | (no existe en el origen) | – | – | sin documentos que copiar |
| **Total** | **329 131 objetos** | **190,57** | **23,33** | **datos+índices = 213,90 MB** |

`storageSize` (comprimido en disco) de la copia restaurada: 26,66 MB datos + 23,33 MB índices = 49,99 MB. Para la cuota se usa la medida conservadora datos+índices sin compresión.

Corridas en la base nueva (todas con sus hijos y `counts` coherentes, verificado):

| run_id | kind | estado | children_ref |
|---|---|---|---|
| `hist-20260710-4ea348836e35` | historical_development | completed (activa) | (hijos bajo el propio run_id) |
| `hist-20260710-52b01cd999dd` | historical_development | superseded (`quality_issue` R05 conservado) | (idem) |
| `final-20260731-d587255d87fb` | final_evaluation | completed (no activa) | `final-20260731-d587255d87fb~g1` |

La corrida final: 78 918 pronósticos SKU + 777 de categoría, 0 recomendaciones, 1 backtest (27 combinaciones y 108 diferencias). Capacidad estimada ANTES de insertar (BSON): 31,90 MB (+3,19 MB de índices estimados); medida real tras restaurar: 37,9 MB (datos 34,8 + índices 3,1 prorrateados).

## 3. Copiado, excluido y archivado

- **Copiado**: `sales`, `credit_notes`, `imports`, `import_conflicts`, `import_rejects`, las dos corridas históricas con sus hijos (mismos `_id`, `run_id` y `children_ref`; nada se reescribe), puntero activo nuevo hacia la histórica activa, y la corrida final con su backtest (publicada con el protocolo T10R).
- **Excluido (no copiado)**: `sessions` (22), `users` (2), `login_attempts` (0), `login_budget` (0), `jobs` (8), `scheduler_ticks` (no existe), `run_pointer` del origen (apuntaba a la histórica; se crea uno nuevo), y 7 corridas: seis generadas completadas (`gen-20260622…`, `gen-20260625…`, `gen-20260628…`, `gen-20260630…`, `gen-20260703…`, `gen-20260710…`) y la `gen-20260620-d438bef389c9` fallida. Motivo: credenciales/estado operativo o datos de prueba reproducibles.
- **Archivado fuera de MongoDB** (`artifacts/private/t11a/archivo/`, no versionado, 19 archivos, 6 547 821 bytes, manifiesto con sha256 `70e30a0b2acc…d9cdc`): documento de cada corrida omitida y sus hijos en NDJSON.gz (forecasts/recommendations) con conteo y hash de contenido por corrida (p. ej. 77 343 pronósticos y 3 647 recomendaciones en la generada del 10/07). **No se borró nada del origen.**
- **Referenciados por hash, no copiados a Mongo**: 18 artefactos de `artifacts/private/final/` (modelo `.joblib`, NPZ de predicciones y de simulación ≈128 MB, CSV mínimo de agosto, logs, auditoría) con nombre, sha256 y tamaño en el manifiesto de archivo y en el de backup. Los Excel originales siguen en almacenamiento privado fuera del repositorio.
- Secretos: ningún export, manifiesto ni documento contiene sesiones, usuarios ni credenciales (prueba automática busca marcas secretas en manifiestos y NDJSON).

## 4. Uso frente a la cuota de Atlas Free (512 MB)

| Medida | MB | % de 512 MB |
|---|---:|---:|
| Datos + índices de la base restaurada | **213,90** | **41,8 %** (objetivo ≤ 60 % = 307,2 MB: **cumple**) |
| Solo `storageSize`+índices (comprimido en disco) | 49,99 | 9,8 % |
| Antes de publicar la final (solo copia) | 176,43 | 34,5 % |

## 5. Proyección de crecimiento (medida por corrida)

Tamaño por corrida con `$bsonSize` real de sus hijos + índices prorrateados por documento:

| Tipo de corrida | Pronósticos | Recomendaciones | Total MB | % de cuota |
|---|---:|---:|---:|---:|
| historical_development (activa / sustituida) | 31,04 + 3,01 | 8,14 / 6,57 + 0,17 | 42,6 / 41,0 | 8,3 % / 8,0 % |
| generated_baseline (medida en v2, lectura) | 33,33 + 3,17 | 8,20 + 0,15 | 44,8 | 8,8 % |
| final_evaluation | 34,63 + 3,10 | 0 | 37,9 | 7,4 % |

Base fija (ventas+notas) = 92,3 MB (18,0 %). Margen hasta el 60 %: 307,2 − 213,9 = **93,3 MB ≈ 2 corridas generadas adicionales** (213,9 + 2 × 44,8 = 303,5 MB = 59,3 %); una tercera llevaría a 348 MB (68 %). Las medidas de las generadas provienen de la copia en `demand_forecasting_v2` (misma estructura); la proyección debe volver a medirse tras restaurar cuando exista una corrida real adicional.

Si el uso superara el 60 % (propuesta **no ejecutada**): archivar la corrida `hist-20260710-52b01cd999dd` (sustituida por defecto de calidad; 41,0 MB, 8 %) a NDJSON.gz recuperable (~4 MB comprimidos, con hash), dejando solo el documento de `runs` marcado `superseded`; liberaría ~41 MB (→ 172,9 MB, 33,8 %). La restauración selectiva usaría el mismo `restore_db`.

## 6. Reproducibilidad y hashes

Manifiestos en `artifacts/private/t11a/` (no versionados): `manifiesto_publicacion.json` (completo), `manifiesto_publicacion_docs.json` (sin datos, apto para docs), `archivo/manifiesto_archivo.json`, `backup/manifiesto.json` (sha256 `fa9561aa6e61…f434b`), `acta_restauracion.json`, `huella_por_corrida.json`, `huella_generadas_v2.json`. Hash de contenido (suma módulo 2^256 de sha256 de cada documento BSON; independiente del orden) de la base respaldada: `sales` f1931fc6902d3e9a…, `credit_notes` ba2c3335b69b6ce8…, `forecasts` d65835ea8a58f76a…, `recommendations` 24b0ccea0e3d2847…, `runs` 5a858103be0ffad4…, `backtests` 01d82fdba77f6a25…, `imports` 10193ef6da115e8d…, `run_pointer` 3e89c767c4c7126f…. Nota: `manifiesto_publicacion_docs.json` se generó ANTES de publicar la final (154 686 pronósticos, 2 corridas); la medición definitiva incluye la final y es la de `backup/manifiesto.json`.
