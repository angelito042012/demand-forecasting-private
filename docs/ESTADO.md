# Estado vigente del proyecto

Actualizado el 17/10/2026, Lima. Fecha final 23/10/2026. Claude ejecuta y Codex dirige/revisa; un ejecutor principal activo. Historial en HISTORIAL_ENTREGAS.md; revisiones 01–10. Este resumen sustituye estados anteriores.

## Siguiente encargo

**ETAPA_10_CLAUDE.md (T12)** tras aceptar T10/T10R al commit 6212f6a en REVISION_CODEX_10.md. R07–R10 cerrados para demostración local. Preparar/verificar protocolo y referencias, sellar predicciones iniciales con marzo–julio y ejecutar evaluación final dedicada de agosto bajo selección congelada. No re-seleccionar ni alterar parámetros después del test. Mantener las barreras generales de entrenamiento/web, sin despliegue ni gasto en T12.

La autorización de agosto es exclusiva del encargo T12; todavía no se ejecutó. Predicción fija 01–21/08 desde 31/07 y simulación secuencial 01–31/08 son diseños diferentes. Base principal solo lectura; paquete final inicial en artefactos locales/manifiesto, integración web/nube en siguiente encargo tras capacidad y restauración. No abrir reference_v1.

## Hitos aceptados

- Datos: seis Excel originales intactos en C:\Users\rogel\Documents\Datos, 87437 líneas =86877 ventas +560 notas de crédito;31 columnas homogéneas. No pedir reexportación. Importador schema2/fuentes aprobadas/conciliación/barrera temporal R01–R04 aceptados para esas fuentes. Base activa demand_forecasting_v2; v1 demand_forecasting_dev conservada.
- Decisiones: TIPO_DOC=7 notas de crédito, sin inferir retorno físico. Máscara 03/04,12/04,07/06, sin ceros ni calendario comprimido. Categoría por corte; SKU 16140041 al 31/07 permanece ROSTRO. Inventario sintético autorizado y rotulado, sin impacto real demostrado. Ventas pueden estar censuradas por stock desconocido.
- T04:459375 filas SKU-día y5441categoría-día. T05–T07 aceptados como desarrollo; RF/XGBoost no mejoraron referencia SKU. T07 H14WAPE RF0,9292 frente promedio0,8726,0/4 folds favorables. Operativo promedio_28 por SKU, categorías=sumSKU; RF comparador. Simulación27 combinaciones/3347 SKU/61 días bajo supuestos; más servicio con más stock/compras no demuestra superioridad.
- T08/T09/T08R: autenticación sesión HttpOnly/CSRF/roles, lectura/API/UI conectadas; mocks solo con demo=1 rotulado. Exactitud racional R05 y proxy local R06 corregidos; histórica corregida activa y anterior superseded conservada. Congelación final previa al test en docs/SELECCION_CONGELADA.md y config/seleccion_congelada.json +checksum, sin ejecutar hasta ahora.
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
