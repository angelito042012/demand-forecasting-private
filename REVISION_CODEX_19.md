# Revisión Codex 19 — planificación de noviembre

18/10/2026, America/Lima. Entrega `2e99534`, `7dbb30b`, `f50f6a1`. **Resultado: implementación entregada; aceptación técnica pendiente de R19/R20.** La integración y las cuentas del escenario base están verificadas en el alcance descrito abajo. No hace falta rehacer el pronóstico, el dataset ni T12. Aceptación humana pendiente.

## R19 [P1] — un intento que pierde el trabajo puede borrar el resultado del nuevo

Archivo `pipeline/plan/store.py`, especialmente `clean_attempt()` y el bloque `except BaseException` de `generate_plan()` (líneas 216–221 de la entrega). Las filas se escriben y se eliminan solo por `plan_id`; la cabecera tiene `attempt`, pero los resultados no se aíslan por intento. Al fallar `guard()` tras un relevo, el manejador anterior ejecuta `delete_many({plan_id})` sin comprobar propiedad. Puede borrar resultados ya publicados por el sucesor y dejar una cabecera `completed` con cero filas. La limpieza inicial por `plan_id` también puede interferir con otro publicador; no se reserva el intento de forma atómica antes de limpiar.

Reproducción determinista con el código real de `generate_plan()`, motor real y colecciones en memoria (sin Mongo en vivo): en el segundo guard del intento anterior se completa un intento sucesor del mismo plan, y después se lanza `queue.LostOwnership`. El sucesor publica una fila; la limpieza anterior la elimina. Estado final: cabecera completada, `counts.products = 1`, cero resultados. Evidencia `artifacts/private/codex_review19/check_takeover.py` y `takeover_result.json`. Los dobles de base modelan únicamente las operaciones usadas; confirmar la solución también con Mongo temporal en el entorno del ejecutor.

Corrección requerida: reclamación/publicación y limpieza con propiedad por intento, sin borrar resultados ajenos o publicados. Reutilizar el patrón robusto del publicador histórico si resulta aplicable; no basta con añadir otro guard seguido de un borrado no condicionado. Aislar resultados por intento y seleccionar la versión publicada, o un mecanismo equivalente con exclusión y comparación atómica verificables. El intento obsoleto no puede escribir/borrar tras el relevo. Preservar plan completado anterior, idempotencia y reintentos.

Pruebas: relevo con publicación del sucesor antes de la limpieza del anterior; fallo tardío antiguo; intercalación durante limpieza inicial; mismo plan concurrente y lectura de resultados publicados. Demostrar que fallan antes y pasan después, con bases temporales y dos intentos controlados. No repetir suites/modelos ajenos al cambio.

## R20 [P2] — la pantalla consume una forma distinta de la API e informa supuestos incorrectos

`frontend/src/app/pages/plan.page.ts`, modelos y pruebas de contrato. La respuesta real de `backend/app/data/plan.py:get_plan()` incluye `params`, `dataset.sales_cutoff` y `dates.sales_cutoff`, mientras que la pantalla/fixtures esperan `parameters` y `sales_cutoff` en raíz. El detalle real de cada escenario entrega `series`, mientras que `dailyFor()` lee `daily`.

Consecuencias reproducidas:

1. La reserva, el mínimo y el múltiplo del plan no aparecen en el bloque de parámetros (se busca `h.parameters`). La captura aportada por Claude también carece de esos valores en ese bloque.
2. Al consultar un plan anterior con otro corte, se muestra el corte del dataset actualmente disponible, no el del plan (fallback a inputs). La prueba usa plan hasta agosto e inputs hasta septiembre: muestra septiembre.
3. «Ver el día a día» informa ausencia de serie aunque la API entregue `series` con las filas.
4. El aviso «En este escenario no llegan otros pedidos» está escrito de forma incondicional. Permanece incluso cuando el plan seleccionado contiene pedidos con fecha, y el formulario conserva un título equivalente al añadirlos. Debe distinguir «se consideran estos pedidos» de «no llegan otros adicionales» y mantener su naturaleza reportada/asumida.

