# Revisión T11A: integración local verificada; tres cierres antes de publicar

17/10/2026, Lima. Entrega **989fa6c** y antecedentes71656c2/e1905cb/813f3f3/be3bf2e. La lista de tareas de Claude está cerrada; eso confirma entrega, no sustituye revisión técnica. La integración local del paquete final, la separación de corridas y la recuperación de Mongo son aceptables con sus evidencias. **T11 real todavía no se inicia**: cerrar R12–R14 y el preflight/costo en `ETAPA_12_CLAUDE.md` (T11B).

## Verificación propia

- **83 pruebas aprobadas, 0 omitidas, 69,61 s, dos avisos de deprecación**: estado T12, publicador final, copia/restauración, API final y producción. JUnit/log: `artifacts/private/codex_review12_tests.xml/.log`. Ruff selectivo limpio. No se repitió la suite511 ni el navegador/Docker completo ni T06/T07/T12 real.
- Revisión independiente de publicador/archivo y de configuración/proxy/producción. El publicador final usa artefactos validados y protocolo T10R, no reentrena ni consulta agosto de Mongo; mantiene histórica activa y final separada. API/UI de fechas y recomendaciones no disponibles coherentes. Configuración y cadena local de proxy/cookies son consistentes con los tests.
- Reproducción propia R12 solo con estado/reporte sintéticos y lectura del backup: `artifacts/private/codex_review12_repro.py/.json`. No se tocó el paquete final, v1/v2 ni configuración de nube.
- Restauración real propia del export existente en `df_restore_review12_<uuid>`: **ok=true, 0 problemas, 18,98 s, 329131 objetos**, datos190,566MB +índices22,902MB =**213,469MB**. Base temporal eliminada al terminar; originales intactos. Evidencia `artifacts/private/codex_review12_restore.json`. Valida la parte Mongo, no la recuperación de archivos privados de R13.
- Frontend127/build, Chrome20/20, imagen991MB y smokeDocker29/29 son evidencia del ejecutor inspeccionada, distinta de las83 pruebas propias. No se infiere de ellas que la generación de corridas en contenedor esté verificada: el reporte la declara pendiente.

## R12 — P2: excepción al cierre del manifiesto deja completa=true

`pipeline/final/report.py:182–188`: después del try, `store._end('reporte')` declara éxito y estado completo. Las lecturas/reconstrucción/escritura del manifiesto definitivo ocurren después y fuera de control de errores. Inyectar OSError en ese cierre produce excepción con `reporte=completa`, `completa=true` y el manifiesto previo todavía `reporte=en_curso`. Reproducción confirmada. No altera las predicciones existentes, pero incumple el cierre fiel exigido por R11.

Controlar todo el cierre y registrar fallo aunque suceda después del primer reporte/_end; no emitir un manifiesto válido con estado incoherente. Regresión de fallos tardíos y recuperación sin prepare/evaluate. Conservar hashes y procedencia; no repetir el experimento.

## R13 — P2: faltan copia y restauración de los artefactos privados

`scripts/backup_restore.py:37–43` solo enumera/hasea artefactos, expresamente no los copia. `archive.verify_export_files` y `restore_db` solo validan/restauran colecciones e índices. Backup real: **18 archivos privados listados, 0 presentes dentro del respaldo; verificación Mongo sin problemas**. El acta lo declara, pero el encargo exigía recuperación de modelos/artefactos con hashes. La copia de Mongo por sí sola no recupera NPZ, modelos y evidencias si se pierde su carpeta original.

Añadir bundle privado separado o extensión del backup, restaurar en carpeta vacía distinta y comprobar todos sus hashes; probar ausencia/alteración. No borrar originales para demostrar el caso ni regenerar modelos/evaluación. Distinguir explícitamente `mongo_ok` y `artefactos_ok`, y no anunciar recuperación integral hasta verificar ambos.

## R14 — preparación del contenedor: generación y referencias pendientes

La imagen actual no contiene artefactos privados, Git ni repositorio. Eso protege los datos, pero `pipeline/publish/source.py::_git_show/verify_reference/verify_code/verify_config` necesita commits Git para validar T07. Montar solo modelos/NPZ no basta. `_load_reference` absorbe el fallo y puede publicar baseline sin comparador/snapshot, por lo que no se debe asumir paridad de recomendaciones con la demostración local.

Preparar un paquete privado de referencia con anclajes aprobados verificables sin Git en runtime, montado de solo lectura, o una solución equivalente que conserve los checksums aprobados. No introducir .git, secretos ni datos en una imagen pública ni desactivar validación para que pase. Probar generación completa por HTTP→cola→worker dentro del stack real con límite de recursos propuesto, datos aislados/restaurados y origen10/07, idempotencia/puntero/recomendaciones exactas. Medir memoria/tiempo; ajustar infraestructura/costo si1GiB no alcanza. No reentrenar T07 ni ejecutar T12.

## Restauración y consistencia

Las pruebas y export/restauración de Mongo son válidas para escritores realmente detenidos. Ausencia de staging y conteos estables no garantizan snapshot ante mutaciones del mismo conteo; el procedimiento debe imponer la ventana de mantenimiento. Archivar una histórica sustituyendo solo sus hijos rompería counts/referencias si conserva su run como legible: es propuesta no ejecutada, no política ya implementada. Conservar ambos históricos por ahora; el tamaño medido de publicación cabe con margen.

## Plan de costo y acceso: todavía no pedir aprobación de un precio cerrado

Los rangos US$5–7/US$20 hasta23/10 y US$28–30/mes son estimaciones con conceptos sin verificar, no cotización final. Antes de aprobar recursos, comprobar suscripción/regiones/cuotas y hacer cálculo reproducible, con free grants compartidos por suscripción (no duplicarlos para API/worker), CPU/memoria activos/idle y supuestos medidos. No presumir que el worker que sondea Mongo siempre cumple condiciones de idle.

Microsoft documenta que idle exige, entre otras condiciones, CPU<0,01vCPU y red<1000bytes/s; los jobs se cobran activos. Los perfiles Dedicated y funciones como endpoints privados/mantenimiento planificado pueden generar cargo de gestión; no deben confundirse con un entorno de solo perfil Consumption sin esas funciones. Fuente: [facturación oficial](https://learn.microsoft.com/en-us/azure/container-apps/billing), consultada17/10. Las IP de egreso pueden cambiar: [red oficial](https://learn.microsoft.com/en-us/azure/container-apps/networking). El almacenamiento efímero no recupera archivos tras reemplazar una réplica: [almacenamiento oficial](https://learn.microsoft.com/en-us/azure/container-apps/storage-mounts).

T11B permite preparar autenticación interactiva y **consultas de solo lectura** con la cuenta del usuario para cerrar esos datos, sin pedir contraseñas/tokens por chat, sin crear roles/grupos/recursos ni transferir ventas. Si falta el inicio de sesión, pedir solo ese paso y avanzar en R12–R14; no volver a pedir alta de cuentas. La aprobación del gasto será sobre el plan corregido, con límite de crédito y apagado explícitos; no hay presupuesto de bolsillo autorizado.

## Fase del proyecto

Datos/experimentos y evaluación final están hechos; aplicación e integración final funcionan localmente. Estamos en **cierre técnico previo al despliegue (T11B)**. Restan publicación HTTPS/conexión Atlas y restauración del entorno publicado, rendimiento y aceptación humana T13, informe/manual/video T14 y entrega T15 antes23/10. No prometer porcentaje de avance ni fecha anticipada garantizada; no rehacer modelos para cerrar despliegue.
