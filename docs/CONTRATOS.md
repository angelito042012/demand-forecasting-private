# Contratos propuestos y aceptación

> **Actualización T08 (17/10/2026):** las secciones «API propuesta» y «Persistencia» de este documento quedan sustituidas por `docs/T08_CONTRATO.md` (rutas, sesión por cookie HttpOnly, errores, paginación, colecciones de corridas y publicación versionada). La clave de venta vigente es la del importador v2 (`docs/ESTRATEGIA_CLAVES.md`); las claves históricas de esta tabla no deben seguirse. Se conservan aquí las pruebas de aceptación A01–A14.

Estas decisiones son una base para implementación; el formato real de ventas ya fue verificado y la semántica debe validarse con el negocio. No constituyen una API ya implementada.

## Datos

| Entidad | Campos mínimos | Clave y validación |
|---|---|---|
| Venta | fecha, pedido_id, linea_id, sku, categoria, cantidad, precio_unitario, almacen | Fuente + pedido + línea; fecha local Lima, cantidad/unidad explícita |
| Producto | sku, descripcion, categoria, unidad, proveedor_id, multiplo, minimo | SKU único; unidad estable; múltiplo positivo |
| Stock | fecha, sku, almacen, disponible | Fecha + SKU + almacén; reconciliar con movimientos |
| Movimiento | id, fecha, sku, almacen, tipo, cantidad | Entrada/salida/ajuste/devolución explícitos |
| Pedido pendiente | id, sku, cantidad, fecha_esperada, estado | Evitar contar recepciones dos veces |
| Política | proveedor/SKU, lead_time_dias, revision_dias, seguridad, umbral_exceso, costo, tasa_holding | Valor y fuente; desconocido no equivale a cero |

Si el export no tiene linea_id, definir una clave estable con procedencia y posición original; no deduplicar dos ventas idénticas legítimas por sus valores. Tratar anulaciones y devoluciones por reglas explícitas. Separar datos crudos de depurados. Una carga repetida no duplica transacciones. Conciliar montos con tolerancia monetaria documentada y registrar rechazos por fila.

Fechas de negocio locales; timestamps técnicos UTC. Importes en PEN, costos con precisión decimal. No conservar nombres, teléfonos o documentos de clientes porque no son necesarios para pronosticar. Archivos reales en data/private/, excluidos del versionado.

## Correspondencia con los Excel actuales

Encabezados Hoja1!A2:AE2. fecha = FECHA; pedido_id = ID_PEDIDO; sku = ID_ARTICULO; categoria = GRUPO; cantidad = CANTIDAD_UM_BASE después de comprobar equivalencia; precio_unitario original = PRECIO por unidad de venta; importe = TOTAL_LINEA; almacen = ID_ALMACEN. No mezclar PRECIO de empaque con cantidad base sin conversión. Conservar serie, tipo documental, fila de origen y hash. No hay linea_id explícito; definirlo con procedencia y posición, y manejar importaciones solapadas sin eliminar líneas legítimas iguales. ID_PEDIDO=0 no es clave válida para las 560 líneas negativas. TIPO_DOC=7 confirmado como nota de crédito por el usuario; separar de ventas brutas y no inferir devolución física. No hay columnas de saldos de stock.

## API propuesta

| Operación | Método y ruta | Resultado y permiso |
|---|---|---|
| Salud | GET /api/v1/health | Sin datos sensibles |
| Acceso | POST /api/v1/auth/login | Sesión expirable; no registro público |
| Carga | POST /api/v1/imports | ID de carga y estado; administrador |
| Incidencias | GET /api/v1/imports/{id} | Conteos y errores; autorizado |
| Ventas | GET /api/v1/sales/summary | Agregados y filtros |
| Corridas | GET /api/v1/runs | Estado, corte, antigüedad |
| Ejecución | POST /api/v1/runs | Encolar o ejecutar fuera de petición; administrador; idempotente |
| Pronóstico | GET /api/v1/forecasts | run_id, entidad, fecha objetivo, cantidad, modelo |
| Reposición | GET /api/v1/recommendations | Stock, tránsito, horizonte, pedido, motivo |
| Comparación | GET /api/v1/backtests/{id} | Política base y propuesta, métricas y supuestos |

Paginación y límites en consultas; 401 sin sesión, 403 sin rol, 422 datos inválidos. Limitar tamaño de importación y validar contenido, no solo extensión. CORS restringido al frontend. Contraseñas con hash apropiado; sesión protegida; rate limit en login; secreto fuera del código. Probar permisos en servidor, no solo ocultando botones. Elegir cookies seguras con protección CSRF o tokens con manejo explícito de expiración y almacenamiento; documentar la decisión.

## Persistencia

Colecciones sugeridas: users, products, sales, stock_snapshots, inventory_movements, policies, imports, model_runs, forecasts, recommendations, backtests, audit_events. Incluir schema_version y validación. Índices únicos para clave de venta, producto, y pronóstico por corrida/entidad/fecha. Índices de consulta por fechas y SKU. La corrida solo cambia a completed cuando todos sus resultados son coherentes; lectores ignoran resultados incompletos. No depender de transacciones multidocumento sin comprobar soporte real.

## Pruebas que definen aceptación

| Código | Comprobación | Evidencia necesaria |
|---|---|---|
| A01 | Importar archivo correcto y repetirlo sin duplicados | Totales originales, aceptados y rechazados |
| A02 | Fecha inválida, resumen y devolución tienen tratamiento explícito | Casos y reporte de rechazo |
| A03 | Cambiar datos posteriores al corte no cambia features anteriores | Prueba de fuga temporal |
| A04 | Baselines y ML evaluados en las mismas ventanas | Métricas, cobertura y hashes |
| A05 | Serie cero/constante no genera NaN engañosos ni infinito | Casos de métricas |
| A06 | Recepción, demanda y pedidos conservan balance de stock | Casos pequeños calculados manualmente |
| A07 | Lead time, tránsito y empaque alteran correctamente el pedido | Pruebas de reglas |
| A08 | Ambas políticas reciben exactamente condiciones equivalentes | Configuración guardada |
| A09 | Roles bloquean lecturas/escrituras no autorizadas | Pruebas de API |
| A10 | Carga → resultados → recomendación funciona en navegador | Evidencia E2E |
| A11 | Reintento batch no duplica y un fallo conserva último válido | Prueba de reintento |
| A12 | Copia restaurada permite consultar una corrida | Acta técnica de restauración |
| A13 | Despliegue HTTPS y consulta por 1–5 usuarios | Prueba de humo y latencia medida |
| A14 | Usuario interpreta recomendación y reconoce incertidumbre | Registro de aceptación real |

Meta de rendimiento propuesta: consultas paginadas de resultados precalculados con p95 menor de dos segundos en una prueba documentada de cinco usuarios, excluyendo y reportando aparte cold start. Validarla con la infraestructura elegida. Cero defectos críticos abiertos para liberar; metas ML se informan aunque no se alcancen.

## Reglas acordadas y procedencia

DECISIONES_DATOS.md define días excluidos, catálogo temporal e inventario sintético. Toda salida operativa del escenario debe incluir provenance=SYNTHETIC_NOT_REAL_INVENTORY y scenario_id. Mostrar la condición simulada en pantallas, exportaciones e informe. Nunca mezclar stock simulado con ventas originales sin identificar ambos orígenes. Verificar balance de inventario y comparación bajo idénticas condiciones.
