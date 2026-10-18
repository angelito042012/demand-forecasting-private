# Estado vigente del proyecto

Actualizado el 17/10/2026, Lima. Fecha final 23/10/2026. Claude ejecuta y Codex dirige/revisa; un ejecutor principal activo. Historial en HISTORIAL_ENTREGAS.md; revisiones 01–12. Este resumen sustituye estados anteriores.

## Siguiente encargo

**UX01R entregado (17/10/2026; `docs/UX01R_REPORTE.md`)** tras `REVISION_CODEX_16`: **R17 cerrado con evidencia** (lista de análisis sin bucle, error visible con «No pudimos cargar tus análisis» y Reintentar, regresión que falla sin el arreglo), **Evaluación de resultados simplificada** (vista inicial breve + «Ver cómo se evaluó: detalle académico»; H14 01–14/08 distinto del bloque 01–21/08) y cinco precisiones de lenguaje. Pruebas: frontend 234/234 y build de producción; comprobación acotada en la imagen real 18/18 (incluye error de carga simulado en el navegador). **Demo actualizada y encendida** en `https://localhost:8443` (imagen `df-app:ux01r-f95092f`, misma base `df_demo_20261017221940`; recargar con Ctrl+F5 e ingresar de nuevo). El rediseño UX01 (`docs/UX01_REPORTE.md`, `docs/UX01_DECISIONES.md`) se conserva.

**Observación de Rogelio (abierta): «No comprendió el uso en su primera visita».** La aceptación humana sigue **pendiente** hasta su nueva prueba con `docs/T13_GUION_ACEPTACION.md`. R12–R16 aceptados localmente; no repetir. **No existe autorización de publicación, gasto ni transferencia a nube**; ETAPA_15 sigue diferida. Cuentas/cuota Azure ya resueltas, no repetir.

## Antecedente T13B, ya revisado antes de la observación UX

**Etapa 14 (T13B) entregada para revisión de Codex el 17/10/2026** (`docs/T13B_REPORTE.md`): R15 (medidor de rendimiento) y R16 (demostración con base común) cerrados; **demostración local activa** en `https://localhost:8443` sobre la copia restaurada `df_demo_20261017221940` (solo 127.0.0.1); paquete de publicación para **una sola autorización** en `docs/T11_PLAN_DESPLIEGUE.md`. R12–R14 aceptados localmente; no se repiten. No hay recursos facturables, imágenes subidas ni datos transferidos; Azure: `Microsoft.App` registrado, `ManagedEnvironmentCount` Brazil South 0/1. Siguiente: aceptación humana por Rogelio con `docs/T13_GUION_ACEPTACION.md` (**pendiente**; no se completa por inferencia); decisión sobre el mensaje único de autorización de nube; T14 final y T15 (entrega 23/10/2026).

## Hitos aceptados

- Datos: seis Excel originales intactos en C:\Users\rogel\Documents\Datos, 87437 líneas =86877 ventas +560 notas de crédito;31 columnas homogéneas. No pedir reexportación. Importador schema2/fuentes aprobadas/conciliación/barrera temporal R01–R04 aceptados para esas fuentes. Base activa demand_forecasting_v2; v1 demand_forecasting_dev conservada.
- Decisiones: TIPO_DOC=7 notas de crédito, sin inferir retorno físico. Máscara 03/04,12/04,07/06, sin ceros ni calendario comprimido. Categoría por corte; SKU 16140041 al 31/07 permanece ROSTRO. Inventario sintético autorizado y rotulado, sin impacto real demostrado. Ventas pueden estar censuradas por stock desconocido.
- T04:459375 filas SKU-día y5441categoría-día. T05–T07 aceptados como desarrollo; RF/XGBoost no mejoraron referencia SKU. T07 H14WAPE RF0,9292 frente promedio0,8726,0/4 folds favorables. Operativo promedio_28 por SKU, categorías=sumSKU; RF comparador. Simulación27 combinaciones/3347 SKU/61 días bajo supuestos; más servicio con más stock/compras no demuestra superioridad.
- T08/T09/T08R: autenticación sesión HttpOnly/CSRF/roles, lectura/API/UI conectadas; mocks solo con demo=1 rotulado. Exactitud racional R05 y proxy local R06 corregidos; histórica corregida activa y anterior superseded conservada. Congelación final previa al test en docs/SELECCION_CONGELADA.md y config/seleccion_congelada.json +checksum, conservada como registro previo al test; evaluación ejecutada en T12.
- T10/T10R: carga web/admin, cola durable, generación promedio_28, worker, timer manual/deshabilitado por defecto; login atómico, publicación por intento, limpieza con reserva CAS, takeover con lease leído, reserva por mes/fuente, recuperación de tick. Frontend/lector sin permisos de mutación. Desarrollo web continúa limitado a origen 01/06–10/07,H<=21, sin agosto.

