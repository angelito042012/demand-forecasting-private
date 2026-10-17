# Revisión T08: correcciones antes de aceptación completa

17/10/2026, Lima. Entrega 960638d y antecedentes desde d59703b. **T08/lectura T09 quedan parcialmente verificados, con aceptación final pendiente de R05–R06.** No repetir T06/T07 ni abrir agosto. Siguiente: ETAPA_07_CLAUDE.md (corrección acotada T08).

## Comprobaciones y alcance

Codex ejecutó tests/backend/test_auth_api.py, test_auth_cli.py, test_data_api.py, tests/publish/test_publisher.py y tests/sim/test_engine.py: **118 aprobadas, un aviso, 91,02 s**; ruff correcto. Son pruebas seleccionadas, no repetición de la suite integral de 509 s. El log de Claude registra 226 aprobadas y un aviso; su evidencia E2E registra 24/24 y frontend 42/build correcto. Codex leyó esos registros y dos capturas guardadas; no volvió a ejecutar Chrome ni el entrenamiento. Dos revisores de solo lectura examinaron autenticación y publicación.

La auditoría adicional de Codex leyó las fuentes aprobadas hasta 10/07 y verificó que su fingerprint coincide hoy con G4. La configuración congelada conserva su hash y T07_METRICAS.json coincide con el commit aceptado 5790103. No hay evidencia actual de mezcla de catálogo/datos. Se consultó la base real solo para lectura; las pruebas escribieron exclusivamente en bases temporales aisladas. Resumen privado artifacts/private/codex_review07_audit.json; JUnit artifacts/private/codex_review07_tests.xml.

Los 118 tests pasan pero no detectan los siguientes casos. La recomendación requiere una referencia matemática independiente del mismo helper usado para construirla.

## R05 [P2]: precisión reducida cambia pedidos publicados

pipeline/publish/builders.py, build_recommendations (líneas 148–149) usa pred_promedio_28 del CSV de T07, guardado con diez cifras significativas. recompute_recommendation aplica ceil después de redondear a nueve decimales. Esa combinación **no** elimina el error: no es únicamente un riesgo hipotético como dice T08_REPORTE.

La lectura exacta de unidades observadas en 13/06–10/07 confirma 28 días útiles para los 3347 SKU con snapshot. Frente al cálculo exacto, hay **225 objetivos y 118 pedidos distintos**, todos estos pedidos inflados en una unidad. Revisor adicional confirmó totales de sugerencias: 640 con pedido positivo/2773 unidades frente a 582/2655 correctas. Ejemplo SKU 12040025: 12 unidades/28 días; objetivo exacto (14+7)*12/28=9, posición9, pedido0. Publicado: objetivo10/pedido1. SKU 12010025: 4/28, objetivo3 frente a4 y pedido2 frente a3.

Recuperar media y pronóstico operativo de historia aprobada <=origen con precisión suficiente y trazabilidad (numerador/días útiles); no inferir fracciones redondeadas del CSV ni aumentar arbitrariamente un epsilon. No modificar artefactos T07 para ocultar el problema. Cambiar la versión/identidad del publicador: corregir solo el builder deja la corrida antigua porque la idempotencia devuelve already_published. Publicar una corrida corregida nueva, validar todos los SKU, promoverla y marcar claramente la anterior como sustituida por error de recomendaciones. La corrida actual hist-20260710-52b01cd999dd no debe tratarse como recomendación validada.

## R06 [P2]: cabeceras de proxy eluden las claves del límite de login

scripts/start-local.ps1 lanza Uvicorn sin desactivar proxy_headers. La versión instalada los activa por defecto y confía en loopback. backend/app/routers/auth.py:49–50 y 75–78 usa request.client.host suponiendo que no acepta X-Forwarded-For, pero Uvicorn ya reescribió ese cliente.

Codex reprodujo dinámicamente el middleware instalado, sin servidor ni DB: la misma conexión 127.0.0.1 con XFF 198.51.100.10 y 198.51.100.11 llega como dos clientes diferentes. Por tanto ambas claves del límite basadas en IP son manipulables. Para demo local, --no-proxy-headers y prueba por la cadena real HTTP, no solo TestClient que omite ese middleware. Para despliegue futuro: proxy confiable y saneamiento explícitos. No hay hallazgo de omisión de CSRF, exposición de tokens/contraseñas ni escalada de rol en las rutas actuales.

## Otros ajustes antes de ampliar alcance

- Publicación: anclar hashes de métricas/manifiesto a una referencia aprobada y comparar fingerprint de catálogo/fuentes con G4 antes de combinar resultados. Hoy coinciden, pero el publicador solo calcula hash del archivo actual y permitiría mezclar futuras fuentes cambiadas. El hash del publicador/versión de adaptación debe formar parte de la identidad, sin inventar una corrida nueva en cada reintento.
- UI: comparación usa un árbol genérico completo que produjo una captura de 29829 píxeles de alto; recomendación muestra 4.9999999994 y metadatos/cálculo duplicado. Es evidencia de flujo técnico, no aceptación de facilidad de uso. Mostrar resumen principal y tablas filtradas con formatos numéricos, detalles técnicos plegados y reglas científicas visibles.
- Concurrencia: límites de login count-then-insert y lease de publicación sin fencing/renovación requieren endurecimiento/pruebas antes de concurrencia pública, worker/timer T10 o despliegue. No se presenta como daño actual demostrado en CLI única.

## Congelación y próximos hitos

La elección promedio_28 y el protocolo final siguen siendo razonables y no se modifican para resolver precisión/proxy/UI. La congelación documental conserva su hash; el test no está autorizado aún. Corregir T08 primero con pruebas de regresión independientes y evidencia breve. Después: T10 (carga/batch), ejecución final bajo congelación, despliegue/restauración e informe. No declarar terminada la aplicación ni la aceptación humana por pasar pruebas técnicas.
