# Análisis y plan de ejecución

## Conclusión

**Segunda revisión de datos:** marzo–julio fueron actualizados y agosto no cambió. Los seis meses tienen ahora 31 columnas homogéneas de detalle por artículo: 87 437 filas en total. Se puede avanzar con el pronóstico tras limpieza y conciliación. El usuario autorizó una evaluación operativa por escenarios sintéticos; se generó una referencia reproducible. Los datos reales de inventario siguen desconocidos, por lo que no se podrá afirmar impacto real. Leer AUDITORIA_DATOS.md; queda retirado el bloqueo anterior por falta de detalle histórico.

El proyecto consiste en una plataforma web para convertir las ventas históricas de una MYPE de productos de cuidado personal en pronósticos, recomendaciones de reposición y evidencia comparativa sobre inventarios. Para llegar al 23/10/2026 hay que cerrar primero los datos y las reglas de reposición, construir una sola cadena funcional y reservar los últimos dos días para validación y entrega. Es un plazo de siete días calendario desde el 16, con ocho fechas de trabajo si se incluyen ambos extremos; no permite prometer una implantación empresarial madura ni mejoras estadísticas antes de medirlas.

La meta es completar el alcance académico y operativo declarado: importar, depurar, pronosticar, simular, recomendar, consultar y documentar. Un resultado que no confirme la hipótesis sigue siendo científicamente válido; no equivale a cumplir el umbral predictivo propuesto. La aceptación del software, del experimento y del informe debe registrarse por separado.

## Qué problema resuelve

Según las secciones Situación problemática y Objetivos del documento, la reposición se decide principalmente por experiencia, observación del stock y ventas recientes. Falta un procedimiento cuantitativo que anticipe necesidades y permita medir la calidad de esas decisiones. El usuario principal es el responsable de inventario; el propietario supervisa y autoriza compras. El sistema presenta recomendaciones y su fundamento; la compra sigue siendo una decisión humana.

La cadena causal que se investigará es: registros dispersos o insuficientemente aprovechados → decisiones empíricas → posible desajuste entre inventario y demanda → posibles quiebres, exceso y menor rotación. La ausencia de machine learning no demuestra por sí misma una mala gestión. El documento reconoce que la magnitud de los problemas debe corroborarse, aunque su matriz de consistencia luego los afirma como hechos. Corregir esa inconsistencia.

El informe declara para agosto 15 078 filas originales, 755 líneas válidas, 516 SKUs, 25 categorías y S/ 20 328,10; ocho categorías superarían el 80% del valor vendido. Estos son datos reportados por el documento, no recalculados aquí en la primera lectura. La auditoría posterior del archivo recibido arroja otro universo; ver AUDITORIA_DATOS.md. La exclusión de una fila residual que duplicaba el total debe convertirse en una regla de validación trazable, sin borrar automáticamente cualquier fila parecida. El Pareto describe concentración de ingresos, no prueba quiebres ni precisión predictiva.

## Qué está decidido y qué no

| Elemento | Estado en el documento | Implicación |
|---|---|---|
| Negocio | MYPE retail de cuidado personal en Lima | Una empresa y pocos usuarios; evitar multitenencia |
| Datos | Seis meses consecutivos; agosto 2026 es un mes límite | Marzo–agosto confirmado y formatos homogéneos verificados |
| Objetivo predictivo | Demanda por categoría; otras secciones incluyen producto | Cerrar granularidad antes de entrenar |
| Evaluación | Cinco meses de entrenamiento y último mes de prueba como referencia | Ajustar solo con justificación previa al test |
| Modelos | Ensambles; Random Forest, XGBoost/LightGBM como candidatos | Ningún algoritmo ganador está demostrado |
| Ejecución | Batch semanal | Consulta de resultados persistidos, sin entrenar al abrir una pantalla |
| Criterios ML | MAPE menor de 15% y R² mayor de 0,85 | Son metas declaradas, no resultados garantizados |
| Evaluación operativa | Backtesting frente a política actual | Exige stock, movimientos, tiempos y reglas reales |
| Construcción existente | Usuario confirma inicio desde cero | No afirmar que las tecnologías ya estén implementadas |

