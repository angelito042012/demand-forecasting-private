# Etapa 15: aceptación humana y publicación condicionada a autorización

Fecha límite:23/10/2026 Lima. Leer REVISION_CODEX_15.md y paquete vigente de docs/T11_PLAN_DESPLIEGUE.md. No confundir este número de encargo con el hito T15 de entrega final: ese hito sigue pendiente. R12–R16 cerrados localmente; no repetirlos, ni modelos, T12 real o preflight Microsoft.App/cuota concluido.

## 1. Condición de entrada para operar en nube

Este archivo **no autoriza gasto ni transferencias**. Solo iniciar acciones1–7 del paquete si existe un mensaje explícito de Rogelio que autorice ese conjunto, los destinos/datos y el techo. Una aprobación del conjunto basta para sus comandos comprendidos; no pedir confirmación por cada paso rutinario. No interpretar captura de informe ni silencio como aprobación.

Paquete autorizable: grupo nuevo rg-demand-forecasting-pub en Brazil South, un entorno Consumption, API y worker0,5vCPU/1GiB una réplica cada uno, ACRBasic, Filesdf-dataRW/df-refROparaWorker, LogAnalyticsconcap e identidadAcrPull; registrar solo proveedores imprescindibles. Imagen sin datos/secretos, referenciaT07privada7,6MiB y solo basepub~214MB haciaAtlasFree existente. Techo operativo20USD del crédito hasta23/10, intervención12USD observados/proyección que amenace20/medidor inesperado. No gasto de bolsillo, pago por uso, servicios Dedicated/NAT/VNet ni apertura globalAtlas por defecto. Si cambia el alcance/costo o el destino contiene datos inesperados, detener la acción dependiente y solicitar decisión concreta; continuar trabajo independiente.

Si no existe aprobación: mantener demo activa y guiar aceptación local. No solicitar nuevo código Azure todavía. No crear una cuenta ni pedir de nuevo información ya acordada.

## 2. Aceptación local inmediata

La demo df-demo está disponible en https://localhost:8443 sobre copia restaurada, con credenciales privadas. No leer/imprimir el archivo de claves en respuesta o logs. Si Rogelio necesita ayuda, indicar la ruta para abrirlo localmente o create-user interactivo; no pedir contraseña por chat.

Guiar cinco pasos del guion real y solicitar resultados (cumple/no cumple y observación); marcar A14 solo con participación real. No completar la tabla por las pruebas automáticas. Mantener advertencia de inventario simulado, antigüedad, WAPE distinto de acierto, RF sin mejora principal, final sin pedidos inventados. Registrar versión e imagen, URL, fecha y quién ejecutó. No prometer aceptación académica del asesor/MYPE.

No apagar/recrear esta demo ni eliminar sus volúmenes para realizar el despliegue. Los trabajos de nube usan recursos/configuración independientes. Si hay conflicto real de puertos/recursos locales, explicarlo y resolver sin destruir datos.

## 3. Ejecución de nube, solo después de autorizar

