# Revisión T08R: R05 y R06 cerrados para demostración local

17/10/2026, Lima. Entrega revisada 80117c0 y antecedentes ac8ee8b, 7fcc99c y e2cae1f. **T08R aceptado; R05 y R06 cerrados para el alcance local. T08 y lectura integrada T09 aceptados con los límites declarados.** No equivale a despliegue o aceptación humana. Próximo encargo ETAPA_08_CLAUDE.md (T10).

## Evidencia independiente selectiva

Codex ejecutó test_exactness.py, test_r05_reproduccion.py y test_proxy_headers_chain.py: **31 aprobadas, un aviso, 31,62 s**. Incluyen ventana/máscaras/ceros/historia corta, fracciones con objetivo entero, identidad/publicación/sustitución, referencias alteradas y servidor Uvicorn real con/control sin proxy headers. No se reentrenó ni se ejecutó la suite costosa T07. JUnit privado artifacts/private/codex_review08_tests.xml.

Ruff en el alcance revisado identifica únicamente dos diagnósticos de estilo en scripts/audit_recommendations.py: noqa SIM113 colocado en línea incorrecta (RUF100) y contador n_ok que puede eliminarse o reemplazarse por enumerate. No afectan el cálculo. Corregir en la preparación T10; no se presenta ruff de esta revisión como completamente limpio.

Auditoría adicional de Codex, en lectura de la base real: agregación directa de ventas de fuentes G4 entre 13/06 y 10/07, techo entero independiente, snapshot y tránsito del NPZ con checksum verificado. Las **3347 recomendaciones** de hist-20260710-4ea348836e35 coinciden en stock, tránsito, suma/días, objetivo, posición y pedido: **0 diferencias, 582 sugerencias positivas, 2655 unidades**. Los 300 sin snapshot tienen cantidades nulas. Corrida nueva completed/activa; anterior hist-20260710-52b01cd999dd superseded, con enlace a nueva y sus 3647 hijos conservados. Hash de selección congelada verificado. Resumen privado artifacts/private/codex_review08_audit.json. No se modificó la base real ni se leyó agosto.

## Interpretación de correcciones

La recomendación usa señales históricas exactas con origen/fingerprint y aritmética racional; los pronósticos T07 con diez cifras se conservan como evidencia histórica, sin volver a usarlos como entrada del techo operativo. La nueva identidad incluye versión del publicador y señales, y las referencias de métricas/manifiesto se anclan al commit aprobado. Las regresiones prueban los dos casos encontrados en la revisión anterior y el fallo antes de publicar ante fuentes incoherentes.

El inicio local incluye --no-proxy-headers y las pruebas del servidor real comprueban que variar XFF no cambia las claves efectivas del límite. Eso resuelve R06 en la demostración local; un proxy de despliegue necesita configuración de confianza/saneamiento explícita.

Codex inspeccionó capturas de recomendación corregida y comparación: explicación única, números formateados, filtros, tabla principal y metadatos plegados. Leyó el registro E2E de Claude (16/16), sin repetir navegador. Suite 254/3 omitidas y frontend 79/build son resultados de Claude, distintos de los 31 tests del revisor. La interfaz es más legible; no se afirma evaluación formal de accesibilidad o aceptación por usuario.

## Pendientes que pasan a T10

El límite de intentos sigue siendo count-then-insert y el publicador no renueva/fencea su lease. Antes de worker/timer concurrentes se requieren reserva atómica, propiedad por intento, pruebas de toma de control y garantías contra limpieza/publicación de un trabajador obsoleto. Son alcance nuevo, no una reapertura de R05/R06.

La pantalla de comparación llama al conjunto «hasta 10/07» aunque es el origen de la corrida G4: sus objetivos llegan al 31/07 y el backtest/simulación resumidos cubren ventanas propias hasta 31/07. Ajustar esos rótulos al integrar T10; distinguir origen, fechas objetivo y período de evaluación sin alterar métricas.

T10 implementará carga web, cola durable, worker, generación del baseline seleccionado y timer local comprobable. Agosto sigue reservado y la congelación no cambia. Corrida histórica y simulación continúan etiquetadas; ninguna sugerencia autoriza compras. Despliegue/HTTPS/restauración, evaluación final y aceptación/informe permanecen pendientes. Se solicitó información de cuentas/presupuesto para planificar la nube; no se autoriza gasto por ausencia de respuesta.
