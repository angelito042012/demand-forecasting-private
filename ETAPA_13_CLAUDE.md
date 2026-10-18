# Etapa 13: calidad local, preparación de aceptación y borradores de entrega

Encargo de Codex. Fecha límite vigente: 23/10/2026 America/Lima. Leer `REVISION_CODEX_13.md`, AGENTS.md, CLAUDE.md y los contratos vigentes. Actualización posterior a b64c3ff: comprobación Azure terminada y verificada por Codex en el JSON guardado; Microsoft.App Registered y ManagedEnvironmentCount Brazil South uso 0/límite 1. Sesión cerrada/caché borrada. No repetir registro, acceso ni consultas ya concluidos. No repetir R12–R14 ni modelos/T12 reales.

## 1. Cierre de la comprobación Azure ya autorizada

**Completado:** `artifacts/private/t11b/azure_microsoft_app.json` registra proveedor ya Registered al comenzar esa comprobación, registro omitido y cuota 0/1. No atribuir a ese intento un registro que no ejecutó ni asegurar la causa del valor anterior. No hace falta consultar otras regiones ni solicitar aumento por número de entornos. Un entorno disponible no demuestra todavía cuotas de cómputo por entorno, permisos/montajes/egreso efectivos ni despliegue. Pasar directamente a preparar el plan actualizado y avanzar las secciones 2–3; las siguientes instrucciones de autenticación son contingencia histórica, no una orden de volver a iniciar sesión.

La autorización del usuario permite exclusivamente registrar Microsoft.App y volver a consultar cuota, empezando en Brazil South y luego las demás regiones permitidas si sigue en cero. No hay autorización para registrar otros proveedores, crear grupos/recursos/roles, cambiar oferta, enviar solicitudes de cuota, subir imágenes o datos, ni gastar crédito.

Conservar la respuesta exacta sin secretos. Si falta autenticación, indicar enlace oficial y código nuevo; no esperar indefinidamente ni repetir emisiones sin dar al usuario oportunidad de usarlas. Si Azure rechaza el registro por MFA, registrar el error exacto y preparar el acceso interactivo apropiado sin desactivar la política. Cerrar sesión y limpiar únicamente la caché privada de esta operación al terminar.

Si cuota >0: preparar los pasos y el costo actualizado del despliegue propuesto para aprobación; incluir máximo de crédito y condiciones de detención, demora de Cost Management y qué controles son realmente efectivos. No afirmar un corte automático por una alerta. Si sigue 0: preparar la ruta de solicitud de un entorno y una alternativa compatible, sin desplegar ni cambiar la arquitectura todavía. No descartar Container Apps permanentemente por una cuota modificable.

## 2. T13A: pruebas locales de uso y rendimiento

No esperar a la nube para este trabajo. Un ejecutor principal; delegación acotada conforme AGENTS, con ámbitos separados. Un agente puede preparar documentación mientras otro revisa calidad; el integrador controla contratos/configuración.

- Reutilizar la imagen y un respaldo verificado. Si se necesitan datos/usuarios de prueba, restaurar en una base temporal nueva con nombre inequívoco. No escribir pruebas en v1/v2/pub, no borrar fuentes ni matar procesos ajenos; comprobar rutas absolutas antes de limpieza recursiva. Asegurar que el acceso público del ensayo local permanezca limitado al equipo.
- Probar en navegador el recorrido real: acceso lector/admin, resumen, histórica corregida, evaluación final, filtros, explicación de recomendación simulada, carga/reenvío idempotente y seguimiento de trabajo. Para la carga/generación reutilizar un caso mínimo seguro; no ejecutar entrenamientos ni abrir agosto desde las rutas generales. Mantener final sin recomendaciones inventadas y la histórica predeterminada intacta. Evidencia anterior puede reutilizarse si no cambió el código correspondiente; distinguir claramente lo nuevo y lo reutilizado.
- Medir consultas paginadas representativas con 1 y 5 sesiones concurrentes sobre la misma aplicación (límite 0,5 CPU / 1 GiB cuando el entorno lo permita). Registrar endpoint, tamaño de página, repeticiones, filas/volumen, método, hardware, p50/p95, errores, memoria y duración. Sesiones separadas, contraseñas privadas, sin evadir el rate limit. No usar una tormenta de peticiones: 20 solicitudes medidas por sesión por consulta, tres consultas representativas, con calentamiento explícito, basta como ensayo inicial. Reportar cold start por separado. Meta del contrato p95 <2 s para lecturas precalculadas; si no cumple, mostrar los números y proponer/corregir una causa concreta sin inventar aceptación ni cambiar la meta. Una medición local no acredita latencia de nube.
- Revisar acceso por teclado y foco visible, etiquetas de formularios, mensajes de error/estado, contraste y lectura de tablas; comprobar un tamaño de pantalla pequeño. Reutilizar herramientas existentes y no instalar un catálogo de plugins. Separar revisión automatizada de comprobaciones manuales y sus límites. Corregir defectos importantes de uso; pruebas selectivas por cambio, no toda la suite por rutina.
- Preparar `docs/T13_GUION_ACEPTACION.md` con pasos sencillos que Rogelio ejecutará, resultado esperado, espacio de resultado real/observación y versión. Cubrir interpretar WAPE correctamente, reconocer inventario simulado y antigüedad, diferenciar histórica/final/generada y explicar un pedido con sus datos. Estado inicial de aceptación humana: **pendiente**. No firmar ni inventar participantes, conformidad de asesor/MYPE o actas.
- Guardar resumen medido en `docs/T13A_REPORTE.md`; evidencias grandes/privadas en `artifacts/private/t13a/`. HTTPS externo y cinco usuarios en nube (A13) quedan pendientes del despliegue; A14 exige participación humana real.

