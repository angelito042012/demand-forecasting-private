# T11B: últimos cierres locales y preflight de nube de solo lectura

Lee ESTADO/TRASPASO, `docs/REVISION_CODEX_12.md`, contrato y planT11. T11A/989fa6c entregada; publicación final local/recuperación Mongo verificadas. Codex83pruebas selectivas aprobadas. **No rehacer T11A ni T12.** Fecha final23/10/2026 Lima. Un integrador, hasta tres agentes con ámbitos independientes (estado, recuperación, runtime/infra); integración/contratos por principal.

Esta unidad cierra **R12–R14**, demuestra generación en contenedor y deja un plan de nube/costo listo para autorizar. Permite consultas de solo lectura en Azure tras autenticación interactiva del usuario. **No crear recursos/grupos/roles, registrar proveedores, subir imágenes, consumir crédito ni transferir datos de la aplicación a la nube.** No pedir nuevas cuentas ni secretos por chat. Si falta login, solicitar solo ese paso al usuario y seguir trabajo local; no detener correcciones independientes.

## 1. R12: que un fallo tardío no deje el paquete como completo

`report.write_report` marca _end antes de reconstruir/escribir el manifiesto final fuera del try. Repro privada Codex `artifacts/private/codex_review12_repro.py/.json`. Incluir el cierre entero en control de error y publicación coherente de estado/manifiesto. Fallo al releer preparación/auditoría, construir manifiesto, persistirlo o completar estado ⇒ reporte error/completa=false, sin manifiesto válido contradictorio. Escrituras atómicas/reanudación apropiadas, sin simular éxito.

Regresiones que fallen antes: error después del primer reporte y después de _end; recuperación correcta sin invocar preparación, lectura de agosto, entrenamiento, evaluación o simulación. No editar un booleano a mano. Reconciliar solo si hace falta el paquete existente con auditoría/reporte, con registro de corrección técnica posterior; conservar hashes originales de cálculo y fechas/intentos de las cinco fases originales.

## 2. R13: recuperación integral de archivos privados

Añadir bundle privado separado/verificable para T12 y referencias T07 necesarias, además de Mongo. El respaldo actual solo enumera18archivos y no los copia. Incluir manifiestos, predicciones/inicialización, modelos, NPZ/CSV mínimos y documentos/anclajes necesarios para funcionar/restaurar; rutas relativas seguras, lista cerrada, sin .env, contraseñas, sesiones, tokens ni .git. Datos comerciales solo en almacenamiento privado excluido de Git.

Restaurar en carpeta nueva vacía e independiente de originales/backup; verificar hash byte y lógico cuando corresponda. Demostrar lectura de las salidas finales restauradas y uso de referencias para generación, sin regenerar los datos originales. Pruebas de archivo ausente/alterado, path traversal, destino original/no vacío rechazado y respaldo parcial no anunciado como íntegro. No borrar originales para probarlo. Medir tamaño/duración y registrar `mongo_ok`, `artefactos_ok` y `recuperacion_integral_ok` diferenciados.

Actualizar acta de restauración/guía: detener escritores de verdad o imponer mantenimiento antes del export; conteos sin cambios no son un snapshot frente a mutaciones del mismo conteo. Conservar v1/v2/publicación originales y ambos históricos. No implementar ahora archivo selectivo que deje runs legibles sin sus hijos; el tamaño medido ya tiene margen.

## 3. R14: referencia verificable sin Git y generación real en contenedor

Montar T07 no basta: source._git_show requiere Git/commits y la imagen no los tiene. Preparar un **paquete de referencia de runtime** verificable con los anclajes/hashes aprobados ya versionados; montaje privado de solo lectura. Su creador puede usar Git local durante build/export; runtime no necesita .git ni Git. No autorizar una nueva referencia autoaprobada solo recalculando el hash del archivo actual; anclarla a los contenidos/config/commits aceptados.

Mantener el verificador de desarrollo y preservar versiones/rechazo de alteraciones. Pruebas de manifiesto/métricas/config/código/NPZ/CSV alterados y paquete incompleto: error claro antes de usar datos incompatibles. No incrustar modelos/datos/secretos en la imagen pública ni desactivar controles de referencia. Documentar rutas/datos requeridos por API y worker; limitar acceso web al frontend compilado, no al almacén privado.

