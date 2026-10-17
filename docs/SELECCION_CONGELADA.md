# Selección congelada y diseño de la evaluación final (preparado, NO ejecutado)

Fecha de congelación: 17/10/2026, America/Lima. Configuración versionada: `config/seleccion_congelada.json` (sha256 en `config/seleccion_congelada.sha256`). Este documento y esa configuración se comprometen en Git **antes de cualquier lectura del test**. Este encargo solo prepara y congela: no se entrenaron paquetes finales, no se consultó agosto (ventas ni movimientos sintéticos) ni `reference_v1`, y no se ejecutó ninguna evaluación final.

## 1. Qué queda congelado

| Elemento | Decisión |
|---|---|
| Método operativo v1 | **`promedio_28` por SKU**: media de las observaciones utilizables (ceros válidos incluidos, días ausentes/enmascarados excluidos) de los 28 días naturales hasta el origen, constante para h = 1…21. Categoría = **suma** de los pronósticos SKU. Horizonte máximo 21 días. |
| Comparador experimental | **RF por categoría distribuido a SKU** (T07): mismos parámetros (100 árboles, profundidad 12, hoja mínima 20, `max_features` 0,5, semilla 20261017, 1 hilo), mismas features (`t07-1`), mismos horizontes (h = 1…21), mismos pesos de asignación. **No fue ganador en T07** (WAPE H14 0,929 frente a 0,873; 0 de 4 folds). Se evalúa como comparador, no como candidato a reemplazar. |
| Control predictivo | `cero`: control estadístico, no una política de compra. |
| Política sintética de referencia | `referencia_fija` (media de 28 días congelada al inicio × (L+R+S)): no es la política de la empresa. |
| Motor de simulación | `pipeline/sim/engine.py`; ecuaciones sin cambio desde T07 (el commit `d59703b` solo añadió validación de entradas y conservación diaria). |
| Referencia al módulo experimental | commit `e5466413ef58af372cd0e1e8afade7cfad35bb4b` de T07 y los sha256 de sus 14 archivos en la configuración; verificados contra `codigo_sha256` de `docs/T07_MANIFIESTO.json`. Si la API cambia después, la evaluación final apunta a esos archivos exactos (o a una copia con el mismo hash). |
| Resultados T06/T07 | Se conservan, incluidos los desfavorables. |

## 2. Diseño de la evaluación final (futura)

- **Corte inicial**: 31/07/2026. Universo y catálogo de categorías: los conocidos al corte (primera venta ≤ 31/07; catálogo con la regla de `DECISIONES_DATOS.md` al corte). Agosto está reservado hasta la autorización de ejecución.
- **Evaluación predictiva fija**: un bloque de **21 días desde el 01/08 al 21/08**, pronóstico emitido **una vez** en el origen 31/07 y sin usar ventas reales dentro del bloque. Acumulados a 10, 14 y 21 días y error diario; niveles SKU y categoría; cohortes por corte (primaria: ≥ 56 días de historia y ≥ 21 observaciones utilizables en 28; historia corta); universo común entre métodos. **Criterio primario**: WAPE acumulado a H = 14, SKU, cohorte primaria, universo común.
- **Simulación de todo agosto** (01/08–31/08): las tres políticas y los nueve escenarios T07 (L ∈ {3, 7, 14}, S ∈ {0, 7, 14}, R = 7; principal L = 7, S = 7). Universo, stock inicial (`⌈media_inicial·(L+R)⌉`), medias y costos (65 % de la mediana de precio base, holding 20 %/365) estimados **solo con datos ≤ 31/07**. Orden de eventos, 9 decimales antes del techo, demanda proxy exógena, días sin demanda conocida sin evento ni denominador: igual que `T07_PROTOCOLO.md`.
- **Predictiva fija ≠ simulación secuencial**: la evaluación predictiva no se reajusta dentro del bloque; la simulación reajusta semanalmente (final de los días 1, 8, 15, 22 y 29 de agosto) usando únicamente observaciones ya pasadas, con método y parámetros congelados (RF reentrenado con etiquetas ≤ día de revisión; `promedio_28` actualizado al origen de cada revisión). No se mezclan ni se promedian entre sí.
- **Pesos de asignación categoría → SKU (RF)**: unidades positivas de los 28 días anteriores al origen dentro de la categoría; si la categoría suma cero, proporción histórica hasta el origen; si sigue sin masa, reparto uniforme entre SKU conocidos. Se cuentan los fallbacks y se verifica la conservación del total de categoría.
- **SKU nuevos** (primera venta posterior al 31/07): se reportan aparte (cantidad, unidades, cobertura) sin historia inventada ni stock supuesto. Las 141 altas / 568 unidades auditadas antes no sustituyen esta evaluación.
- **Métricas**: WAPE (suma real > 0), MAE, RMSE, sesgo acumulado (predicho − observado), proporciones sub/sobre, cobertura; MAPE solo con reales positivos con su cobertura y los ceros excluidos; en simulación fill rate, perdidas, tasa de días-SKU con faltante, stock medio y final, pedidos, tránsito final, compras desembolsadas y costo consumido (supuestos) por separado, con diferencias absolutas y relativas frente a `referencia_fija` y `promedio_28` (denominador cero ⇒ no evaluable). Totales y por cohorte inicial.

## 3. Reglas de lectura (sin promesas)

- No se prometen umbrales (ni MAPE < 15 % ni R² > 0,85). No se vuelven a seleccionar parámetros, métodos, categorías ni horizontes tras ver agosto.
- Con **un solo bloque** no puede aplicarse la condición de ≥ 3 folds favorables de T07: RF no puede declararse ganador por la prueba final; se informan mejora relativa frente a `promedio_28`, sesgo (referencia: |sesgo|/observado ≤ 0,25) y cobertura. Una ventaja de servicio en simulación con más stock o compras no se presenta como mejora.
- Resultados desfavorables y el control cero se conservan y se reportan. El resultado no demuestra impacto en inventario real de la empresa.
- Si al implementar la integración aparece un defecto que afecte este protocolo, se documenta y se somete a revisión antes de modificar la congelación; no se cambia en silencio.

## 4. Protocolo de ejecución futura (no ejecutado)

1. Encargo explícito posterior de Codex tras revisar la integración y esta congelación.
2. Verificar hashes de este documento (registrado al comprometerlo), de `config/seleccion_congelada.json` y de los archivos del módulo experimental.
3. Cargar agosto únicamente con `load_final_test_sales(..., frozen_selection_confirmed=True)` en un script dedicado (`scripts/run_final.py`, **no implementado en T08**), con fuentes aprobadas y la barrera de corte.
4. Ejecutar el procedimiento una vez; guardar manifiesto con hashes de datos, fuentes, código, configuración y predicciones; publicar los resultados como corrida de prueba final, claramente distinta de la corrida histórica de desarrollo.
5. Sin re-selección posterior.

## 5. Estado

Congelado y **no ejecutado**. La demostración local de T08 es una corrida histórica de desarrollo al 10/07/2026 (backtest T07), no una prueba de agosto ni un despliegue.