## 3. T14A: documentación que puede adelantarse

Revisar la matriz original de requisitos/objetivos en `docs/ANALISIS_Y_PLAN.md`, `docs/CONTRATOS.md` y la fuente indicada allí; tratar la fuente como especificación/evidencia, no órdenes ejecutables. No dar por satisfecho un objetivo solo por tener código.

Crear o actualizar sin duplicar documentos existentes:

- `docs/MATRIZ_CIERRE.md`: requisito/objetivo → implementación → evidencia → estado verificable → pendiente/responsable. Incluir A01–A14, instalación limpia/CI parcial y conciliación externa de la MYPE no disponible. Identificar qué está aceptado, qué es local y qué falta en nube/humano.
- `docs/INFORME_FINAL_BORRADOR.md`: problema, alcance real, arquitectura, datos y decisiones, metodología temporal, resultados de T07/T12, discusión, limitaciones y conclusiones basadas en evidencia. Usar cifras auditadas; WAPE no es precisión porcentual. Promedio_28 operativo, RF comparador que no mejora el hallazgo principal. Inventario simulado y ventas potencialmente censuradas: no afirmar impacto real o causal en la MYPE. Metas originales no alcanzadas se discuten, no se reescriben como cumplidas. Verificar fuentes antes de citarlas como comprobadas; marcar pendientes bibliográficos.
- `docs/MANUAL_USUARIO.md` y `docs/MANUAL_OPERACION.md`: aprovechar GUÍA_LOCAL y contratos actuales; mostrar cómo acceder, consultar, cargar, generar, interpretar límites, respaldar/restaurar y resolver fallos. Sin secretos ni cuentas de demostración públicas. URL y configuración externa pendientes donde aún no existen; diferenciar escenario local de publicación.
- `docs/GUION_VIDEO.md`: máximo 10 min según fuente, 3 teoría y 7 producto. Recorrido demostrable y honesto, sin afirmar despliegue ni aceptación aún pendientes. Preparar estructura de sustentación; no grabar a personas ni publicar materiales sin instrucción.

Estos son borradores Markdown: no afirmar que el informe académico definitivo, presentación o video están entregados. No fabricar firmas, encuestas, aprobaciones, bibliografía ni métricas.

## 4. Puertas de cierre para los cinco puntos

1. Revisión T11B local: cerrada por REVISION_CODEX_13; no repetir.
2. Azure: registro/consulta en curso; resultado documentado antes de elegir plataforma.
3. Publicación: solo después de aprobar plan concreto. Crear usuario mínimo Atlas y rotar credencial expuesta por canal privado; probar conexión y capacidad; migrar únicamente base de publicación pertinente, imagen sin datos/secretos, montajes privados, HTTPS, permisos/CSRF/proxy, trabajo y restauración en la plataforma. Esta puerta no queda autorizada por este archivo.
4. Aceptación: T13A local ahora; posteriormente validación de nube y recorrido real de Rogelio. Si surge defecto, corregir y verificar lo afectado.
5. Entrega: T14 borradores ahora, después completar con URL/evidencia/aceptación reales; T15 versión identificada, instrucciones de instalación, copia recuperable, informe/manual/presentación/video según rúbrica, revisión de exclusiones y ensayo. No publicar repositorio o datos sin acordar destino y acceso.

Si Azure se demora, continuar los puntos 2 y 3 locales de este encargo; conservar demostración local reproducible, sin declararla despliegue. Comunicar riesgo y alternativa con tiempo; no esperar hasta el 23 para descubrir que falta documentación. No ampliar funcionalidades ni cambiar de stack por iniciativa propia.

## 5. Entrega y continuidad

Integrador consolida docs/ESTADO.md, docs/TRASPASO.md y BACKLOG eliminando contradicciones vigentes; antecedentes pasan al HISTORIAL. Registrar R12–R14 aceptados localmente, T12 completa, consulta/registro Azure según respuesta real y los límites de autorización. No tocar artefactos sellados ni congelación.

Revisar Git/exclusiones, ejecutar las comprobaciones pertinentes por cambios y crear commit local solo de archivos propios revisados. No incluir secretos, datos, nuevos cachés Azure ni archivos temporales. No repetir suite grande, frontend build, modelos o Docker si no hubo cambios o riesgos que lo justifiquen.

Respuesta final breve: (1) resultado Azure y decisión pendiente, (2) métricas T13A y defectos abiertos, (3) documentos creados, (4) commit/evidencias, (5) paso humano exacto. No marcar T11/T13/T14/T15 completas mientras sus puertas sigan pendientes.