Ejecutar **una generación real del baseline, origen10/07,H21** por API→job→worker de la imagen, en base de prueba/restaurada distinta, con referencias restauradas y recursos equivalentes a Bicep (0,5vCPU/1GiB inicialmente). Verificar salida completa, mismo origen/fechas/universo, cat=sumSKU, comparador compatible y recomendaciones exactas del snapshot T07; usar auditoría existente sin reentrenar modelos. Segundo pedido idempotente, puntero original intacto, reinicio no duplica; nunca usar snapshot de otro día.

Medir duración y máximo de memoria/ausencia de OOM; si1GiB no alcanza, ajustar recursos/plan/costo con evidencia. No ejecutar RF nuevo ni prepare/evaluate real de T12. Conservar prueba de comportamiento explícito si una referencia opcional falta; la demostración principal debe mantener las funciones acordadas. No repetir29pruebas del smoke ni todo el navegador si los cambios no lo justifican; añadir la comprobación nueva y regresiones afectadas.

## 4. Preflight autenticado de solo lectura y costo corregido

Preparar CLI aislada según plan (contenedor oficial o herramienta local separada), sin tocar el venv bloqueado. Autenticación del **propio usuario en su navegador**, p.ej. device-code, sin pedir/guardar contraseñas ni imprimir access/refresh tokens. Mantener caché de sesión privada; no copiarla al repositorio. No es necesario conceder roles nuevos a nadie para hacer las consultas que permita su cuenta actual.

Tras login, consultar únicamente suscripción/oferta/saldo cuando disponible, políticas de regiones, providers (solo show/list, no register), cuotas y permisos efectivos para los recursos propuestos; registrar resultado mínimo sin datos personales/identificadores innecesarios. `what-if` solo si hay grupo existente y permiso apropiado, sin crearlo para este fin; no presentarlo como confirmación de costo o garantía de cuota. Si el beneficio/saldo solo se ve en portal, pedir esa verificación puntual al usuario sin secretos. No aceptar presupuestos ni términos nuevos.

Corregir `T11_PLAN_DESPLIEGUE.md` con tabla reproducible de tarifas/medidores, fecha/URL oficial y fórmula:
- API/worker por separado, activo/idle con CPU/memoria/tiempo y grants **compartidos** por suscripción, sin descontar dos veces la cuota; worker no se presume siempre idle. Jobs activos y demora de5min explícita si se eligen.
- Distinguir cargo de gestión de perfiles Dedicated/funciones facturables de un entorno de soloConsumption sin endpointsprivados/mantenimiento planificado. No presupuestar un medidor irrelevante como cargo seguro ni descartarlo solo por ausencia en captura. Anclar decisión a documentación/plantilla/oferta.
- Incluir ACR, Files/capacidad/operaciones/copias, logs/retención y salida de red; ítems no determinables con valores/supuestos conservadores y rango, sin inventar certeza. Costo hasta23/10 y mensual si se mantiene encendido; propuesta de apagado/archivo posterior.
- Región permitida y cuotas reales; estrategia de egreso hacia Atlas y proxy confiable. IPs por recurso/API documentada, pueden cambiar; no inventar IP estática ni activar acceso global/serviciosNAT facturables sin decisión separada. Cliente de Atlas mínimo y credencial rotada por canal privado se completarán en despliegue.
- Validar Bicep actualizado y que monta el paquete runtime/archivos persistentes y recursos probados. Secretos por canales seguros, no argumentos/logs versionados; auth deAzure no equivale a despliegue.

Al terminar, dejar **una propuesta principal concreta**: recursos/región/modo/recursosprobados, costo estimado y máximo solicitado de créditos hasta23/10, condición de parada y política después del curso. Presupuesto y alertas no cortan gasto: explicar controles operativos reales. No pedir al usuario aprobar una lista de supuestos sin cerrar; señalar solo verificaciones que de verdad requieren crear el primer recurso y cómo se acota su riesgo/costo.

## 5. Evidencia y cierre

Regresiones R12/R13/referencia portable, generación en stack y pruebas afectadas; no suite completa por rutina. Evidencias privadas `artifacts/private/t11b/`, reporte `docs/T11B_REPORTE.md`, acta integral y plan corregido. ESTADO/TRASPASO/BACKLOG/HISTORIAL y tareas del gestor actualizados honestamente; commit local con exclusiones.

Detener para revisión antes del paso facturable/transferencia. T12 científica no cambia, nada de entrenamiento por buscar mejores cifras. Todavía no declarar publicación HTTPS ni aceptaciónhumana; T13rendimiento/aceptación y T14/T15informe/manual/video siguen después del despliegue. No repetir encargos anteriores para cerrar esta unidad.