## Revisión Codex10 y límites

**59 pruebas selectivas aprobadas,0 omitidas,43,65s**, incluida cadena timer --loop +worker/Mongo reales con reloj acelerado y procesos terminados. Ruff de archivos afectados limpio. Logs previos confirman regresiones fallaban antes. No repetir suite completa ni frontend/T06/T07 por rutina. Evidencia privada codex_review10_tests.xml/.log y codex_review10_audit.json; revisión REVISION_CODEX_10.md.

Resultados propios de Claude, separados: T10R408 pytest/6 omitidas(sin RUN_REALDATA), T10 frontend106/build y Chrome16/16; no nuevos resultados de navegador del revisor. R07–R10 resueltos en alcance web/local; un bulk ya enviado puede terminar, reserva misma SHA y upserts mantienen idempotencia. **CLI importadora serial y nunca junto a cargas web/worker.** Reserva partial requiere remediación privilegiada. Scheduler con fuentes/config estables; antes de hacerlas dinámicas persistir identidad por ranura. Dos validadores/estilo ajeno quedan como mantenimiento, no bloqueo.

## Base y operación

- Histórica activa: hist-20260710-4ea348836e35, completed; anterior hist-20260710-52b01cd999dd, superseded. Ambas conservan77343 pronósticos/3647 recomendaciones/1 backtest. Corrida activa:3347con snapshot simulado y300sin snapshot,582 pedidos positivos/2655 unidades auditados previamente.
- Gen-20260620-d438bef389c9 pasó de staging a failed/INTENTO_ABANDONADO por mantenimiento seguro, documento conservado sin hijos; no se reejecutó. Otras generadas son pruebas, no evidencia de mejora.
- **459394400 bytes =459,39 MB** de datos lógicos+índices, última medición solo lectura. No migrar automáticamente el histórico completo ni borrar evidencia. T12 no inserta masivamente nuevas corridas en v2.
- activate_run=False en desarrollo; histórica predeterminada, generadas por enlace/selector. Scripts/start-local.ps1 y stop-local.ps1 controlan procesos propios; Mongo útil se conserva. Claude reportó procesos detenidos; revisión solo inició procesos aislados de tests y los cerró.
- Credenciales privadas nunca se imprimen/versionan; no leer .env ni archivo de credenciales demo para revisar. Hashes del documento/JSON/checksum congelados idénticos a9596d26, comprobados antes de T12.

## Nube y entregas restantes

Azure for Students activado según captura:US$100 disponibles hasta 17/10/2027. Atlas Free demand-forecasting-dev creado en São Paulo; aplicación aún sin conexión/migración/despliegue verificados. Rotación de credencial mostrada en captura pendiente de confirmación privada; nunca pedir contraseña por chat. Sin presupuesto de bolsillo ni conversión a pago por uso autorizados.

Después de T12 y su revisión: T11 capacidad/archivo recuperable/HTTPS/almacenamiento durable/copia-restauración, integración del paquete final; T13 rendimiento/accesibilidad y aceptación humana; T14 informe/manual/video; T15 entrega antes 23/10. T01CI/instalación limpia y conciliación con reporte externo de la MYPE siguen parciales cuando corresponda; no inventar su cierre. No alternancia automática de cuotas; usuario avisa del cambio de ejecutor. Commits locales autorizados, secretos/datos excluidos.

## T12 evaluación final (17/10/2026, ejecutada una vez)

