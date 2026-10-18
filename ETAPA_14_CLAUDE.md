# Etapa 14: cerrar procedimiento de aceptación y dejar publicación lista para autorizar

Encargo posterior a 42233a6 y REVISION_CODEX_14.md. Fecha límite: 23/10/2026, Lima. Claude ejecuta; Codex dirige/revisa. No repetir modelos, evaluación final, registro Microsoft.App ni preflight concluido. No hay autorización de gasto ni publicación todavía.

## A. Dos correcciones pequeñas, sin ampliar alcance

1. R15: corregir `scripts/t13a_perf.py` según revisión14. Definir percentil nearest-rank y probar valores conocidos n20/n100; capturar fallos HTTP/timeout por sesión y estados no200, exigir conteos completos y cerrar recursos en finally. Ninguna tanda incompleta puede terminar con informe aprobado/salida de éxito. Cero muestras no debe producir una excepción no manejada de statistics. Timeout total para coldstart. TLS verificado por defecto para nube; omisión solo mediante opción explícita de ensayo local. Guardar muestras privadas y resumir exactitud/completitud/errores. Regresiones sintéticas sin levantar servicios.
2. Conservar el perf.json original. Corregir descripción de cifras anteriores: son una cota conservadora, no el nearest-rank exacto; no inventar un p95 recalculado sin muestras. Informar máximos>2s aparte del criterio p95. Se permite repetir solo el ensayo corto local corregido si hace falta p95 exacto; no toda la suite ni navegador de nuevo sin cambios relevantes.
3. R16: arreglar manual/guion para que la demo final use copia temporal nueva con T12, histórica auditada y cola/usuarios coherentes. Inyectar de manera explícita la misma URI/base a API, CLI de usuarios y worker; comprobarlo sin imprimir secretos. Si el mecanismo se hace con un script nuevo, que sea pequeño y validable, no una refactorización del sistema. No alterar v1/v2/pub ni crear una histórica nueva por rutina.
4. Separar paradas/mantenimiento PowerShell de compose y comprobar escritores; no borrar volúmenes para una parada habitual. Limitar toda limpieza a procesos/rutas/bases propias verificadas.
5. Ajustes documentales de revisión14: snapshot correspondiente a corrida, MAPEacum14 por entidad, SKU-fold vsSKUúnicos, matriz/versión actuales. Conservar resultados adversos y pendientes nube/humano. Consolidar autoridad vigente de AGENTS/CLAUDE/RETOMAR y ESTADO/TRASPASO/BACKLOG con antecedentes en HISTORIAL; R12–R14 siguen aceptados localmente.

## B. Dejar la demostración preparada para Rogelio

Usar una copia nueva restaurada y un solo método de arranque (preferentemente imagen de producción con correcciónCSS) que exponga solo loopback local. Preparar lector/admin mediante canal privado; contraseñas no en respuesta/log/chat/Git. No reutilizar la base temporal de T13A ya eliminada. No usar 0.0.0.0 en el binding público del equipo para facilitar acceso externo.

Antes de entregarla: verificar health, misma base en todos los procesos, histórica correcta y corrida final visibles; confirmar HTML real de la imagen sin media=print/onload de estilos, CSP conservada. Esta es una comprobación pequeña del artefacto concreto, no repetir22 pasos ni experimentos. Si se modifica código funcional, comprobar lo afectado.

Dejar demo disponible para la prueba humana (no apagarla al terminar, salvo fallo o conflicto real). Registrar exactamente procesos/contenedores/URL/base y parada segura. No detener Mongo o aplicaciones ajenas. Si hay contraseña por definir, explicar un solo paso local seguro al usuario; no pedirla por chat. Entregarle un guion breve inicial (acceso, histórica/final, WAPE, recomendación simulada) usando la URL real activa. Aceptación permanece pendiente hasta que Rogelio ejecute y comunique resultados; no completar su columna por inferencia.

## C. Preparar autorización de nube concreta, todavía sin ejecutarla

Actualizar docs/T11_PLAN_DESPLIEGUE.md de forma coherente, con acciones numeradas1–7 y alternativas posteriores en8. Puede aprobarse el conjunto con un solo mensaje explícito y límites; quitar la exigencia artificial de autorizar cada acción individualmente. Mantener pasos seguros comprobables y no avanzar si la autorización real no existe.

El paquete propuesto debe decir claramente:

