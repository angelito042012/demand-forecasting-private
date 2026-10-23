# T22 — Viabilidad de la actualización operativa autónoma (22/10/2026, 21:15 Lima)

Revisión hecha con el código, los archivos y las fuentes reales actuales. **Conclusión: completar hoy una actualización operativa autónoma, probada de extremo a extremo, NO es viable.** Se informa ahora, como pidió Rogelio, para decidir qué hacer con el tiempo restante. No se publicó nada incompleto como «actualización autónoma».

## 1. Qué existe y es reutilizable
- `pipeline/plan/normalize.py` (`normalize_book`: columnas, fechas, clasificación, `registro_id` por contador de ocurrencias, ventana de fechas), `pipeline/plan/dataset.py` (contraste registro a registro, `prepare`) y `dataset_v2.py` (SHA del libro = informe SQL, `coincide: true`, parcial en `plan_sales_partial`, `dataset_id` por contenido, versión nueva y anterior `superseded`, idempotente).
- `pipeline/inventory/reconstructed.py` (reglas de existencia: cierre = conteo + entradas − salidas; no negativos; conteo base igual al snapshot; SHA del CSV = manifiesto) y el motor `pipeline/plan/engine.py` + trabajo `generate_plan` (versiones e idempotencia por identidad de contenido).
- Interfaz de administrador: formulario de plan, trabajos, estados (todo con CSRF y roles).

## 2. Qué lo impide hoy
1. **No existen datos operativos posteriores al 20/10/2026.** `octubre.xlsx` llega al 20/10; la base SQL restaurada llega al 21/10 16:26:38 (día incompleto). El corte del plan v2 (20/10) ya es el último día completo. Por tanto **no hay «datos reales recientes» con los que probar un corte nuevo**; solo se puede probar la repetición idéntica (reutiliza), el rechazo de cortes inválidos y la exclusión del parcial del 21/10.
2. **Falta una fuente de movimientos de stock que la aplicación pueda leer.** La existencia al corte se obtiene del conteo informado + los movimientos del kardex (SQL Server). La nube no puede ni debe leer SQL Server (el respaldo no se sube). Compras y ventas por sí solas **no bastan** (el kardex incluye otros tipos de movimiento; deducir stock solo de ventas queda excluido por instrucción). Lo indispensable, por corte: **(A)** un paquete de existencias generado desde el kardex (`existencias.csv` + `manifest.json`, mismo formato y reglas que el del 20/10) **o (B)** un conteo físico nuevo en el formato del conteo recibido (fecha/hora del conteo ≥ cierre del corte). Sin A o B la aplicación debe **bloquear** la generación («no hay existencia al corte») y nunca mostrar el stock del 20/10 como actual.
3. **La conciliación contra SQL no se puede ejecutar desde la aplicación.** Opciones sin reducir en silencio: adjuntar el informe de conciliación (`informe.json`, generado por soporte contra SQL) y que la app verifique SHA y `coincide`; o permitir la carga **sin** informe marcándola explícitamente «no verificada contra SQL» en la vista previa y en la trazabilidad (reducción explícita, requiere aprobación de Rogelio).
4. **Las constantes del procedimiento actual** (`LAST_FULL_DAY`, `OCTOBER_NAME`/`OCTOBER_WINDOW`, `PARTIAL_DATE`, `AS_OF_LOCAL`) deben parametrizarse, y la importación de la existencia debe aceptar `as_of` del manifiesto.
5. **Tamaño del trabajo** (estimación revisada): núcleo parametrizado y versionado con deduplicación/conflictos/parcial y pruebas con datos reales (reproducción del corte 20/10) ≈ 4–5 h; API + trabajos del worker + almacenamiento GridFS ≈ 3–4 h; asistente de interfaz (vista previa: corte, cobertura, stock y procedencia, supuestos, pendientes) ≈ 3–4 h; pruebas de seguridad y de extremo a extremo, publicación, verificación y manuales ≈ 3–4 h. **Total ≈ 14–17 h (1,5–2 jornadas)**; no cabe en lo que queda del 22/10.

## 3. Alcance mínimo propuesto (para el siguiente bloque de trabajo, tras confirmar los datos)
1. **Núcleo operativo** (`pipeline/plan/operational.py`): recibe libro de ventas + corte elegido + mes objetivo; deriva la ventana de 28 días del corte; valida formato, fechas y cobertura (días con y sin registros, **sin tratar lo desconocido como cero**); deduplica por `registro_id` (idéntico → duplicado; mismo id con contenido distinto → conflicto que bloquea); separa los datos posteriores al corte como parciales; versiona (`plds-<hash>`) con trazabilidad (quién, cuándo, SHA, estado de verificación SQL) conservando `plds-1f4717744dc3` y los planes de noviembre v1/v2.
2. **Existencia al corte:** importar A o B con las reglas actuales; bloquear si falta o si su fecha es anterior al corte.
3. **API y trabajos:** subida multipart (GridFS) → trabajo → vista previa persistida → confirmación → `generate_plan` (reutiliza el motor sin cambios; promedio de 28 días y parámetros acordados).
4. **Interfaz de administrador** «Actualizar datos del plan»: elegir corte y mes, ver vista previa (corte, cobertura, stock y procedencia, supuestos, pendientes, estado de verificación SQL) y confirmar; los pendientes de la empresa (compras 11452/11455, 13 diferencias) se muestran sin cerrarse.
5. Las restricciones y los datos reservados de la evaluación académica **no se tocan** (flujo y colecciones separados).

## 4. Decisiones y datos que necesito de Rogelio
- **Fuente de existencias** para cada corte nuevo: ¿paquete desde el kardex (A, lo genera soporte con `sql21_prepare` generalizado) o conteo físico nuevo (B)? Es el dato indispensable: sin él no se puede actualizar el stock correctamente.
- **Política SQL:** ¿informe de conciliación obligatorio, u opcional con etiqueta explícita «no verificada contra SQL»?
- **Fecha de los siguientes datos reales:** un libro de ventas posterior al 20/10 y su paquete/conteo de existencias (o la fecha en que existirán) para la prueba con datos reales.

## 5. Hecho hoy dentro de este encargo
TRUSTED_PROXIES medido y configurado (`docs/T22_TRUSTED_PROXIES_Y_CREDENCIAL.md`); identificación de la credencial de Atlas en curso (primera instrucción a Rogelio). Sin cambios en planes, datos ni cálculos.
