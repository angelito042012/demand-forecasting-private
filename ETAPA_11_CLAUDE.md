# T11A: preparar publicación, integrar T12 y comprobar recuperación local

Lee ESTADO/TRASPASO, `docs/REVISION_CODEX_11.md`, `docs/T12_PROTOCOLO.md` y contratos T08/T10. T10R aceptado; resultados científicos T12/3f40176 validados por Codex. R11 de checkpoints pendiente. Fecha final **23/10/2026 Lima**. Claude es ejecutor; no rehacer datos, experimentos, T10 o T12.

## 1. Alcance y punto de parada

Preparar y verificar todo lo necesario para un despliegue concreto: R11, paquete final integrado localmente, contenedores, base de publicación, almacenamiento, copia/restauración y plan de infraestructura/costo/permisos. **No crear todavía recursos externos, consumir crédito/generar cargos, ampliar Atlas a pago ni transferir ventas a la nube.** La propuesta final deberá poder aprobarse con recursos, región, costo máximo y pasos concretos; esa autorización será el último paso antes de aprovisionar/publicar, no un motivo para dejar la preparación pendiente.

Azure for Students ya muestraUS$100 hasta17/10/2027; Atlas Free demand-forecasting-dev en São Paulo creado. No hay presupuesto de bolsillo ni conversión a pago por uso autorizados. No pedir volver a crear cuentas. Contraseña mostrada anteriormente en captura: rotación no confirmada, el usuario la gestiona por canal privado; no pedirla ni imprimirla. No leer archivos privados de credenciales para incluirlos en reportes. Si falta una sesión de Azure/Atlas, documentar el paso mínimo de autenticación y seguir trabajo local independiente.

Un integrador, hasta tres trabajadores con ámbitos: empaquetado/infra, datos/restauración, UI/API final. Primero contrato de publicación y límites; integrador controla dependencias/config/contratos. R11 es pequeño y va al inicio, no repetir toda T12. Guardar checkpoints y traspaso por unidad.

## 2. R11: cierre fiel del estado final, sin repetir el experimento

- Registrar inicio/fin/error de auditoría y reporte, estado completo de las siete fases, artefactos/evidencias e idempotencia. Falla una fase ⇒ completa=false, sin declarar reporte válido.
- Regresiones sintéticas: prepare/evaluate/audit/report completan status; fallos audit/report y recuperación; al reanudar no se invocan prepare/evaluate ni load_final_test_sales ni entrenamiento. Pruebas que fallen con la versión anterior.
- Reconciliar el paquete real existente ejecutando solo auditoría/reporte desde artefactos guardados. Registrar **corrección técnica posterior** con commit/fecha real, conservar procedencia de a39d3e9/86325a7 y los hashes originales de predicciones, modelo, inicialización, reales, series y métricas. No inventar timestamps para las fases ausentes. No editar el booleano a mano ni re-seleccionar/recalcular el experimento.

## 3. Contrato e integración local de T12

- Definir `docs/T11_CONTRATO.md` y manifiesto de publicación: qué corridas/resultados/datos sirven la web y qué evidencias se archivan de forma recuperable, esquemas, roles, procedencia y versiones. La evaluación final debe distinguirse de histórica T07 y de generada de desarrollo, sin sustituirlas silenciosamente.
- Integrar **predicciones fijas origen31/07→01–21/08 y comparación final** leyendo los artefactos ya validados, sin ejecutar modelos/experimentos dentro de HTTP. Mantener resultados adversos/control cero, universo común/cohortes y etiquetas de inventario simulado; WAPE no es exactitud. Selección operativa promedio_28, RF comparador. Categorías=sumSKU con advertencia de unidades base heterogéneas.
- No convertir las revisiones de la simulación secuencial en predicciones fijas ni mezclar métricas T07/T12. Mostrar fechas/cobertura/antigüedad y límites de un único bloque. Los datos siguen históricos, no afirmar que pronostican octubre.
- Publicación local de un kind/esquema explícito del paquete final, idempotente y con las garantías de T10R; capacidad calculada antes de insertar. `demand_forecasting_v2` y v1 se conservan. Trabajar en **base nueva** para el conjunto publicable, con nombre documentado, y bases temporales para pruebas. No activar puntero de la base original.
- Recomendaciones: las históricas siguen disponibles. Una evaluación final no crea automáticamente un pedido operativo. Si el paquete final no trae una recomendación validada para ese origen/snapshot, mostrar el motivo/no disponible y enlace a la demostración histórica; no fabricar stock ni usar un snapshot de otro día. No añadir una política nueva tras ver el test.
- La barrera general de entrenamiento y de carga web de agosto sigue cerrada. Lecturas de resultados finales admiten sus fechas solo para esa corrida/tipo con autorización de usuario; no ampliar globalmente `LAST_ALLOWED_DATE` para todos los endpoints. Pruebas de separación de corridas/fechas/roles y de API caída sin mocks.

