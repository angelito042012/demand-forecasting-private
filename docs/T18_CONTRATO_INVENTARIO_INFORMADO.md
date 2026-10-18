# T18 — Contrato del snapshot de inventario informado (conteo fechado)

Fecha: 18/10/2026 (America/Lima). Encargo: `ETAPA_18_CLAUDE.md`. Fuente: `docs/REVISION_CONTEO_50_20261018.md`. Alcance **local** y de ensayo aislado: no se toca v1/v2/`demand_forecasting_pub`, ni la base de la demo activa, ni Azure/Atlas; no se entrena nada.

## 1. Qué es (y qué no es)

- **Es** un *inventario físico reportado por la empresa* para el **18/10/2026 17:00 (America/Lima, UTC−05:00)**, almacén **1** («Almacén Principal»), 50 productos, con fuente y huella. Naturaleza: `CONTEO_FISICO_REPORTADO_POR_USUARIO`; **no hay verificación independiente** (no se afirma auditoría presencial).
- **No es** inventario simulado: la etiqueta «Inventario simulado con supuestos…» **no** se aplica a este snapshot ni se quita de los escenarios simulados de T07/T12.
- **No sustituye** retroactivamente los saldos calculados de marzo–septiembre ni los `inventory_snapshot` de T07/T12; **no** se compara el saldo calculado al 30/09 con este conteo como si fueran la misma fecha; **no** se inicializa el backtest de agosto con él; **no** se convierte en estado «actual» indefinido: la fecha del conteo no cambia al consultarlo.
- **Desconocidos declarados** (nunca cero): ventas del 01 al 18/10 (el histórico de ventas disponible termina el 30/09), pedidos de compra por recibir, movimientos de octubre. Por eso **no hay recomendación de reposición actualizada al 18/10**.
- Reservadas y no vendibles = 0 son **declaraciones de esta fuente** (50 filas). Presentaciones (caja de 12, pack de 2) se conservan como unidad declarada del código: **no se multiplica** ninguna cantidad.

## 2. Entradas y validaciones del importador

Entradas (solo lectura): `conteo_reportado.csv` y `Solicitud_conteo_50_productos.xlsx` y `review.json` de `artifacts/private/conteo_recibido_20261018_v2/`, y el catálogo del grupo `artifacts/private/datos_preparados_v1/02_grupo/productos.csv` (códigos esperados, nombre, categoría, unidad).

Se rechaza (sin escribir nada) si: el SHA-256 del Excel no coincide con `sha256_origen` de **todas** las filas ni con `review.json`; el conjunto de códigos no es **exactamente** el del catálogo (faltantes, sobrantes o repetidos); algún `producto_id` no es texto de dígitos conservado tal cual (se preservan ceros a la izquierda); nombre o unidad (`UND`) no coinciden con el catálogo; `cantidad_libre_reportada` vacía, negativa, fraccionaria o no numérica; reservada/no vendible negativas o no enteras (**vacío = «no informado» = `null`, distinto de 0**); si todas las cantidades están informadas, `total = libre + reservada + no_vendible`; `almacen_id_confirmado` no es verdadero (`True`/`1`; en la fuente real es `True`) o `almacen_id_candidato` ≠ `1` o `corte_sin_ventas_confirmado` ≠ verdadero o `estado_uso` ≠ `APTO_COMO_SNAPSHOT_FECHADO` o `naturaleza` ≠ `CONTEO_FISICO_REPORTADO_POR_USUARIO` o `verificacion_independiente` ≠ falso; `fecha_hora_reportada` inconsistente entre filas, sin zona, o con una zona distinta de `America/Lima` (UTC−05:00); falta de la descripción de presentación.
**R18 — correspondencia derivado ↔ Excel (antes de cualquier escritura).** El CSV es un derivado: el importador abre el libro `.xlsx` revisado (solo lectura) y exige, con el código `DERIVADO_NO_COINCIDE`, que **cada registro** coincida con las celdas del documento: código (como texto) y fila (`fila_origen`), producto, unidad, presentación, cantidad disponible/reservada/no vendible (vacío ≡ celda vacía, nunca 0; texto, fórmula o fracción en una celda de cantidad no se aceptan), total derivado de esas celdas (sin total si falta una componente), observaciones, y que el conjunto de filas del CSV sea **exactamente** el de las filas de datos del documento; además la fecha y la hora (C3/G3), el almacén (C4) y los metadatos de `review.json` (responsable, alcance, movimientos, fecha/hora) deben coincidir con la cabecera del documento. Las **confirmaciones humanas** (almacén 1, sin ventas durante el conteo) no están en el Excel: se verifican aparte (CSV y `review.json.user_confirmation`). Un libro ilegible o con hashes recalculados pero valores distintos se rechaza; una fuente modificada legítimamente se acepta solo como otra fuente (otro SHA ⇒ otra versión). El snapshot guarda `source.verified_against_excel`, la disposición de plantilla y las filas verificadas.