## Tecnologías y función

| Componente | Seleccionado en la fuente | Decisión de ejecución propuesta |
|---|---|---|
| Lenguaje | Python 3.x | Python 3.12 para fijar una base reproducible |
| Datos | pandas, NumPy | Importación CSV/XLSX, validación y series diarias |
| Excel | Lectura con pandas | Añadir openpyxl como dependencia de lectura |
| Análisis | Matplotlib, Seaborn | Figuras y evidencia reproducible |
| ML | scikit-learn, XGBoost/LightGBM | Baselines + Random Forest + un boosting; no probar todo sin límite |
| Experimentación | Jupyter/Colab | Opcional; el pipeline final debe ejecutarse fuera del notebook |
| API | FastAPI | API versionada, validación y permisos por rol |
| Acceso a BD | Motor/PyMongo | Elegir PyMongo; Motor está deprecado desde mayo de 2026 |
| Interfaz | Angular | Angular 21 como propuesta compatible con Node 24 instalado; fijar versiones |
| Persistencia | MongoDB Atlas M0 | Colecciones validadas, índices e historial de corridas |
| Aplicación | Azure App Service F1/B1 | Verificar plan Linux, recursos y costo real antes de elegir |
| Batch | Azure Functions timer | Cron en UTC, idempotencia y tiempo máximo medido |
| Versionado | Git/GitHub | Git local primero; repositorio remoto cuando se facilite |
| Calidad | Fuente menciona Selenium para unitarias | pytest para Python; pruebas Angular; navegador para integración/E2E |

