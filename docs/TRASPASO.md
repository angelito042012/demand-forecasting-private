# Traspaso vigente

**Último traspaso, conteo revisado 18/10:** las 50 filas recibidas están completas. Cierre declarado 18/10/2026 17:00 Lima, sin ventas durante el conteo, Almacén Principal = almacén 1, confirmado por Rogelio. Fuente intacta, copia/CSV/revisión/validación en `artifacts/private/conteo_recibido_20261018_v2/`; usar v2, pues v1 precede a las confirmaciones. Informe `docs/REVISION_CONTEO_50_20261018.md`; encargo listo para enviar **ETAPA_18_CLAUDE.md** (inventario reportado fechado, entorno local aislado). No regenerar la plantilla ni editar el Excel recibido. Todavía faltan ventas octubre para pronóstico actualizado y pedidos pendientes para compra operativa; no convertir desconocidos en cero. No se tocó ninguna base/app/servicio/nube. La preparación académica anterior se conserva como antecedente, sin confundir sus saldos con este conteo.

**Última entrega Codex, 18/10 — preparación académica v1 terminada:** leer `docs/PREPARACION_DATOS_ACADEMICA_V1.md`. Paquete privado `artifacts/private/datos_preparados_v1/`: 14 originales conservados, CSV del universo, 50 productos seleccionados con corte julio, cuatro XLSX y verificación. 106.525 filas reconciliadas, 7 pruebas dirigidas aprobadas. Dos filas separadas; seis copias marcadas y conservadas; créditos separados. Inventario calculado retrospectivo, nunca conteo físico ni entrada predictiva. No se tocó aplicación, bases, T12, servicios o Azure. No iniciar otra etapa automáticamente: revisar el paquete con Rogelio antes de definir importación/estudio. El párrafo siguiente describe el estado previo a esta autorización de preparación.

**Actualización Codex,18/10/2026:** Rogelio recibió compras marzo–septiembre y ventas de septiembre, y pidió revisar los14Excel antes de decidir alcance o validar interfaz. Auditoría de solo lectura en `docs/AUDITORIA_NUEVOS_DATOS_14_EXCEL.md`; detalle privado `artifacts/private/auditoria_14_excel/audit.json`. Hay1 802productos comunes, pero saldo inicial desconocido: compras−ventas no identifica inventario real. Pendientes: aclarar incidencias y decidir si es posible verificar un saldo real para un grupo de productos. No importar, deduplicar ni entrenar por inferencia de esta auditoría; T12 se conserva. UX01R/R17 ya revisados y aceptados localmente en REVISION_CODEX_17 (las menciones posteriores a revisión pendiente son históricas). No se cambió estado de servicios ni se accedió a nube.

## Estado al 18/10/2026 (Claude, tras la etapa 18)

Último commit de código: `464eb0c` (inventario informado). UX01/UX01R aceptados localmente por Codex (REVISION_CODEX_17); R12–R17 no se repiten.

### Entornos locales (ambos solo en 127.0.0.1, certificado autofirmado)
| | Dirección | Imagen | Base | Comando |
|---|---|---|---|---|
| Demo anterior (sin Inventario informado) | https://localhost:8443 | `df-app:ux01r-f95092f` | `df_demo_20261017221940` | `.venv\Scripts\python.exe -m scripts.demo_local up|status|stop` |
| Ensayo T18 (con Inventario informado) | https://localhost:8444 | `df-app:t18-464eb0c` | `df_ens18_20261018172811` | `.venv\Scripts\python.exe -m scripts.demo_local --env ens18 up|status|stop` |
Credenciales (nunca imprimirlas): demo en `artifacts/private/t13b/demo_credenciales.txt`; ensayo en `artifacts/private/t13b/ens18_credenciales.txt`. `df-mongo-dev` se encendió solo para las pruebas backend; no lo necesitan las demos. Nunca `down -v`; no tocar contenedores ajenos.

### Hecho en la etapa 18
Contrato `docs/T18_CONTRATO_INVENTARIO_INFORMADO.md`, importador `pipeline/inventory/reported_count.py` (CLI; `demo_local --env ens18 import-count …`), API `GET /api/v1/inventory/reported[/snapshots]`, pantalla `/inventario`, `demo_local` multi-entorno y compose con `DF_APP_IMAGE`/`DF_EDGE_PREFIX`. Snapshot `invrep-20261018T1700-a1-608d15a74a58` (v1): 50 productos, 48 con existencia, 2 sin. Reporte `docs/T18_REPORTE.md`.

### Pendiente
1. **Prueba humana de Rogelio** en 8444: tres tareas de comprensión (`docs/T13_GUION_ACEPTACION.md`) + consultar el inventario informado. Aceptación humana y la observación «No comprendió el uso en su primera visita» siguen abiertas hasta sus respuestas reales.
2. Revisión de Codex de la etapa 18.
3. **Datos faltantes:** ventas del 01/10 al corte del conteo (sin ellas no hay pronóstico ni recomendación actualizados; no son cero); compras/movimientos de octubre y pedidos por recibir (desconocidos, no cero).
4. Azure/Atlas/publicación: **sin autorización**; plan en `docs/T11_PLAN_DESPLIEGUE.md`. T14 final, T15 (entrega 23/10/2026).
- Si se interrumpe: `git status`, `docker ps -a`, `demo_local status` y `demo_local --env ens18 status`.