1. Registrar el texto/alcance de aprobación en el estado y revisar saldo disponible por el portal con el usuario. Recalcular costo según días reales, preservando margen por uso aún no reflejado en Cost Management. La ausencia de cargos visibles al crear el entorno no demuestra costo cero. No esperar indefinidamente un medidor para poder continuar; usar composición de recursos/tarifas verificadas y límites de réplica/tiempo para estimar, documentando incertidumbre. Ninguna alerta es un corte garantizado a20USD.
2. Iniciar sesión oficial con MFA del propio usuario cuando sea necesario. No imprimir contraseñas, tokens o archivos de caché. Reutilizar la sesión durante la operación autorizada mientras siga vigente; cerrar sesión al terminar la unidad de despliegue. Si MFA rechaza escritura, mostrar el error preciso y resolver con autenticación apropiada, sin desactivar políticas.
3. Registrar solo los proveedores listados necesarios. Crear únicamente el grupo nuevo; inventariar recursos y etiquetas de alcance. Crear el entorno Consumption y dependencias mínimas necesarias según Bicep (logs puede ser dependencia del entorno; no fingir un entorno aislado imposible). Verificar cuota de cómputo y configuración real. No asignar roles al usuario; solo AcrPull a la identidad de aplicación en el ámbito del registro previsto. Si requiere solicitud de cuota no autorizada o recurso adicional, presentar decisión antes de actuar.
4. Construir imagen desde commit identificado que contiene la correcciónCSS, etiqueta/digest inmutables; verificar HTML real y contexto sin datos/.env/.git. Crear ACR/Storage/shares/logs/identidad según plan y subir la imagen solo dentro del alcance aprobado. Montar referencia privada de solo lectura únicamente en worker y datos durables compartidos con API. Verificar permisos del usuario10001 sin relajar seguridad global.
5. Atlas: guiar a Rogelio de forma sencilla para crear usuario mínimo readWrite solo pub y rotar la credencial expuesta. Obtener el secreto por un archivo privado/gestor local controlado o mecanismo seguro para inyección, sin pegarlo en el chat, imprimirlo o versionarlo. No dejar instrucciones imposibles que requieran un gestor remoto aún no creado: explicar el paso concreto y la ruta privada solo cuando se necesite. Configurar lista de IP limitada al egreso de Azure; si no se puede dentro del alcance, solicitar decisión sobre esa limitación, sin abrir 0.0.0.0/0 por iniciativa propia. Probar DNS/TLS/conectividad real.
6. Exportar/verificar copia local pertinente en mantenimiento real; restaurar en destino Atlas nuevo/vacío. No migrar v1/v2 completas, fuentes Excel originales, usuarios/sesiones/jobs de ensayo ni credenciales demo. Si Atlas contiene contenido inesperado, abortar restauración sin borrar. Registrar conteos, importes, índices, puntero y hashes pertinentes; confirmar lógica+índices y proyección de capacidad de512MB. No repetir la evaluación científica para migrar.
7. Crear API/worker con secretos inyectados, origenHTTPS exacto y proxy de confianza verificado; crear administrador/lector propios de publicación por canal privado. No reutilizar contraseñas demo. HTTPS de plataforma válido; la opción insecure-local no se usa en nube.
8. Probar desde la plataforma: health, autenticación/roles/CSRF y límite de login frente a cabeceras falsificadas, histórica/final separadas, carga y generación mínima idempotentes, conservación de puntero, persistencia de archivos tras reemplazo, referencia válida y no expuesta por web. Medir1/5sesiones con medidor corregido y muestras privadas; informar p95 y máximos/coldstart separadamente. Elegir el mínimo caso pertinente sin inflarAtlas con muchas corridas (hay margen limitado). No borrar históricos para liberar espacio.
9. Demostrar copia/restauración en el entorno compatible con Atlas sin restaurar encima de datos existentes. Mantener escritores detenidos; documentar límites como currentOp restringido. Si una restauración adicional simultánea amenaza cuota, usar un procedimiento secuencial con copia local/base nueva dentro del presupuesto y sin borrar el destino original hasta autorización específica. No desactivar controles ni declarar aprobado un paso omitido.
10. A13 solo completa con evidenciaHTTPS y usuarios/sesiones en nube; A14 exige resultados humanos. Registrar URL real, commit/digest, recursos, ocupación, costos observados/estimados, límites y pasos de reversión. Mantener la demo local disponible como respaldo.

## 4. Costos, salida y límites de autonomía

No prometer vigilancia de Claude entre sesiones ni automatización de apagado inexistente. Documentar revisión de costos al terminar la sesión, a24h y diaria mientras esté autorizado. Si se proyecta sobrepasar20USD o aparece medidor fuera del alcance, no ampliar recursos ni esperar a agotar crédito: comunicar riesgo y preparar reducción o desmontaje de recursos nuevos propios, conservando copia verificada. Nunca tocar recursos ajenos. Si se necesita un nuevo presupuesto, pedirlo antes de asumirlo.

La política después23/10 sigue por decidir: pedir una sola preferencia concreta sobre mantener laURL hasta una fecha del docente con nuevo presupuesto o desmontar tras copia. No asumir gasto mensual ni fecha de eliminación. Registrar la decisión antes del vencimiento de la autorización; no tratar aprobación hasta23/10 como gasto indefinido.

Si falla nube dentro del alcance, conservar demo/evidencias y reportar el bloqueo exacto y alternativa estimada; no cambiar de stack o cobrar otro servicio silenciosamente. No inventar A13 ni dejar todo el proyecto detenido: continuar documentación y aceptación local.

## 5. Cierre documental y continuidad

Tras resultados reales de nube/humano, actualizar matriz de cierre, informe/manuales, guion de video y versión. Conservar los borradores como tales hasta revisión final; no crear firmas, encuestas o aceptación del asesor. Preparar presentación/video según fuente y solicitud del usuario, sin afirmar grabación/publicación que no exista.

Actualizar ESTADO/TRASPASO/BACKLOG/HISTORIAL y autoridad de AGENTS/CLAUDE/RETOMAR con el encargo vigente y límites reales. Evidencia extensa privada, sin secretos ni datos comerciales en Git. Commits locales de archivos propios revisados.

Entrega breve: URL y resultado real por puerta, pruebas ejecutadas/omitidas, costo/ocupación, cómo acceder privadamente, bloqueos y siguiente acción humana concreta. No repetir pruebas amplias sin cambio/riesgo nuevo. No marcar T15 final antes de A13/A14 y documentación/entrega real o excepción explícita del usuario.