## 4. Capacidad, archivo y base de publicación

Datos de dirección solo lectura:BD459,39MB; forecasts267,06MB, recommendations66,43MB, sales81,79MB antes de índices. Revisión privada `artifacts/private/codex_review11_capacity.json`. Hay seis corridas generadas de pruebas no imprescindibles para la publicación; las dos históricas y toda evidencia deben conservarse recuperables. No hacer limpieza destructiva de v1/v2 ni quitar resultados desfavorables.

- Crear manifiesto reproducible para la base nueva: ventas86877/créditos560, fuentes/importaciones necesarias, corridas históricas pertinentes (con superseded/quality_issue), paquete final y resúmenes/backtests. **No copiar sesiones, contraseñas demo, usuarios de prueba, jobs viejos, login_budget ni rutas privadas**. Usuarios de publicación se crean por procedimiento seguro separado.
- Modelos, NPZ de simulación (~128MB), archivos mínimos de evaluación, logs/Excel privados van a archivo/almacenamiento durable privado separado, con hashes y política de acceso; no insertar binarios de modelos/ledger completo en Mongo ni servirlos públicamente.
- Medir después de restaurar/copiar datos+índices de la nueva base, no usar tamaño comprimido del dump como tamaño Atlas. Contrastar cuota real del clúster Free y restricciones/versión, índices y agregaciones; objetivo de dirección: margen amplio, preferiblemente ≤60% de la cuota al publicar y proyección explícita de nuevas corridas.
- Si no cabe, proponer archivo selectivo recuperable o despliegue Mongo alternativo con costo/operación evaluados. No contratar nivel mayor ni cambiar de motor como arreglo silencioso. Conservar desarrollo completo local.

## 5. Copia y restauración reales, antes de nube

- Exportación consistente con escritores detenidos/controlados, fuentes/artefactos/manifiesto e índices; documentar alcance y exclusiones (sesiones activas/secretos). Respaldo privado, sin copiar claves de nube a Git o logs.
- Restaurar en una base temporal **diferente**, comprobar conteos, hashes/identidades, índices, estados de corridas, referencias de hijos y consultas API reales sobre histórica/final, con usuarios nuevos de prueba separados. No sobrescribir v1/v2 ni base de publicación existente.
- Medir tamaño, duración de copia/restauración y retención; evidencia de una recuperación exitosa, no solo que se creó un archivo. Modelos/artefactos restaurados verifican hashes. Archivar evidencia de todas las corridas omitidas de publicación. No repetir entrenamiento/evaluación para restaurar.

## 6. Empaquetado y configuración de producción

- Crear imagen(es) Docker reproducibles con Python3.12 y lockfiles probados; Angular compilado de producción, API y rol worker/scheduler reutilizable. Dockerfile(s), compose local de ensayo y `.dockerignore` excluyen .env, tokens, Git, .venv/node_modules, Excel y artefactos comerciales; los datos se suministran privadamente a volúmenes/almacenamiento, no se incrustan en imágenes públicas.
- Preferir web/API **mismo origen HTTPS** para conservar cookies SameSite=Strict y CSRF, con rutas Angular recargables. No usar `ng serve` en producción; API desconocida devuelve error API, no index.html. Construcción limpia y smoke local del contenedor con la base restaurada.
- APP_ENV=production, Secure cookies, secretos obligatorios generados por canal privado, roles sin registro público, CSRF/Origin correctos, proxy/header de cliente solo desde salto de confianza documentado. Comprobar que variar X-Forwarded-For no evita el límite, con la cadena de proxy elegida. No exponer Mongo/worker ni endpoints administrativos sin permisos.
- Subidas/modelos/artefactos y trabajos sobreviven reinicios/reemplazos de contenedores; disco efímero no es almacén durable. API/worker comparten el mismo almacén privado real y rutas compatibles. Evitar que CLI/scheduler carguen otra URI/base por omitir variables o por depender de .env local. Timer deshabilitado por defecto; si se habilita después, fuentes/config estables e identidad de tick inmutable antes de admitir cambios dinámicos.
- Publicación final/consumo de cuota protege último válido, es idempotente y no carga todo el historial a ciegas. Registros sin secretos ni filas comerciales. Límites de body/archivo y errores de producción saneados.