- Objetivo: URL HTTPS de la aplicación, usuarios admin/lector propios, generación/carga y recuperación verificadas en la plataforma.
- Azure for Students: únicamente el grupo nuevo `rg-demand-forecasting-pub` en Brazil South; un entorno Consumption; API y worker con 0,5 CPU/1 GiB y una réplica cada uno; ACR Basic; Storage LRS con `df-data` de lectura/escritura y `df-ref` de solo lectura para el worker; Log Analytics con tope; identidad con AcrPull. Registrar solo los proveedores imprescindibles. Sin Dedicated, VNet, NAT, endpoints privados o mantenimiento planificado; sin conversión a pago por uso ni gastos de bolsillo. Si un paso exige cambiar estas condiciones, documentar el bloqueo, no aceptar ampliaciones.
- Techo operativo propuesto: US$20 del crédito hasta el 23/10; estimación según días reales antes de crear recursos. Intervenir a US$12 observados o si la proyección de consumo amenaza US$20. Explicar que `spendingLimit=On` protege el saldo total de la oferta, no configura un corte personalizado de US$20, y Cost Management tiene demora. Reservar margen por costos aún no reflejados; si aparecen medidores inesperados o no se pueden acotar, detener el avance y preparar reducción/desmontaje seguro de recursos propios. No prometer vigilancia permanente de Claude cuando la sesión no está activa ni un apagado automático inexistente.
- Transferencias autorizables: imagen sin secretos/datos crudos, referencia T07 privada de 7,6 MiB hacia Azure Files y únicamente base de publicación de unos 214 MB hacia Atlas Free existente. No migrar toda v2/v1, originales Excel, sesiones, usuarios o trabajos de ensayo. Copia integral local previa y destinos/base vacíos; abortar si Atlas ya tiene contenido inesperado. No sobreescribir ni borrar una base remota preexistente sin acuerdo.
- Atlas: usuario mínimo `readWrite` solo en pub, credencial expuesta rotada antes de usar, permisos y lista de IP de egreso acotados, TLS real. Dar al usuario instrucciones concretas para configurar y guardar el secreto por canal privado; nunca pedir contraseñas/tokens en chat o imágenes. No abrir `0.0.0.0/0` por defecto; si el egreso estable no es posible dentro del alcance, presentar la decisión antes de abrirlo. No introducir NAT pagado silenciosamente.
- Despliegue trazable: reconstruir la imagen desde el commit corregido, con etiqueta/digest inmutable; verificar HTML/CSP de esa imagen; montar referencia privada de solo lectura y almacenamiento durable. Administrador creado por canal privado; secretos inyectados sin imprimir valores ni incluirlos en el historial versionado.
- Pruebas posteriores en nube: health/HTTPS, roles/CSRF y cabeceras de proxy adversariales; consultas con una y cinco sesiones usando el medidor corregido y muestras guardadas; generación/idempotencia y archivos durables tras reemplazo. Coordinar mantenimiento para exportar/restaurar sin operar sobre v1/v2 originales. Documentar las operaciones no admitidas por Atlas Free; no desactivar verificaciones para completar la tarea.
- No dar A13 por cumplido solo por tener URL: requiere evidencia de nube. A14 humana también sigue pendiente.
- Después del 23/10: presentar elección sin imponerla: desmontar tras copia verificada o conservar URL con modo ligero y costo mensual nuevo autorizado. No asumir gasto recurrente indefinido. Si el docente requiere revisar la URL después de la entrega, preguntar fecha concreta antes de planificar el desmontaje.

Se puede cerrar preparación y guiar la aceptación local sin volver a autenticar Azure. El acceso de escritura a Azure será cuando exista aprobación, con MFA propia y las acciones ya autorizadas, sin pedir permiso por cada comando incluido. No enviar solicitudes de cuota que el usuario no autorizó.

## D. Entrega breve

Commit local de cambios propios revisados, evidencia de regresiones R15 y verificación de la demo en `artifacts/private/t13b/`, y `docs/T13B_REPORTE.md`. Conservar originales/evidencias previas. No ejecutar nuevas pruebas amplias salvo cambio/fallo que lo justifique.

Respuesta final al usuario:
1. R15/R16 corregidos y pruebas realmente ejecutadas.
2. URL local activa, versión, cómo obtener/crear sus usuarios sin revelar claves y cinco pasos para probar.
3. Plan de nube concreto listo para una aprobación con límite y política posterior pendiente.
4. Archivos para Codex y bloqueos reales. No afirmar publicación, aceptación o informe/video definitivo.
