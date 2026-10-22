# T20 — Actualización v2 (21/10/2026): reporte del checkpoint local para revisión de Codex

Checkpoint: commit **`3c94ab8`** (código) más el commit de este reporte; imagen del ensayo `df-app:t20-3c94ab8` en `https://localhost:8445` (ens19, misma base `df_ens19_20261018193002`; el plan v1 del 18/10 se conserva). Contrato: `docs/T20_CONTRATO_ACTUALIZACION_V2.md`; conciliación de origen: `docs/CONCILIACION_SQL_20261021.md`. Sin Azure/Atlas en este checkpoint. Aceptación humana: **pendiente**.

## 1. Qué se implementó
- **Dataset v2** (`pipeline/plan/dataset_v2.py`): los 14 libros verificados + `octubre.xlsx` como fuente 15 (ventas 01–20/10; 9 853 líneas, 5 609 documentos), corte de ventas **20/10**, ventana `promedio_28` **23/09–20/10**; exige que el SHA del libro y el informe de comparación registro a registro con SQL (`coincide: true`) correspondan. El 21/10 parcial (318 líneas, último documento 16:26:38) va a `plan_sales_partial` y el motor nunca lo lee. `dataset_id` `plds-1f4717744dc3` (v1 `plds-ac611eb67297` queda `superseded` y legible). 116 378 registros.
- **Existencia reconstruida** (`pipeline/inventory/reconstructed.py`): conteo físico reportado del 18/10 17:00 + movimientos del kardex hasta el cierre del 20/10; `invrec-20261020-445045630003`; 50 productos; 13 con diferencia frente al stock del sistema, **comparados en la misma fecha** (hasta el último movimiento 21/10 16:26:38); sin ajustes.
- **Plan v2** (`plan-2026-11-d20261021-d72cbd8fa9bd`): decisión 21/10, plazos 7/14, reserva 7 d, mínimo 1, múltiplo 1; supuesto explícito «No hay pedidos adicionales por recibir registrados… se supone que no llegan otros (sin confirmar con la empresa)»; `confirmations` pendientes (compras 11452/11455 no sumadas; 13 diferencias); `stock_provenance` por producto.
- **API:** `GET /plans/{a}/compare/{b}`, `GET /stock`, `/plans/inputs` con `kind` y decisión por defecto = cierre + 1.
- **Interfaz:** «Ventas previstas», «Existencias», «Compra recomendada», «Configuración de reposición»; «Reposición simulada» pasa a «Más → Evaluación académica» con su etiqueta metodológica intacta; discrepancia solo en los productos afectados; comparación v1/v2.

## 2. Primer día de consumo (comprobación expresa)
Existencia al **cierre** del 20/10 ⇒ día 0 = 21/10. Prueba automática: la serie va del 21/10 al 30/11 (41 días consecutivos, sin huecos ni repetidos, incluido el cambio de mes); el `inicio` del 21/10 es la existencia de cierre; llegadas 28/10 (7 d) y 04/11 (14 d). En el navegador el día a día de 3110044 empieza el 21/10. El 21/10 parcial no se resta del stock ni suma a las ventas.

## 3. Pruebas realmente ejecutadas
- Dirigidas: `tests/plan tests/backend tests/jobs tests/inventory tests/ops/test_t11_container.py`: **657 aprobadas, 5 omitidas** (370 s); con `RUN_REALDATA=1` el agente de datos corrió 162 pruebas (dataset v1/v2 reales en dry-run + existencias): todas aprobadas. Ruff limpio.
- Frontend: **294/294** y build correcto (agente de frontend).
- **Recálculo independiente** (`artifacts/private/t20/recalculo_independiente_v2.py`, sin importar el motor): 100 de 100 compras (50 × 7/14) coinciden con la API, 0 diferencias.
- **Importación real** en ens19 (idempotente: segunda corrida `unchanged`) y plan v2 generado por API→trabajo→worker en 2 s: 50 productos; 40 OK y 10 `LLEGA_TARDE` (solo con 14 días: llega el 04/11 y falta stock del 01 al 03/11).
- **Navegador sobre la imagen:** 16/16 (`artifacts/private/t20/e2e_t20_resultado.json`): menú, plan v2 por defecto, existencia reconstruida, confirmaciones, 13 indicadores de diferencia, entender la compra, día a día desde el 21/10, comparación, Existencias (50/13), evaluación académica con su etiqueta, administrador e idempotencia, 375 px.

## 4. Comparación v1 → v2 por producto
`artifacts/private/t20/comparacion_v1_v2.csv/.json` (50 productos). Cambian 21 compras a 7 días y 21 a 14 días (12 suben y 9 bajan a 7 días); 19 productos con compra en v1 y 19 en v2 a 7 días; 10 estados cambian a `LLEGA_TARDE`. Las existencias de v1 (18/10 17:00) y v2 (cierre 20/10) son de fechas distintas; la diferencia mezcla ventas nuevas, existencias y fecha de decisión. Ej.: 12040022: previsión diaria 0,607 → 0,357; compra 8 → 0.

## 5. Límites y pendientes
Compras 11452/11455 y las 13 diferencias, **pendientes de confirmar con la empresa**; los plazos y la reserva son parámetros configurados, no condiciones del proveedor; el stock del sistema no se explica con el kardex; el conteo sigue «reportado, no verificado»; el 21/10 parcial queda fuera del pronóstico. Nada publicado en Azure/Atlas ni en T12; demos 8443/8444 intactas (imágenes `t11a-local` y `t18r-616b5ef`).

## 6. R21 (REVISION_CODEX_20): flujo principal sobre el plan vigente (commit `ffa877f`, imagen `df-app:t20r-ffa877f` en 8445)
Inicio y «Ventas previstas» ahora leen el plan vigente con un servicio compartido (`current-plan.store.ts`, misma regla que Compra recomendada) y reutilizan los resultados ya calculados; los análisis históricos pasaron a `/evaluacion/ventas-previstas` y `/recomendaciones` (Más → Evaluación académica) con sus etiquetas intactas. Frontend 302/302 y build; recorrido en navegador sobre la imagen 9/9 (`artifacts/private/t20/e2e_r21_resultado.json`): mismo plan (`…d72cbd8fa9bd`), corte 20/10 y mismas cantidades que la API en 6 productos en Inicio → Ventas previstas → Compra recomendada; históricos accesibles con sus etiquetas. Pendiente conocido: cada pantalla pide sus resultados por separado; solo se comparten cabecera y selección.