## 7. Propuesta de nube concreta, sin aprovisionar aún

Crear `docs/T11_PLAN_DESPLIEGUE.md`: diagrama, recursos exactos, región, cuotas/permisos a verificar, red, almacenamiento, modo de worker/timer, rollback/desmontaje y accesos mínimos faltantes. Comparar brevemente opciones que conserven Azure/Python/Angular/Mongo (p.ej. Container Apps Consumption +jobs frente a alojamiento con worker continuo); escoger por viabilidad real/costo, no por añadir servicios.

- Consultar documentación/precios oficiales vigentes y registrar fecha/URL. Azure CLI no se encontró en el PATH durante la revisión; preparar herramienta aislada si necesaria, sin cambiar el entorno Python bloqueado ni imprimir tokens. Una sesión autenticada permite inspección **solo lectura** de suscripción/crédito/cuotas; no iniciar recursos para probar acceso.
- Cotizar costo total hasta23/10 y mensual si se deja encendido: cómputo API, worker/timer, almacenamiento durable y copias, registro de imágenes, logs/retención, IP/egreso/red y Atlas. Describir cargos que no cubre el free grant. Presupuesto/alertas no son un corte automático de gasto; mantener protección de la suscripción estudiantes, sin pago por uso.
- Para worker duradero que requiere observar Mongo, explicar cómo se activa y procesa jobs si API escala a cero. Si se usa job programado y worker --once, documentar demora máxima, reintentos y lease; no llamarlo worker permanente ni dejar una cola sin consumidor. Timer diario06:00 Lima=11:00UTC, sin acceso al test/experimentos.
- Atlas: usuario de aplicación mínimo por base, credencial nueva/rotada y conexión verificada posteriormente por canal privado; rangos/IP de egreso de Azure conocidos y plan para sus cambios. No adoptar una apertura global permanente como solución por defecto. No introducir un NAT/servicio adicional costoso sin incluirlo en propuesta.
- HTTPS con dominio/certificado de plataforma o mecanismo concreto disponible; sin comprar dominio. Infraestructura declarativa/scripts parametrizados preparables/revisables y comprobación estática local cuando sea posible, sin desplegar ni transferir datos.

Referencias iniciales (volver a verificar en la cuenta/oferta concreta):
- Atlas Free: https://www.mongodb.com/docs/atlas/reference/free-shared-limitations/ y https://www.mongodb.com/docs/atlas/manage-clusters/ (cuota cuenta datos+índices).
- Container Apps billing: https://learn.microsoft.com/en-us/azure/container-apps/billing y https://azure.microsoft.com/en-us/pricing/details/container-apps/ . El free grant de cómputo no vuelve gratuitos almacenamiento/red/otros recursos.
- Almacenamiento: https://learn.microsoft.com/azure/container-apps/storage-mounts (distinguir almacenamiento efímero de Azure Files durable).

## 8. Cierre y evidencia

Pruebas dirigidas R11, integración final y regresiones afectadas; build/frontend solo por los cambios reales de UI; smoke del contenedor, recuperación y acceso/CSRF/proxy. No repetir T06/T07 ni prepare/evaluate real. Demo local de final/histórica, selección consistente y rutas después de reinicio; logs/capturas sin secretos en `artifacts/private/t11a/`.

Entregar `docs/T11A_REPORTE.md`, contrato, plan de despliegue/costos, inventario de base nueva/archivo y acta de restauración. Actualizar ESTADO/TRASPASO/BACKLOG/HISTORIAL con R11, T12 científicamente validada/cierre técnico, pruebas y pendientes reales. Commit local con exclusiones revisadas. **Detener para revisión antes de crear recursos/transmitir datos/consumir crédito**; la siguiente autorización se pedirá sobre este plan concreto. No declarar despliegue por tener contenedores locales.