PyMongo sustituye la alternativa Motor por mantenimiento, sin cambiar la base NoSQL. [Documentación oficial de Motor](https://motor.readthedocs.io/en/stable/).

Node 24.19.0 instalado está dentro del rango publicado para Angular 21. La selección exacta se fijará en el archivo de dependencias y lockfile al crear o adoptar el frontend. [Compatibilidad oficial Angular](https://angular.dev/reference/versions).

No asumir que Atlas M0 incluye snapshots administrados. Diseñar exportación y restauración verificadas; conservar también datasets, configuración y artefactos del modelo fuera de la base. [Backups de clúster gratuito](https://www.mongodb.com/docs/atlas/backup/cloud-backup/free-cluster-backup/).

El timeout de Functions depende del plan: el plan Consumption documenta máximo de diez minutos; otros planes tienen límites y condiciones diferentes. Medir el entrenamiento antes de alojarlo allí. Si excede el presupuesto, separar entrenamiento e inferencia batch y documentar el cambio. [Límites oficiales de Azure Functions](https://learn.microsoft.com/en-us/azure/azure-functions/functions-scale).

## Arquitectura propuesta

Flujo de carga: usuario autorizado → Angular → FastAPI → validación → dataset versionado + MongoDB. Flujo analítico: dataset validado → preparación → entrenamiento/validación → pronóstico → simulación y recomendaciones → persistencia de corrida completa → API → pantallas.

Una corrida tendrá un identificador único, fecha de corte, hash del dataset, versión del código, parámetros, modelo y métricas. Solo publicar corridas completadas. Un fallo conserva el último resultado válido y muestra su antigüedad. El timer debe reclamar un bloqueo por corrida y evitar duplicados al reintentar. Los artefactos binarios del modelo se guardan en almacenamiento de archivos o blobs con checksum; MongoDB conserva su referencia. No cargar archivos de modelos enviados por usuarios.

Propuesta de estructura de implementación: `backend/` para API y autenticación; `pipeline/` para datos, ML y simulación; `frontend/` para Angular; `infra/` para despliegue; `tests/` para pruebas; `docs/` para evidencia. Un solo integrador controla contratos y archivos de dependencias.

Pantallas necesarias: acceso; carga e incidencias; ventas y calidad; pronósticos filtrables por categoría/producto y horizonte; recomendaciones con stock, plazo y explicación; comparación de políticas; historial de corridas. Estados obligatorios: cargando, sin datos, error, resultados antiguos y datos insuficientes. No presentar valores faltantes como cero.

## Datos necesarios y decisiones de negocio

Ventas detalladas de los seis meses recibidas. Para la modalidad autorizada, usar los parámetros y movimientos sintéticos de DECISIONES_DATOS.md. Una futura validación real requerirá catálogo, stock inicial, movimientos, pedidos, costos y plazos reales. Con ventas solamente se puede pronosticar ventas observadas, pero no reconstruir de forma fiable demanda perdida ni disponibilidad histórica. Un día sin venta puede ser demanda cero, cierre, ausencia de registro o quiebre: distinguirlos.

Confirmar con el responsable: frecuencia real de revisión, lead time por proveedor, lote mínimo, múltiplo de empaque, stock de seguridad, pedidos en tránsito, devoluciones, promociones y criterio de sobrestock. Registrar fecha y responsable de cada respuesta. Si no hay política actual documentada, reconstruirla con entrevista y movimientos; un promedio móvil usado como sustituto debe llamarse política de referencia, no política real.

Propuesta para resolver categoría/SKU: mantener la evaluación por categoría exigida por el objetivo 1; producir demanda y recomendaciones por SKU cuando exista soporte suficiente, agregando para verificar coherencia. Si se desagrega un pronóstico de categoría por participaciones históricas, calcularlas solo con datos anteriores al corte y declarar la limitación. No distribuir una compra por categoría como si todos sus artículos fueran intercambiables. Para series escasas usar baseline explícito o marcar insuficiencia.

## Procedimiento científico

1. Conservar originales y manifiesto de archivos; perfilar fechas, vacíos, duplicados, cantidades, unidades y totales por mes. Separar devoluciones y filas de resumen. IQR sirve para marcar anomalías; no eliminar promociones reales sin justificación.
2. Construir calendario diario por entidad. Con seis observaciones mensuales no hay base suficiente para ensambles por categoría; usar resolución diaria si los registros la permiten. Seis meses tampoco demuestran estacionalidad anual.
3. Reservar el último mes completo como test. Dentro de los cinco meses previos usar validación temporal de origen móvil; no partición aleatoria. Congelar selección e hiperparámetros antes del test.
4. Comparar naive, naive semanal y media móvil con Random Forest y un boosting. Construir rezagos y medias con desplazamiento previo. Precio futuro solo si era conocido al emitir el pronóstico. Nunca usar cantidad del período objetivo como predictor de sí misma.
5. Alinear la validación con la operación: horizonte provisional de siete días, revisable según lead time y revisión. Para horizontes múltiples no usar ventas futuras reales para construir rezagos dentro del bloque pronosticado. Si se actualiza diariamente, declararlo y reproducirlo igual en ambos escenarios.
6. Reportar MAE, RMSE, MAPE y R² por categoría y global, tamaños de muestra y baselines. MAPE solo sobre denominadores positivos, con cobertura informada; ceros se reportan aparte. Añadir WAPE cuando el total real sea positivo. R² no es interpretable con series constantes; registrar N/A, no forzar un número.
7. Comparar inventarios bajo iguales fechas, demanda, stock inicial, costos, restricciones y tiempos. Definir cuándo se reciben pedidos, se atiende demanda y se repone. No entregar a la política información futura.
8. Medir sensibilidad a lead time, seguridad y supuestos de demanda censurada. Una simulación condicionada a ventas observadas no demuestra causalidad ni mejora real ya obtenida. Una prueba estadística requiere unidades comparables y dependencias temporales consideradas; no afirmar significancia por una sola comparación agregada.

Reposición propuesta por revisión periódica: posición = stock disponible + pedidos en tránsito − compromisos; objetivo = demanda prevista durante lead time + período de revisión + stock de seguridad; pedido = máximo de cero y objetivo − posición, redondeado al múltiplo de empaque y sujeto a mínimos y restricciones. La forma de calcular seguridad y el umbral de exceso se fijan con el negocio y datos previos al test.

## Indicadores operativos

| Indicador | Definición propuesta | Precaución |
|---|---|---|
| Fill rate | Unidades atendidas / unidades demandadas | Sin demanda perdida observada es aproximación o simulación |
| Quiebres | Días SKU con demanda no atendida / días SKU evaluables | No confundir stock cero sin demanda con venta perdida |
| Exceso | SKUs que exceden umbral acordado / SKUs evaluables | Explicitar fecha o promedio temporal |
| Holding | Suma de inventario medio diario × costo unitario × tasa diaria | Tasa debe provenir del negocio o quedar como escenario |
| Rotación | Costo de ventas / inventario promedio al costo | Alternativa en unidades por SKU; no mezclar ingresos y unidades |

## Plan hasta el 23 de octubre

| Día | Entrega comprobable | Responsable humano de referencia | Dependencia |
|---|---|---|---|
| 16 viernes | Alcance, contratos, entorno, solicitud de datos, backlog | Rogelio y Milton | Documento |
| 17 sábado | Datos auditados; política actual; primer flujo carga → consulta | Mauro y Rogelio; Milton valida negocio | Datos y acceso |
| 18 domingo | Baselines, validación temporal y modelo candidato; UI conectada | Blanca y Fabricio | Dataset aceptado |
| 19 lunes | Simulador y recomendaciones con casos calculados a mano | Rogelio y Blanca | Reglas y pronóstico |
| 20 martes | Integración completa, autenticación, batch y despliegue de prueba | Rogelio y Fabricio | Contratos estables y nube |
| 21 miércoles | Test final congelado, evidencia de métricas, aceptación inicial | Blanca, Mauro y Fabricio | Flujo integral |
| 22 jueves | Correcciones críticas, restauración, manuales e informe | Todo el equipo; Milton coordina | Pruebas |
| 23 viernes | Ensayo, versión final, video y entrega antes de las 18:00 | Todo el equipo | Criterios de cierre |

Esta asignación conserva los roles declarados en la fuente; no confirma disponibilidad real de los integrantes. Estimación de planificación: 110–170 horas-persona distribuidas entre datos (18–26), ML (20–30), inventarios (16–24), API (18–28), UI (16–24), integración/calidad/documentación (22–38). Los agentes reducen tareas mecánicas, pero no eliminan revisión humana ni espera por accesos. Validar capacidad efectiva el día 17.

Ruta crítica: datos y política → dataset → evaluación temporal → simulación → integración → aceptación → evidencia. UI y API pueden avanzar con contratos y datos sintéticos etiquetados mientras llega el historial. Congelar nuevas funcionalidades el 20 por la noche. El 22 se reservan correcciones y ensayo; el 23 no se estrena arquitectura.

Los seis meses detallados ya se recibieron; al cierre del 17 deben quedar conciliados y con reglas de limpieza explícitas. Si esa validación falla, continuar construcción y registrar la limitación. Se adoptó explícitamente la simulación de escenarios sintéticos; documentar el cambio y la necesidad de conformidad académica, sin presentarla como reconstrucción de la política real. Si falla la nube, conservar una demostración local reproducible y registrar despliegue pendiente; no equipararla a una plataforma publicada. No recortar silenciosamente backtesting, seguridad o evidencia para cumplir la fecha.

## Trabajo con Claude Code y agentes

Claude principal integra y mantiene el plan. Los agentes preparados cubren datos, forecasting, API/inventarios, frontend y revisión de calidad. Utilizar hasta tres trabajadores simultáneos como límite operativo propuesto, solo con archivos separados y contratos acordados. Los revisores devuelven hallazgos al integrador. Nadie cambia contratos, lockfiles o archivos ajenos sin coordinar. Si una tarea es corta o depende de otra aún inestable, ejecutarla secuencialmente.

Los subagentes se definen en `.claude/agents/` y las skills en `.claude/skills/`. Son configuraciones del proyecto, no programas autónomos permanentemente activos. [Agentes oficiales](https://code.claude.com/docs/en/sub-agents), [skills oficiales](https://code.claude.com/docs/en/skills).

Codex asume dirección técnica y revisión de evidencia en este chat: decide prioridad, examina entregas y emite instrucciones concretas para la siguiente iteración. Claude implementa y prueba. El equipo valida reglas, datos, costos y resultados académicos. No hay vigilancia automática ni proceso continuo configurado hasta el 23; cada sesión debe retomar ESTADO.md.

## Skills, modos, plugins y conectores

| Recurso | Uso | Decisión |
|---|---|---|
| Skills propias | Datos, validación temporal, simulación, entrega | Incluidas en el paquete |
| Agentes propios | Separar trabajo y revisión | Incluidos; activar según dependencias |
| Modo de planificación | Cerrar ambigüedades y contratos | Usarlo al iniciar o cambiar arquitectura |
| Modo de implementación normal | Editar y ejecutar pruebas | Con permisos habituales; sin bypass global |
| Git local | Versiones y revisión de cambios | Necesario; inicializar/adoptar repo al comenzar |
| GitHub | Colaboración y CI | Conectar cuando exista remoto; CLI basta |
| MCP de navegador | Inspección interactiva opcional | No es requisito para pruebas automatizadas |
| MCP de MongoDB/Azure | Administración externa | No necesario para desarrollar; preferir SDK/CLI y accesos mínimos |
| Extensiones VS Code | Python y Angular | Ya detectadas; CLI Claude funciona sin extensión adicional |
| Docker | Base local y reproducibilidad | Instalado; servicio no activo |
| Plugins genéricos y “mods” | Sin necesidad técnica identificada | No instalar un catálogo por volumen; no hay mod obligatorio |

No se necesitan LLMs dentro del producto, embeddings, RAG, Kubernetes, Kafka ni agentes que realicen compras. Eso ampliaría alcance sin resolver el problema descrito. Jupyter, Colab y conectores externos son opcionales, no bloqueantes.

## Correcciones necesarias al informe académico

Completar resumen/abstract, matriz de trazabilidad, arquitectura, cronograma, seguridad, pruebas, despliegue, resultados, discusión, conclusiones y anexos. Hay texto de plantilla y verbos en pasado que no acreditan ejecución. El plan de calidad confunde Selenium con pruebas unitarias y contiene una cifra de defectos sin contexto; reemplazarla por criterio verificable y resultados reales. Alinear problemas específicos, objetivos y dimensiones. Justificar denominadores, granularidad y las metas MAPE/R². Diferenciar presupuesto de trabajo valorizado (el documento menciona S/ 6 600) de gastos monetarios reales; no asumir costo cero de nube ni validar bibliografía por estar citada.

Las referencias y cifras de estudios previos requieren comprobación bibliográfica antes de usarse como sustento final; no se realizó aquí una auditoría integral de DOI y artículos. Las imágenes del documento muestran Pareto, Ishikawa, fases y matriz de riesgos; las tablas y textos se incorporaron al análisis. No se modificó ni se certificó el diseño del DOCX.

## Condiciones de entrega completa

Una instalación nueva reproduce la aplicación con versiones fijadas; los datos autorizados se importan con conciliación; pronósticos y recomendaciones guardan trazabilidad; ambas políticas se comparan sin fuga; los permisos se comprueban en la API; la interfaz funciona para los usuarios previstos; el batch no duplica corridas; despliegue y restauración tienen evidencia; informe, manual, repositorio y video están listos. El video solicitado por la plantilla tiene máximo diez minutos, con tres de teoría y siete de producto.

Para cada afirmación conservar: requisito, prueba o experimento, resultado, archivo de evidencia, fecha y responsable. No completar métricas, actas, aceptación del cliente o conclusiones con resultados inventados.

## Decisiones posteriores del usuario

DECISIONES_DATOS.md es la referencia vigente para créditos, días excluidos, categoría y datos sintéticos. El producto mantiene su arquitectura; la evaluación de inventarios compara una referencia sintética con una política basada en pronóstico. Se generó data/synthetic/reference_v1 con parámetros previos a agosto, movimientos y controles de balance. No hay resultados de ML ni mejora empírica demostrada.
