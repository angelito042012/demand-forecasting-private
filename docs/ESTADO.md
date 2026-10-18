# Estado vigente del proyecto

Actualizado el 17/10/2026, Lima. Fecha final 23/10/2026. Claude ejecuta y Codex dirige/revisa; un ejecutor principal activo. Historial en HISTORIAL_ENTREGAS.md; revisiones 01–11. Este resumen sustituye estados anteriores.

## Siguiente encargo

**T11A entregada para revisión de Codex** (`docs/T11A_REPORTE.md`): R11 cerrado, paquete final T12 integrado localmente, base de publicación con capacidad medida, copia/restauración comprobada, contenedores y plan de despliegue/costos. **No se creó ningún recurso externo, no se consumió crédito, no se transfirió ningún dato y no hay despliegue.** Pendiente: revisión Codex; después la autorización concreta del plan (`docs/T11_PLAN_DESPLIEGUE.md`: recursos, región, costo máximo, pasos) antes de aprovisionar; T13 aceptación y T14/T15 informe/manual/video antes del 23/10.

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

## Revisión Codex11 y entrada a T11A

16 pruebas sintéticas T12 aprobadas, 0 omitidas, 69,49 s; ruff afectado limpio. Evidencia propia: artifacts/private/codex_review11_verified_tests.xml/.log y codex_review11_audit.py/.json. Recalculados H14 primaria (3401 SKU, 10366 unidades): WAPE promedio_28=0,7809666, RF=0,7910422, cero=1; RF no mejora. Reconstruidos reales desde CSV mínimo y contrastadas las27simulaciones, saldos/valor/compras,9hashes y sello Git anterior a lectura. Sin repetir entrenamiento ni evaluación real. Resultados424pytest/6omitidas son de Claude, diferenciados.

R11 P2: siete fases definidas, pero audit/report no actualizan estado ni sus errores. Corregir/reconciliar solo esas operaciones, con registro posterior y hashes de cálculo intactos. Integración local y plan de capacidad independientes pueden avanzar; cierre total de T12 tras R11. No migrar la base completa: forecasts267,06MB, recomendaciones66,43MB y ventas81,79MB antes de índices. Preparar base nueva con datos/fuentes y corridas pertinentes, archivo recuperable del resto, sin sesiones/usuarios/jobs demo, sin borrar v1/v2 ni evidencias.

T11A no es despliegue: exige imagen(s), configuración producción, almacén durable, prueba de copia/restauración y plan de recursos/región/costo hasta23/10 y mensual. Cuentas ya creadas; acceso secreto por canal privado. Sin crear recursos/cargos, consumir crédito sin techo concreto acordado ni transferir datos en esta preparación. T13–T15 y publicación HTTPS real siguen pendientes.

## T11A preparación del despliegue (17/10/2026, verificado)

- R11: auditoría y reporte registran sus fases; `estado.json` del paquete real reconciliado (siete fases, `completa=true`) con corrección técnica posterior (commit base 71656c2) y hashes originales intactos. 6 regresiones (4 fallaban antes).
- Integración local de la evaluación final (`final_evaluation`, `final-20260731-d587255d87fb`): contrato `docs/T11_CONTRATO.md`; API/UI separan histórica T07, generada y final; fechas hasta 21/08 solo para esa corrida; recomendaciones no disponibles con motivo. Publicada en la base nueva `demand_forecasting_pub` (v1/v2 intactas).
- Capacidad medida tras restaurar: **213,90 MB datos+índices = 41,8 % de 512 MB**; ≈2 corridas generadas más hasta el 60 %. Copia 18,9 s, restauración 17,9 s (24,1 s con verificación), verificación 10/10.
- Contenedores: imagen única 991 MB, compose de ensayo, smoke 29/29; producción con secretos obligatorios, mismo origen, proxy de confianza explícito.
- Pruebas: `pytest tests` 511 aprobadas / 7 omitidas; vitest 127 y build; E2E Chrome 20/20 con el paquete final real sobre copia restaurada.
- Plan Azure (Container Apps + Files + ACR Basic + Atlas Free) ≈ US$5–7 hasta el 23/10, ≈ US$28–30/mes encendido; cifras de API pública de precios, varias **no verificadas** (egress, snapshots, medidor de gestión de entorno, regiones de Azure for Students, IPs de egreso hacia Atlas).
- Pendientes: aprobación del plan; crear admin de la base de publicación por canal seguro; conexión a Atlas (sin credencial); generación dentro del contenedor no probada; aceptación humana.
