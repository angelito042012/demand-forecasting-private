# Revisión Codex15: R15/R16 aceptados localmente, demo disponible

Fecha: 17/10/2026 America/Lima. Entrega revisada: 8412ca0 y 747dcfe. Sin cambios de producto, acceso autenticado, lectura de credenciales, Docker, reinicios ni consultas Azure/Atlas por el revisor.

## Resultado

R15 y R16 cerrados para el procedimiento local revisado. La aplicación local está disponible para que Rogelio ejecute el guion. Aceptación humana A14, publicación/HTTPS externo/Atlas y pruebas de nube A13 siguen pendientes. No crear otra ronda de correcciones por rutina ni repetir modelos/T12, suites amplias o preflight ya concluidos.

## Evidencia propia

- `pytest tests/ops/test_t13a_perf.py`: 9 aprobadas, 0 omitidas, 1,24 s. Ruff de medidor, demo_local y pruebas aprobado. Evidencia privada: `artifacts/private/codex_review15_tests.xml/.log`.
- Revisión de `scripts/t13a_perf.py`: percentil nearest-rank, estados/excepciones contabilizados, completitud por sesión, salida no exitosa de tandas incompletas, cierre de clientes y timeout de arranque; TLS verificado salvo opción local explícita.
- Recalculadas las seis combinaciones consulta/concurrencia desde `perf_r15_muestras.json`: conteos20/100 esperados, sin errores y todos los p95 publicados coinciden al redondear. Mayor p95=298,56ms (publicado298,6ms). La latencia máxima>2s se mantiene declarada; no es una garantía de máximo ni de nube.
- Consulta HTTP anónima propia: raíz200, health200/statusok, un enlace de estilos normal sin media=print/onload, script-src self conservado, HSTS presente. Se usó omisión de validación de certificado únicamente contra localhost autofirmado. No hubo login ni lectura de contraseñas.
- Código/evidencia: `artifacts/private/codex_review15_live.py/.json`. La demo quedó activa sin mutaciones.
- Revisión R16: compose `df-demo`, URI/base comunes desde estado privado para API/worker y create-user dentro de API, restauración en base temporal y parada conservando volúmenes. Status compara base sin imprimir URI. La verificación autenticada y de igualdad de bases fue ejecutada por Claude; no se repitió por Codex. `status --writers` informa jobs/staging visibles, no prueba por sí solo ausencia de todo escritor; el mantenimiento aún exige detener realmente API/worker/scheduler.

## Plan listo para una decisión humana

El paquete vigente de `docs/T11_PLAN_DESPLIEGUE.md` enumera acciones1–7 y permite aprobarlas juntas con límites. Registro Microsoft.App/cuota0/1 ya cerrados; no volver a autenticarse solo para comprobar lo mismo.

Autorización todavía ausente: recursos del grupo nuevo rg-demand-forecasting-pub/BrazilSouth, proveedores imprescindibles, imagen sin datos/secretos, referencia privada AzureFiles, basepub~214MB haciaAtlasFree, apps y pruebas. Techo operativo propuestoUS$20 del crédito hasta23/10 e intervención aUS$12/proyección/medidor inesperado; no es corte personalizado de Azure. Sin bolsillo/pago por uso, NAT ni apertura globalAtlas por defecto. Política posterior23/10 pendiente de decisión, no asumir gasto mensual ni eliminación de recursos sin autorización.

No se certifica costo final por una estimación: recalcular días antes de crear y mantener margen por facturación demorada. Las cifras4d del paquete son escenarios, no afirmación de que falten exactamente4d; la fecha vigente es23/10/2026 Lima.

## Continuación

Rogelio puede abrir https://localhost:8443 y ejecutar el guion de aceptación con sus credenciales privadas. Registrar únicamente resultados reales. `ETAPA_15_CLAUDE.md` prepara la publicación condicionada a la autorización explícita; si no hay autorización, continuar solo apoyo a aceptación local y cierre documental permitido. No detener df-demo ni bases originales para publicar.