Se añadieron temporalmente cuatro regresiones que usan la estructura real del servidor: **las cuatro fallan con la entrega**. Se archivaron fuera del código al terminar la ejecución: `artifacts/private/codex_review19/frontend_contract.spec.ts`, log `frontend_contract_run2.log`. El intento inicial no llegó a ejecutar pruebas por un error de permisos del caché temporal; la ejecución válida usa TEMP/TMP dentro del directorio privado y registra los cuatro fallos de aserción.

Corrección requerida: acordar y tipar un único contrato real, adaptar la pantalla (o un adaptador explícito), y probar con respuestas del servidor. Mostrar parámetros/corte/serie del plan seleccionado y pedidos de ese plan, no de valores por defecto ni del dataset más nuevo. Cubrir también `forecast: null` del servidor: hoy las plantillas acceden directamente a `forecast.month_total` y los fixtures usan un objeto con campos nulos, por lo que falta proteger ese estado para mostrar «no calculable». Verificar fecha requerida de decisión (`required_arrival_date` del servidor) si se muestra en la interfaz. No calcular cantidades nuevas en el navegador.

Pruebas dirigidas con cuerpo real: reserva/mínimo/múltiplo distintos de defaults; dos planes con cortes distintos; serie diaria no vacía; pedido pendiente no cero; no calculable con forecast nulo; datos de otro plan no sobreviven al cambiar versión. Recorrido corto en imagen ens19 para esos cambios. Mantener texto sencillo; la prueba humana sigue pendiente.

## Verificaciones propias aprobadas y límites

- Árbol limpio al recibir la entrega y después de archivar el archivo temporal de prueba. Existen los tres commits. Leídos contrato, reporte, normalización/importador, ventas/motor/publicación, API, cola y pantalla relevantes.
- **118 pruebas puras dirigidas aprobadas**: motor, descriptivo y normalización, 8,47 s. XML/log en `artifacts/private/codex_review19/pure_tests.*`.
- **1 prueba del paquete real aprobada**, 17,54 s: re-normaliza los 14 Excel y contrasta las 106.525 filas y clases contra los CSV, sin escribir en una base. `real_dataset.*`.
- Recálculo propio sin importar el motor: CSV de ventas de septiembre + conteo + consumo hasta llegada + horizonte/resto y reserva. **100 escenarios contrastados con la respuesta API guardada: cero diferencias**, 19 productos con compra y 31 con cero para ambos plazos. Es comparación contra evidencia guardada, no una nueva consulta en vivo. `recalculation.json`.
- T12, configuración congelada y módulos históricos T06/T07 sin cambios respecto a `be3d167` en los archivos revisados. No se reejecutaron.
- Revisados reportes del ejecutor de navegador 25/25, aislamiento de tres bases y captura de la pantalla; no se acreditan como recorrido o comprobación en vivo propios. Mongo local no accesible desde esta sesión (`ServerSelectionTimeoutError`); no se pidieron credenciales ni se operaron servicios.
- No se alteraron originales, datos, bases, servicios ni código de aplicación. El archivo temporal del revisor se movió a evidencia privada tras las pruebas. Los 119 éxitos propios no sustituyen los cuatro fallos frontend ni el fallo de recuperación R19.

## Encargo y siguiente paso

Claude corrige solo R19/R20, incorpora regresiones y entrega commits, evidencia dirigida, contrato/reporte/estado actualizados e imagen de ens19. Reutilizar su base y conservar demos 8443/8444, conteo, dataset y T12. No reimportar/reentrenar/restaurar todo por rutina; sin nube ni compras reales. Actualizar su lista de tareas conforme al trabajo efectivamente terminado: una lista desactualizada no invalida los commits, pero tampoco acredita terminación. Aceptación técnica de estas correcciones y acompañamiento real de Rogelio siguen pendientes. Después del cierre técnico, recorrido de comprensión en 8445 con `t19_lector`; no registrar aceptación por inferencia.