Tampoco se admite escribir en `demand_forecasting_dev`, `demand_forecasting_v2` ni `demand_forecasting_pub`.

## 3. Persistencia (separada de T07/T12 y de saldos calculados)

Colecciones nuevas, sin tocar `recommendations`, `runs` ni `inventory_snapshot`:

- `inventory_reported_snapshots` — `snapshot_id` (`invrep-<AAAAMMDD>T<HHMM>-a<almacén>-<sha12 del Excel>`), `version`, `status` (`current` | `superseded` | `staging`), `supersedes`, `as_of_utc`, `as_of_local` (ISO con −05:00), `timezone`, `warehouse {id, name}`, `nature`, `independent_verification` (false), `source {file, sheet, sha256, csv_sha256}`, `confirmations`, `coverage {expected, items, group_file, group_sha256}`, `counts {items, with_stock, no_stock}`, `declared_unknowns [{code, detail}]`, `context {sales_history_end}`, `imported_at`, `schema_version`.
- `inventory_reported_items` — `snapshot_id`, `producto_id` (texto), `producto`, `categoria`, `unidad_reporte`, `unidad_descripcion`, `libre`, `reservada` (nullable), `no_vendible` (nullable), `fisica_total` (nullable), `source_row`.
- Índices únicos: `snapshot_id`; (`snapshot_id`, `producto_id`); (`warehouse.id`, `as_of_utc`, `version`).

**Idempotencia y versiones:** la misma fuente (mismo SHA del Excel y mismo almacén y fecha) devuelve el **mismo** snapshot (`action: "unchanged"`, sin escrituras). Una fuente distinta para el mismo almacén y fecha crea una **nueva versión** (`version+1`); la anterior queda `superseded` y **se conserva**. Se escribe primero en `staging` (cabecera y filas) y solo al terminar pasa a `current`; un intento interrumpido se limpia por su propio `snapshot_id` y se rehace. Nada se borra de otros snapshots.

**CLI privilegiada** (como `publish_run`; sin endpoint de escritura HTTP en esta etapa: «escritura solo administrador» se cumple al no existir escritura por la web):
`python -m pipeline.inventory.reported_count --count-dir <carpeta v2> --group <productos.csv> --db <base> [--sales-history-end 2026-09-30] [--dry-run]` → imprime un JSON sin secretos (`action`, `snapshot_id`, `version`, `items`, `con_existencia`, `sin_existencia`).

## 4. API de lectura (autenticada; lector y administrador)

Todas con `strict_params`, sin operadores Mongo, rol cualquiera (`require_user`), sin recalcular nada.

`GET /api/v1/inventory/reported` — parámetros: `snapshot_id` (opcional; por defecto el último `current`), `q` (texto: código o parte del nombre; ≤100 caracteres, seguro), `view` = `all` (defecto) | `with_stock` | `no_stock`, `sort` = `producto_id` (defecto) | `-producto_id` | `producto` | `-producto` | `libre` | `-libre`, `page`, `page_size` (≤200).

