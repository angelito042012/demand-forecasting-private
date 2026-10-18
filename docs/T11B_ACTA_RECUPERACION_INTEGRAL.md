# T11B Acta de recuperación integral (R13): Mongo + bundle privado de artefactos

Fecha: 17/10/2026 (America/Lima). Prueba **local** (MongoDB 127.0.0.1); sin nube ni transferencia de datos. Sin filas comerciales ni secretos en este documento. Inventario simulado con supuestos; no es inventario real. Evidencia JSON: `artifacts/private/t11b/acta_recuperacion_integral_20261017193251.json` (privada, fuera de Git).

## 1. Qué cierra R13

El respaldo T11A solo enumeraba 18 archivos privados. Ahora hay un **bundle privado separado** (no dentro de Mongo ni de Git) con lista cerrada `config/t11b_private_bundle.json`, y un comando de nivel superior que informa `mongo_ok`, `artefactos_ok` y `recuperacion_integral_ok` (true solo si ambos).

Contenido del bundle (43 archivos, 154 159 790 bytes = 147,02 MB):
- paquete T12 (`artifacts/private/final/`): manifiesto de preparación, `predicciones_fijas.npz`, `inicializacion_sim.npz`, `rf_categoria_T12.joblib`, `reales_bloque.npz`, `ventas_agosto_min.csv.gz`, `predictivo.json`, `simulacion.json`, `simulacion_series.npz`, `auditoria.json`, `estado.json`, `verificacion.json` (12);
- anclajes versionados: `docs/T12_SELLO.json`, `T12_MANIFIESTO.json`, `T12_METRICAS.json`, `config/seleccion_congelada.json` y `.sha256`, `config/t07_config.json`, `config/t08_publish.json`, `docs/T07_MANIFIESTO.json`, `T07_METRICAS.json` (9);
- referencia T07: `predicciones_folds.csv.gz`, `simulacion_series.npz` (2);
- sección separada `runtime_reference` (opcional, incluida porque existía): 20 archivos con su `manifest_referencia.json`.