- Fases: verificación → preparación (≤31/07, sellada: `docs/T12_SELLO.json`, commit 86325a7) → lectura de agosto (14 946 líneas, 24 404 unidades, 01–31/08) → evaluación predictiva → simulación secuencial → auditoría → reporte. Las cinco fases de cálculo completas; auditoría y reporte existen, pero no registran sus checkpoints (R11) y estado.json conserva completa=false. No se repitió la evaluación real. Código de evaluación y pruebas fijados en a39d3e9 antes de la fase real. Selección congelada intacta (JSON `8a913805…`, documento `655e0322…`).
- Código congelado: 12 de 14 archivos vivos idénticos al commit e5466413; el motor de simulación se usó desde su copia exacta (`pipeline/final/frozen_code/`, `09cddb7d…`); `importer.py` (T10R) no interviene en el cálculo.
- **Hallazgo primario** (WAPE acumulado H14, SKU, cohorte primaria, universo común n=3 401): promedio_28 **0,7810**; RF categoría distribuido 0,7910 (mejora relativa −1,3 %, RF no mejor); control cero 1,0000; sesgo/observado +2,0 % y +3,0 %. H10 0,8165 vs 0,8308; H21 0,7512 vs 0,7590. Categoría H14 (suma de SKU vs RF): 0,1170 vs 0,1166. Historia corta (357 SKU) H14: promedio_28 1,0618 (sesgo +46,7 %), RF 0,8009. Con un solo bloque RF no puede declararse ganador; el método operativo no cambia.
- SKU nuevos: 103 SKU con venta en el bloque 01–21/08 (353 uds.; cobertura de unidades del universo conocido 97,85 %); 141 SKU / 568 uds. en todo agosto, fuera del universo simulado.
- Simulación L7/S7 (supuestos): fill rate referencia 0,7561, promedio_28 0,7792, RF 0,7812. Frente a la referencia, promedio_28 mejora servicio (+2,3 pp) con +9,7 % de stock medio y +15,8 % de compras; RF frente a promedio_28: +0,19 pp de servicio con +5,5 % de compras y +5,9 % de valor de stock final (RF mayor fill rate en 6 de 9 escenarios, con más compras en 9 de 9). No es mejora demostrada: más servicio coincide con más stock/compras.
- Auditoría separada aprobada (métricas recomputadas desde predicciones selladas y reales guardados; 27 combinaciones con balances re-verificados; sello anterior a la lectura de agosto).
- Pruebas ejecutadas: 16 pruebas sintéticas T12 (bloqueo sin confirmación/congelación alterada/sello alterado, futuros no cambian el paquete, truncamiento por revisión, categorías = suma SKU, conservación RF, catálogo/cohortes/universo al 31/07, faltantes/ceros, SKU nuevos, igualdad de condiciones, balances, denominador cero, equivalencia con el motor vivo); `pytest tests`: 424 aprobadas, 6 omitidas (RUN_REALDATA), 0 fallos. No se repitieron T06/T07 ni los 4 folds.
- Artefactos privados en `artifacts/private/final/` (fuera de Git). Pendientes: revisión Codex; integración web/publicación y plan de capacidad (T11); aceptación humana.

## T11B cierres locales y preflight (17/10/2026, verificado)