```json
{
  "snapshot": {"snapshot_id": "...", "version": 1, "status": "current", "as_of_local": "2026-10-18T17:00:00-05:00", "as_of_utc": "2026-10-18T22:00:00Z",
    "timezone": "America/Lima", "warehouse": {"id": "1", "name": "Almacen Principal"}, "nature": "CONTEO_FISICO_REPORTADO_POR_USUARIO",
    "independent_verification": false, "source": {"file": "Solicitud_conteo_50_productos.xlsx", "sha256_short": "608d15a74a58"},
    "counts": {"items": 50, "with_stock": 48, "no_stock": 2}, "declared_unknowns": [{"code": "BRECHA_OCTUBRE", "detail": "..."}, {"code": "PEDIDOS_PENDIENTES", "detail": "..."}],
    "context": {"sales_history_end": "2026-09-30"}, "imported_at": "..."},
  "items": [{"producto_id": "3230005", "producto": "LANOSTERIN BIFASICO 250 ML", "categoria": "...", "unidad_reporte": "UND",
    "unidad_descripcion": "Un frasco de 250 ML", "libre": 96, "reservada": 0, "no_vendible": 0, "fisica_total": 96}],
  "page": 1, "page_size": 50, "total": 50, "has_more": false,
  "view_counts": {"all": 50, "with_stock": 48, "no_stock": 2},
  "provenance": "INVENTARIO_INFORMADO_POR_LA_EMPRESA",
  "disclaimer": "Inventario informado por la empresa (conteo del 18/10/2026 17:00, hora de Lima); no es inventario simulado ni se ha verificado de forma independiente."
}
```
Notas de implementación (verificadas en pruebas): el objeto `snapshot` incluye además `confirmations` (almacén confirmado, corte sin ventas, evidencia) para el detalle plegado; `view_counts` respeta el filtro `q` mientras `snapshot.counts` es el total del snapshot; el catálogo esperado son las filas con `seleccionado == True` de `productos.csv` (50); `q` es texto literal (prefijo de código o parte del nombre, sin distinguir mayúsculas); `/snapshots` acepta `page`/`page_size`, lista `current` y `superseded` (nunca `staging`); reimportar una versión ya sustituida se rechaza (`VERSION_SUSTITUIDA`).

Sin snapshot: `200` con `snapshot: null`, `items: []`, `total: 0` y `unavailable_reason: "SIN_INVENTARIO_INFORMADO"`. `snapshot_id` inexistente: `404 NO_ENCONTRADO`. `libre`=0 es «cero declarado»; un campo `null` es «no informado» (nunca se convierte en 0). `view_counts` y `total` los calcula el servidor sobre el snapshot completo/filtrado (no sobre la página).

`GET /api/v1/inventory/reported/snapshots` — lista de versiones (`snapshot_id`, `version`, `status`, `as_of_local`, `warehouse`, `source.sha256_short`, `imported_at`), más recientes primero.

## 5. Pantalla «Inventario informado» (UX01R)

Ruta `/inventario`; menú: **Inventario informado** entre las tareas principales; tarjeta «Consultar el inventario informado» en Inicio. Lenguaje sencillo, `PageHeader`, estados cargando/error (con Reintentar)/vacío («Todavía no se cargó el conteo»)/permiso.
- Encabezado: «Inventario informado por la empresa» y propósito («Existencias que la empresa informó para el almacén principal el 18/10/2026 a las 17:00»). Franja: **Conteo del 18/10/2026, 17:00 (hora de Lima) · Almacén Principal (almacén 1) · informado por la empresa; no verificado de forma independiente**.
- Aviso único y claro: **este inventario es del 18/10; el histórico de ventas disponible termina el 30/09** (valor de `context.sales_history_end`, fecha en español); faltan las ventas del 01 al 18/10, **no son cero**; por eso no hay recomendación de reposición actualizada, y las recomendaciones históricas siguen en «Reposición simulada» con sus avisos. Pedidos por recibir: **no informados**.
- Tabla (los 50, ceros incluidos): código (texto), producto, presentación (`unidad_descripcion`), disponible, reservado, no vendible; un valor `null` se muestra «No informado»; **no se muestra un total general** (mezcla presentaciones); sí «50 productos · 48 con existencia · 2 sin existencia» del servidor. Vistas: Todos / Con existencia / Sin existencia; búsqueda por código o nombre; orden; paginación del servidor.
- Detalles plegados: fuente (archivo, SHA corto), versión, confirmaciones, desconocidos declarados, nota de presentaciones (caja de 12, pack de 2: «la cantidad está en la presentación indicada; no se multiplicó»).
- No se usa la etiqueta «simulado» ni se mezcla con recomendaciones. Lectores consultan; no hay controles de escritura.

## 6. Límites

El snapshot no certifica inventarios pasados ni una mejora real; toda fecha posterior requiere movimientos u otro conteo. No se importan las 14 fuentes ni se usan saldos retrospectivos como observaciones. Aceptación humana pendiente.
