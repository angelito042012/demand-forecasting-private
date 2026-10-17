# T12 Protocolo de ejecución: evaluación final de agosto bajo selección congelada

Fecha: 17/10/2026 (America/Lima). Encargo: `ETAPA_10_CLAUDE.md`, autorizado por Codex tras aceptar T10R (`docs/REVISION_CODEX_10.md`). **Este documento, el código y las pruebas se fijan en Git antes de ejecutar la fase real y antes de leer agosto.** No modifica `docs/SELECCION_CONGELADA.md`, `config/seleccion_congelada.json` ni su `.sha256`: sus indicadores «sin ejecutar» son el registro de lo decidido antes del test; el estado real vive en `artifacts/private/final/estado.json`, en `docs/T12_MANIFIESTO.json` y en ESTADO/TRASPASO.

Inventario simulado con supuestos; no corresponde al inventario real de la empresa.

## 1. Qué se evalúa (todo lo demás está congelado)

- **Predicción fija**: origen único 31/07/2026, bloque 01–21/08 (h = 1…21). Métodos: `promedio_28` por SKU (operativo), control `cero`, y RF por categoría distribuido a SKU (comparador experimental; parámetros, features `t07-1`, pesos, semilla 20261017 y horizontes de `config/t07_config.json`). Categoría: baseline operativo = **suma de los pronósticos SKU** (no una media independiente de la serie agregada); RF con conservación categoría→SKU y fallbacks de pesos contados. Criterio primario: WAPE acumulado H=14, SKU, cohorte primaria, universo común; se informan H10/H14/H21 y diario, SKU y categoría, primaria e historia corta, cobertura, MAE, RMSE, sesgo, sub/sobre y MAPE solo con reales positivos (con su cobertura). R² solo si es definible (n ≥ 30 y varianza > 0).
- **Simulación secuencial** (distinta y separada de la predicción fija): 01–31/08, universo conocido al 31/07, políticas `referencia_fija`, `promedio_28`, `rf_categoria_distribuido`, L ∈ {3,7,14} × S ∈ {0,7,14}, R = 7 (27 combinaciones; principal L7/S7). Revisiones al final de los días 1, 8, 15, 22 y 29 de agosto con matrices **físicamente truncadas** (solo historia disponible hasta ese día; RF reentrenado con etiquetas ≤ día de revisión; `promedio_28` actualizado; la referencia fija permanece congelada al inicio). La incorporación de pasado de agosto vale solo aquí y no toca las predicciones fijas.
- Sin umbrales prometidos. Con un solo bloque no se aplica la regla de tres folds: RF no puede declararse ganador; se informan la mejora relativa frente a `promedio_28`, el sesgo y la cobertura. Los resultados desfavorables y el control cero se conservan.

## 2. Código usado y verificación de la congelación (fase `verificacion`)

`pipeline/final/frozen.py::verify_freeze` comprueba (sha256 con CRLF→LF) y registra en `verificacion.json`:

1. `config/seleccion_congelada.json` contra `config/seleccion_congelada.sha256` (`8a913805…ef8d`).
2. `docs/SELECCION_CONGELADA.md` contra su versión en 9596d26 (`655e0322…616f`).
3. `config/t07_config.json` contra el hash de la congelación (`e695f95d…7f79`).
4. Los 14 archivos del módulo experimental contra el commit `e5466413ef58af372cd0e1e8afade7cfad35bb4b` (todos coinciden con git) y contra el estado vivo.

Resultado de la verificación previa a T12: 12 de los 14 archivos vivos son idénticos a los congelados (incluidos `training_access.py`, `t05/t07/features/models/metrics/baselines`, `catalog/daily_series/calendar/sources`). Difieren dos, y se tratan así:

| Archivo | Diferencia | Uso en T12 |
|---|---|---|
| `pipeline/sim/engine.py` | d59703b: validación de entradas y un balance diario adicional; mismas ecuaciones | Se usa la **copia exacta** del commit e5466413 (`pipeline/final/frozen_code/engine_e5466413.py`, sha256 `09cddb7d…727b`), cargada como módulo aislado; una prueba demuestra resultados idénticos con el motor vivo. |
| `pipeline/data/importer.py` | T10R: reserva de mes y valla de escritura | No se usa en el cálculo (T12 no importa ni escribe); solo `get_client`/`sha256_file`. |
| `scripts/run_t07.py` | no se ejecuta (ni sus cuatro folds) | Se toma como plantilla; `scripts/run_final.py` es nuevo. |

Si cualquier hash congelado no coincide, la ejecución se bloquea (`FreezeError`/`FinalGateError`); nunca se corrige en silencio.

## 3. Fases idempotentes y compuertas