- R12: cierre del reporte atómico y bajo control de error (acc9251); fallo tardío ⇒ `reporte=error`, `completa=false`, manifiesto previo invalidado; 2 regresiones fallaban antes.
- R13: bundle privado verificable + `export-all`/`restore-all` con mantenimiento impuesto; export 40,6 s, restauración del bundle 7,8 s (43/43 hashes), Mongo 18,9 s (10/10); `mongo_ok`, `artefactos_ok` y `recuperacion_integral_ok` = true, por separado.
- R14: paquete de referencia de runtime sin Git (19 archivos, 7,6 MiB, anclado a los hashes aprobados versionados) y generación real 10/07 H21 por API→job→worker en la imagen (0,5 vCPU / 1 GiB): 22,2 s, pico 406 MiB, sin OOM, recomendaciones idénticas a la histórica auditada, idempotente y sin duplicados tras `docker kill`.
- Plan Azure corregido: tabla de medidores con fecha/URL, grants compartidos por suscripción, worker no presumido ocioso (medido 0,0097 vCPU), medidor de gestión de entorno anclado a la documentación, rangos conservadores; propuesta principal: modo A, US$ 4–17 estimados, crédito máximo US$ 20, parada > US$ 12. Bicep con share de referencia de solo lectura compila sin errores.
- Pruebas: regresión T11B 440 aprobadas / 5 omitidas; pruebas nuevas R12 (4), R13 (67/1 omitida), R14 (22 + generación real). No se repitió la suite completa ni el navegador.
- Pendientes: registrar los demás proveedores (con aprobación; `Microsoft.App` ya registrado y `ManagedEnvironmentCount` Brazil South 0/1), saldo en portal, usuario/credencial de Atlas y lista de IP, `df-ref`, primer push de imagen, T13–T15.
- Azure (17/10/2026): preflight de solo lectura y registro autorizado únicamente de `Microsoft.App`; resultado en `artifacts/private/t11b/azure_microsoft_app.json`: proveedor ya `Registered` al comenzar la comprobación, `ManagedEnvironmentCount` Brazil South 0/1; sesión cerrada y caché borrada. La causa del 0/0 anterior no queda demostrada. Los demás proveedores siguen sin registrar.

## T13A pruebas locales (17/10/2026, verificado; detalle en `docs/T13A_REPORTE.md`)

- Rendimiento local (stack en contenedores 0,5 vCPU / 1 GiB, base restaurada nueva, 3 consultas, 1 y 5 sesiones, 20 medidas/sesión tras calentamiento): p95 máximo 373 ms (meta < 2 s cumplida en local), 0 errores, pico de la API 91,4 MiB, arranque en frío 6,1 s; estrangulación de CPU observada (150/647 periodos).
- Chrome sobre la imagen de producción: 22/22 (lector, admin, 375 px); agosto rechazado; generación 10/07 desde la UI y reenvío idéntico sin duplicar; histórica predeterminada intacta.
- **Defecto corregido:** la imagen de producción no aplicaba el CSS global (carga diferida con `onload` bloqueada por la CSP). Cambios: `frontend/angular.json` (`inlineCritical:false`) y `frontend/src/styles.scss`. Imagen reconstruida; no se repitieron las pruebas unitarias de Angular (cambio de estilos/compilación).
- Accesibilidad: revisión automatizada sin hallazgos importantes (único contraste bajo: botones deshabilitados, exentos); sin lector de pantalla, zoom 200 % ni objetivos táctiles. A13 (HTTPS/cinco usuarios en nube) y A14 (participación humana) siguen pendientes.
- Pendientes: decisión/aprobación de publicación; credencial/usuario Atlas por canal privado; registro de los demás proveedores; ejecución humana del guion; T14 final y T15.

## T13B cierres R15/R16 y demostración (17/10/2026, verificado; detalle en `docs/T13B_REPORTE.md`)

- R15: `scripts/t13a_perf.py` con nearest-rank, rechazo de tandas incompletas (código 1), errores por hilo contabilizados, cierre en `finally`, timeout de arranque, TLS verificado por defecto, muestras crudas privadas; 9 regresiones sintéticas aprobadas. Cifras anteriores de T13A = cota conservadora; ensayo corto repetido con el medidor corregido: p95 máx. 298,6 ms, `completa=true`; máximos de 2,06–2,50 s en la primera solicitud de 2 de 5 sesiones (informados aparte).
- R16: `scripts/demo_local.py` (up/status/create-user/stop/down) sobre el compose; misma URI y base inyectadas a api, worker y creación de usuarios; comprobación por hash sin imprimir secretos; demostración `df-demo` activa (histórica activa, sustituida y final visibles; lector 403 al generar; HTML sin `media=print`/`onload`, CSP intacta, solo loopback). Mantenimiento: PowerShell y compose documentados por separado; sin `down -v` rutinario.
- Pendientes: ejecución humana del guion; autorización única de nube (alcance, US$ 20, intervención a US$ 12, política posterior a decidir); revisión Codex; T14 final y T15.
