# Revisión Codex14: T13A y borradores T14A

Fecha: 17/10/2026 America/Lima; entrega 42233a6. La fecha de algunos reportes dice 18/10 aunque las marcas Git y UTC corresponden al 17 en Lima; usar la fecha/hora real de cada evidencia al consolidar, sin reescribir sellos.

## Dictamen

La entrega acredita un ensayo local útil, 22 resultados de navegador y borradores científicos honestos. No acredita HTTPS/Atlas/Azure ni aceptación humana. El protocolo y el manual requieren dos correcciones antes de reutilizarlos como procedimiento de aceptación/publicación. No hay motivo para repetir T06/T07/T12 ni la suite completa.

## Evidencia revisada y comprobación propia

- `artifacts/private/t13a/perf.json`: tres consultas, 20 medidas con una sesión/100 con cinco por consulta, cero errores de estado HTTP registrados, calentamiento y cold start separados, límite contenedor 0,5 CPU/1 GiB. La cifra rotulada p95 más alta es 373 ms. La evidencia conserva máximos de 2429,7 ms en pronósticos, 2068,2 en recomendaciones y 2052 en detalle: no confundir p95 con latencia máxima.
- `e2e_t13a_resultado.json`: 22 resultados, cero fallas; evidencia previa conserva cuatro fallas. CSS fuente usa inlineCritical=false y estilos responsivos sin relajar CSP. El compilado dist del host puede ser anterior: el artefacto de publicación debe verificarse desde la imagen reconstruida, no inferirse del directorio del host.
- El check de idempotencia del programa privado de navegador usa una condición incondicional; es una observación, no una regresión estricta. T11B aporta la evidencia fuerte de idempotencia ya aceptada; no es necesario repetirla por rutina.
- Se revisaron matriz, informe, manuales y guiones: WAPE no se confunde con acierto, RF no gana el hallazgo principal, inventario se declara simulado y aceptación/despliegue permanecen pendientes.
- Prueba propia sintética, sin red/DB/modelos: `artifacts/private/codex_review14_probe.py/.json` demuestra los dos defectos de R15 abajo. Ruff del medidor aprobado. No se repitieron Docker, rendimiento real, navegador ni experimentos; 22/22 y cifras locales se atribuyen a Claude.

## R15: medidor debe detectar fallos y nombrar correctamente el percentil

`scripts/t13a_perf.py::pct/run_level`:

1. La fórmula round(q*n+0.5)-1 devuelve la observación 20 para p95/n20 y la 96 para n100. La definición nearest-rank que dice usar el texto requiere 19 y 95. Los valores actuales son conservadores, pero no corresponden al percentil documentado. No hay muestras crudas guardadas para recalcular el valor exacto de esa tanda.
2. Una excepción HTTP dentro de un hilo no se suma a errores ni se propaga al integrador. Reproducido con un cliente sintético fallido y otro sano: esperaba 40 medidas, obtiene 20, reporta errores=0 y retorna un resultado normal. La tanda real sí tiene todas las medidas; este defecto no prueba fallo en ella, pero puede falsear una futura prueba de nube.

Corregir fórmula/definición, propagación/contabilización de errores, exigencia de muestras por sesión, recursos cerrados incluso tras fallo y timeout total de arranque. Guardar muestras privadas y resumen explícito de completitud. `verify=False` es solo para TLS autofirmado local; la prueba de nube debe verificar certificado de forma predeterminada. Regresiones sintéticas de percentil, fallo de un hilo, respuesta no200, cero muestras y timeout. No reejecutar todo el ensayo: conservar cifras anteriores como cota conservadora y limitación, o repetir solo el pequeño ensayo local corregido si se necesita un p95 exacto.

## R16: guion de aceptación debe preparar y usar la misma base en todos los procesos

`docs/MANUAL_OPERACION.md` §2 parte de `.env.example`/desarrollo v2. El guion exige ver T12, que solo está en pub o su copia restaurada. El worker/scheduler/publish_run leen variables de entorno (default v2), mientras API/CLI de usuarios admiten `.env`; cambiar solo `.env` no garantiza misma base. Así puede mostrarse una base y procesarse otra cola, o no aparecer la evaluación final.

Preparar una demostración sobre copia temporal restaurada y documentar URI/base comunes para API, worker y creación de usuarios; comprobación efectiva sin imprimir URI. No republicar histórica por rutina ni modificar punteros/datos originales. Guion debe identificar URL, versión e identificador de base de ensayo realmente activos.

Mantenimiento: `stop-local.ps1` solo detiene procesos registrados PowerShell, no los contenedores. Separar el procedimiento PowerShell del de compose y comprobar escritores antes de `--maintenance-confirmed`; no recomendar `down -v` como parada habitual. Retirada la sospecha de proyecto compose diferente: el archivo declara name: df-t11a, por lo que omitir -p no es por sí mismo un defecto actual.

## Ajustes editoriales acotados

- MANUAL_USUARIO: las generadas pueden tener snapshot válido propio; 10/07 es la fecha de la histórica predeterminada, no de todas. No llamar histórica la única con recomendaciones verificadas.
- INFORME_FINAL_BORRADOR: MAPE acum14 excluye entidades con total observado 14 días igual a cero; no «días con reales >0». Cobertura SKU0,485 es de entidades; cobertura diaria0,097 es otro denominador.
- MATRIZ_CIERRE: 11957 observaciones SKU-fold T07 no son 11957 SKU únicos. Actualizar referencias T13A en curso/por registrar sin convertirlas en nube/humano aprobados.
- Actualizar commit/versión de guion y manuales y autoridad AGENTS/CLAUDE/RETOMAR al estado vigente; evitar volver a pedir R12–R14 por leer instrucciones antiguas.

## Plan de nube revisado

La propuesta es concreta: un grupo nuevo, solo Consumption, API y worker0,5CPU/1GiB/minmax1, ACRBasic, Files2shares, LogAnalyticsconcap, identidadAcrPull; AtlasFree existente. US$4–17 es estimación del modelo de seis días; US$20 de crédito es techo operativo propuesto, no autorizado ni un corte automático de Azure. Se excluyen bolsillo/pago por uso/servicios adicionales. Los cinco proveedores restantes no están autorizados todavía; tampoco transferencias.

Fuentes oficiales consultadas en esta revisión:

- https://learn.microsoft.com/en-us/azure/container-apps/billing : franquicias por suscripción, condiciones idle, jobs activos; gestión con Dedicated/perfiles y funciones especiales. No presentar la existencia de un medidor de precios como prueba de que el Consumption propuesto lo cobra.
- https://learn.microsoft.com/en-us/azure/cost-management-billing/costs/understand-cost-mgt-data : datos con demora según oferta/servicio y ajustes posteriores; una consulta sin cargo aún no demuestra costo cero ni techo20. Para esta oferta de estudiante no se confirmó una demora exacta universal; no atribuirle automáticamente las72h de pago por uso.
- https://www.mongodb.com/docs/atlas/reference/free-shared-limitations/ : límites y restricciones Free actuales. La documentación actual sí permite backups opcionales diarios con hasta cuatro snapshots; no sustituye la copia integral propia ya verificada.

Preparar una sola autorización humana que pueda cubrir el conjunto de pasos de publicación enumerados y sus límites, sin solicitar de nuevo permiso por cada comando comprendido. Antes de pedirla completar R15/R16 y dejar plan/evidencia listos. No activar recursos ni transferir datos hasta autorización explícita. La política posterior al23/10 debe decidirse; no suponer desmontaje o gasto mensual adicional.