`python -m scripts.run_final <fase>` (estado y checkpoints en `artifacts/private/final/estado.json`; un error se registra y nunca marca la ejecución como completa; retomar reutiliza artefactos válidos por hash):

| Fase | Qué hace | Lee agosto |
|---|---|---|
| `verify` | verificación de la congelación (§2) | No |
| `prepare` | `load_training_data(≤31/07)`; entrena/guarda el RF final, emite las predicciones fijas 01–21/08 y la inicialización de la simulación (universo, media inicial, cohorte inicial, costos); manifiesto con hashes de bytes y de **contenido lógico** (NPZ/ZIP con metadatos variables), fingerprints, commit, entorno, semilla; sello `docs/T12_SELLO.json` | **No** (prueba: la función de agosto, sustituida por una trampa, no se llama) |
| `evaluate --confirm-frozen-selection` | compuerta (confirmación explícita; congelación intacta; sello coincidente con los artefactos y **commiteado y sin cambios en Git**); registra la intención y recién entonces llama a `load_final_test_sales(…, frozen_selection_confirmed=True)`; guarda las ventas mínimas de agosto (fecha, SKU, almacén, cantidad; sin identificadores personales); evalúa y simula | Sí, solo aquí |
| `audit` | auditoría separada, sin MongoDB ni reentrenamiento (§5) | No |
| `report` | `docs/T12_RESULTADOS.md`, `T12_METRICAS.json`, `T12_MANIFIESTO.json` | No |

Reglas de datos: calendario natural sin comprimir; máscara 03/04, 12/04 y 07/06; créditos fuera del objetivo; un día sin ninguna línea no es cero ni servicio perfecto (sin evento ni denominador); NaN antes de la primera venta; un cero observado es 0. Catálogo, universo y cohortes al 31/07 sin corregir con agosto (incluido SKU16140041). SKU con primera venta posterior al 31/07 se reportan aparte (número, unidades, cobertura) sin historia, categoría ni stock inventados y quedan fuera del universo simulado.

## 4. Decisiones de implementación acotadas (cubiertas por el encargo)

- **Baseline de categoría** = suma de pronósticos SKU (`nansum`: un SKU sin pronóstico, p. ej. sin observaciones utilizables en 28 días, no aporta).
- **Referencia fija en la predicción fija** coincide con `promedio_28` en un único origen; se evalúa solo en la simulación (media inicial al 31/07 congelada).
- **Universo común**: entidades con pronóstico de los tres métodos; las excluidas se cuentan por cohorte.
- Estadísticos y agregación: los mismos de T05/T07 (`metrics.py`, `t07.eval_fold_predictions/summarize`); simulación: ecuaciones, orden de eventos, redondeo a 9 decimales, costo 65 % de la mediana de precio base con fallbacks, holding 20 %/365 y regla de techo T07.
- La fórmula exacta de la vista previa T08R **no** reemplaza a la simulación experimental congelada.

## 5. Auditoría y artefactos

`pipeline/final/audit.py` recomputa con numpy plano (no con `metrics.py`) WAPE/MAE/RMSE/sesgo por cohorte, método y vista **desde las predicciones selladas y los reales guardados**, no desde el JSON de métricas; cuenta universo y cobertura; comprueba categorías = suma SKU y la conservación RF; verifica que el sello es anterior a la lectura de agosto y que las ventas mínimas están en agosto; y revalida, para las 27 combinaciones, saldo final y diario, atendido + perdido = demanda, pedidos = recibido + tránsito, no negatividad, ausencia de faltante en días sin demanda conocida, mismo stock inicial entre políticas, identidad de valor y fill rate.

Privados (`artifacts/private/final/`, fuera de Git): `estado.json`, `verificacion.json`, `preparacion/` (predicciones, inicialización, RF, manifiesto), `ventas_agosto_min.csv.gz`, `reales_bloque.npz`, `predictivo.json`, `simulacion.json`, `simulacion_series.npz`, `auditoria.json`. Versionados: este protocolo, `docs/T12_SELLO.json`, `T12_RESULTADOS.md`, `T12_METRICAS.json`, `T12_MANIFIESTO.json`, código y pruebas.

## 6. Límites explícitos

No se re-seleccionan métodos ni parámetros; no se usa `reference_v1`; no se modifica la base v1/v2 (solo lectura), los Excel, las cargas ni el puntero histórico; no se inserta el paquete en `demand_forecasting_v2`, no se activa puntero ni nube, no se publica ni despliega. Cualquier repetición técnica tras leer el test se registra con motivo, versión anterior y efecto; no se repite toda la evaluación para confirmar que sale igual. Si aparece una incompatibilidad metodológica sustancial, se registra y se detiene la ejecución para revisión de Codex.