Exclusiones declaradas en el manifiesto: `.env*`, contraseñas/tokens/sesiones/cookies/claves, `.git`, `artifacts/private/t07/modelos/` (47 MB; `verify_and_load` no los exige), xml/log de pruebas y checkpoints, datos crudos. Las rutas se validan (sin absolutas, `..`, `\`, unidades, `.git`, nombres de secretos, enlaces simbólicos).

## 2. Manifiesto y verificación

`bundle_manifest.json`: versión `t11b-bundle-1`, fecha UTC/Lima, `integro`, `faltantes`, por archivo ruta + bytes + sha256 de bytes (+ firma lógica `logical_sha256` en NPZ, misma función que el sello T12), sección `runtime_reference`, exclusiones. Un archivo de la lista cerrada ausente ⇒ `integro=false` y `export-all` falla salvo `--allow-partial`; un bundle parcial no se restaura. `recuperacion.json` registra el sha256 del manifiesto del bundle y del de Mongo; la restauración los exige (un manifiesto reescrito para coincidir con un archivo alterado se detecta).

## 3. Restauración y prueba funcional (sin regenerar nada)

Destino nuevo y vacío, distinto de originales y bundle (se rechazan: no vacío, la raíz del proyecto, directorios de originales, interior del bundle, path traversal). Verifica bytes y firma lógica antes y después de copiar. Prueba funcional sobre la copia restaurada:
- `FinalRun._load_sealed` (función real del runner) acepta el paquete; `estado.json` `completa=true` con las 7 fases completas; `predictivo.json` y `simulacion.json` (27 combinaciones) legibles; `T12_SELLO.json` coincide con el manifiesto de preparación; `seleccion_congelada` coincide con sello y `.sha256`.
- Referencia T07: sha256 de artefactos vs `T07_MANIFIESTO`, referencia aprobada (contenido normalizado) de manifiesto y métricas, `config_sha256`, y carga real de `_load_forecasts` (76 587 filas) y `_load_sim` (3 347 SKU). Comprobación adicional contra el commit aprobado `57901038…` con Git local (solo en esta prueba; el runtime no lo necesita).
- `runtime_reference`: 19 hashes declarados en `manifest_referencia.json` verificados.

## 4. Ventana de mantenimiento (procedimiento impuesto)

`export-all` aplica, en este orden: (1) `--maintenance-confirmed` obligatorio (el operador detiene API, worker y scheduler); (2) `check_maintenance`: sin corridas `staging`, sin jobs `running`, sin ticks `procesando`, sin operaciones de escritura activas en `currentOp` (si `currentOp` no está disponible se registra `no_disponible`, no se supone ok); repetido tras el export; (3) **consistencia fuerte**: hash de contenido por colección antes del volcado, del volcado y después de volcar todas; una mutación con el **mismo conteo** aborta el export y `export-all` retira lo creado. No se usa `fsyncLock` (bloquearía a otros procesos del Mongo compartido; queda como opción si el usuario lo autoriza). Ningún control sustituye detener los escritores: son barreras y detección.

## 5. Ejecución real

| Paso | Resultado |
|---|---|
| `export-all --db demand_forecasting_pub --out artifacts/private/t11b/respaldo --maintenance-confirmed` | ventana ok antes/después (0 staging, 0 running, 0 ticks, 0 escrituras activas); **40,57 s** (Mongo 36,34 s con consistencia fuerte; bundle 4,13 s); Mongo comprimido 13 049 693 bytes; bundle 154 159 790 bytes, `integro=true` |
| restauración Mongo en `df_restore_t11b_20261017193251` | `ok=true`, 0 problemas, 18,91 s, 329 131 objetos, datos+índices 213,597 MB; hash de contenido de las 10 colecciones igual a `demand_forecasting_pub` |
| restauración del bundle en `artifacts/private/t11b/restaurado_20261017193251/` | 43/43 hashes de bytes y lógicos ok, prueba funcional ok, 7,83 s; 43/43 idénticos a los originales actuales |
| **resultado** | `mongo_ok=true`, `artefactos_ok=true`, **`recuperacion_integral_ok=true`**; `restore-all` + comparaciones 33,88 s |

Hashes clave: sello T12 `d587255d87fb2d99e449a098e4c1fa6e1c1c6d5838180b7aa8fe098e9a2ce663`; `bundle_manifest.json` `3be38bba7b7b20e17d546c52072c8b543011d04aaa8c0bfb9889fd7e28f4549b`; `manifiesto.json` Mongo `cb1b145b451cde043e4ac6c277c5b9c7511c67c5a6712ed7025ff140f194c36e`; `manifest_referencia.json` `01f541a21531828cad0caa97a6818ffb8f254e5fb6f9de061a81d0288af3547c`.

Limpieza: se eliminó **solo** la base temporal `df_restore_t11b_20261017193251` (verificado). `demand_forecasting_v2`, `_dev` y `_pub` no se escribieron; no se borró ningún original. Se conservan `artifacts/private/t11b/respaldo/` y `restaurado_20261017193251/`.

## 6. Pruebas

`tests/ops/test_private_bundle.py` (nuevo): archivo ausente, alterado y extra; NPZ con firma lógica distinta; manifiesto reescrito; rutas inseguras (13 casos); config y manifiesto con traversal; `.env`/secretos rechazados; enlace simbólico (detección simulada: en Windows sin privilegio la prueba con symlink real se omite); destino no vacío/original/interior del bundle; respaldo parcial no íntegro; estado incompleto y sello alterado detectados por la prueba funcional; ventana de mantenimiento (sin confirmar, job running, tick, staging); **mutación con el mismo conteo** detectada durante el volcado y entre huella y volcado (el control solo-conteos no la detecta); `export-all` no deja residuos al fallar; mongo_ok y artefactos_ok independientes; CLI. Además se corrigió un defecto de `restore_db`: una colección vacía sin índices propios no se recreaba (ahora se crea).

## 7. Límites

No se implementó archivo selectivo de corridas. Los modelos T07 (`modelos/`, 47 MB) no están en el bundle: no son necesarios para verificar/cargar T07 ni para el paquete T12, pero un reentrenamiento exigiría la fuente de datos. El bundle de `runtime_reference` es una instantánea del estado a las 19:3x; si ese directorio se reconstruye después, hay que repetir `export-all`.
