# Corrección T08: precisión, límite de acceso y presentación

Lee RETOMAR_CLAUDE.md, ESTADO/TRASPASO y docs/REVISION_CODEX_07.md. T08 al commit 960638d tiene una base útil, pero no está aceptado por completo. **Este encargo cierra R05–R06 antes de T10**. No reentrenar T06/T07, no abrir agosto, no modificar la selección congelada, no contratar infraestructura. Un ejecutor principal; se permiten agentes de ámbitos separados si ayudan.

## 1. R05: señales exactas y publicación corregida

Reproducir primero los casos documentados con una prueba que falle antes de corregir. El CSV T07 tiene diez cifras significativas y no sirve como fuente de media operativa antes de techo. Los 3347 productos con snapshot tienen 28 observaciones útiles al 10/07; la auditoría encontró 225 objetivos y 118 pedidos inflados. Ejemplo SKU 12040025: suma28=12, días=28, objetivo9, posición9, pedido0; SKU 12010025: suma28=4, objetivo3, posición1, pedido2.

Derivar la media del SKU con historia aprobada <=10/07, ceros válidos y máscaras existentes. Conservar suma exacta de unidades y días útiles, fingerprint del origen y ventana usada. Calcular forecast14 y seguridad con precisión completa; aplicar el techo de la regla declarada sin truncar el CSV ni un epsilon inventado. Puede usarse Decimal/Fraction con conversión explícita para persistir/serializar. En otros orígenes no asumir siempre denominador28 ni cantidades enteras sin validar el contrato. Los decimales de presentación no deben alimentar el cálculo.

Conservar pronósticos/backtests históricos T07 como evidencia original. La recomendación nueva puede usar el baseline recalculado exactamente al mismo origen; documentar la diferencia de precisión respecto al CSV histórico. No reescribir métricas/artefactos de T07 ni reentrenar modelos. Mantener snapshot del 10/07, tránsito hasta esa fecha, catálogo y SKU sin snapshot como null. Verificar coherencia categoría/SKU sin usar futuro.

Versionar publicador/adaptación y señales exactas en la identidad/fingerprint. Mismos datos+código/config/versión generan la misma identidad al reintentar; corrección de algoritmo cambia identidad. La salida actual no se corrige devolviendo already_published ni alterando hijos de una completed. Publicar una corrida histórica corregida nueva mediante staging, validar, promover y conservar anterior. Registrar superseded_by/quality_issue u otra señal equivalente y evitar que consultas directas a recomendaciones de la corrida anterior las presenten como válidas; UI explica que fueron sustituidas por una corrección de precisión. No borrar ventas, usuarios, bases antiguas ni evidencia.

Auditoría independiente de las 3347 recomendaciones contra sumas/días obtenidos de datos aprobados: cero diferencias de objetivo, posición y pedido. No calcular el valor esperado con el mismo helper probado. Confirmar y explicar nuevos conteos (referencia auditada 582 sugerencias positivas/2655 unidades frente a640/2773 anteriores); si difieren, investigar y mostrar la causa, no ajustar el test a la salida. Producto sin snapshot sigue sin cantidad recomendada.

## 2. Vincular fuentes y métricas publicadas

Antes de combinar catálogo/señal con G4, exigir coincidencia del fingerprint/fuentes con el manifiesto de la corrida aceptada; fallar antes de escribir si cambian. Es una corrida histórica ligada a fuentes inmutables, no una reestimación automática con un catálogo posterior.

Anclar checksums de manifiesto y métricas a una referencia versionada aprobada (5790103/T07 y su contenido normalizado), verificando antes de publicar. Calcular un hash nuevo del archivo alterado no equivale a verificarlo. Actualizar config de publicación/contrato con versión del adaptador y señales exactas. Probar métricas alteradas, catálogo/fuentes alterados y mismo origen con distintos inputs. El código experimental se sigue verificando contra su commit, no contra árbol actual de API.

## 3. R06: confianza explícita de proxy y login

En inicio local Uvicorn debe ignorar cabeceras de proxy proporcionadas por el cliente: configurar --no-proxy-headers u opción equivalente. Revisar todos los puntos de inicio/guía para coherencia. No asumir que request.client conserva la IP TCP cuando hay middleware de proxy.

Prueba de integración de la cadena real (Uvicorn + proxy Angular cuando corresponda): varios fallos del mismo usuario/conexión variando X-Forwarded-For deben seguir alcanzando el límite y devolver 429. Comparar con valores correctos y no afectar CSRF/roles. Un TestClient directo de FastAPI sin el middleware no cubre este defecto. No registrar contraseñas/cookies/tokens en evidencia.

Dejar documentado el contrato de proxy confiable para despliegue; no confiar en cualquier origen ni en cabeceras externas sin saneamiento. Las reservas/conteos concurrentes del rate limit siguen siendo una condición antes de exposición pública; si el ajuste es pequeño y verificable puede resolverse ahora con operación atómica y prueba concurrente. Si queda pendiente, declararlo de forma explícita para T10/T11, sin afirmar resistencia a ráfagas.

## 4. Presentación de la demostración local

La evidencia anterior muestra comparación como árbol completo de casi 30000 px de alto y cantidades como 4.9999999994. Preparar una interfaz legible sin cambiar algoritmos ni requerir un rediseño costoso:

- Comparación abre con escenario principal y tres políticas: servicio como porcentaje, faltantes/unidades, stock medio y compras PEN, con diferencias frente a promedio_28; selector de L/S y cohorte muestra los nueve escenarios sin volcar todo simultáneamente.
- Predictiva permite elegir nivel/cohorte/horizonte/fold y muestra métodos con WAPE/MAE/RMSE/sesgo/cobertura y unidades. Rotular WAPE razón o porcentaje consistentemente; MAPE solo positivos y R² no evaluable donde corresponda. Conservar todos los resultados mediante filtros/detalles, sin ocultar los desfavorables.
- Números de pantalla con formato: unidades enteras para stock/pedido, medias y pronósticos con precisión visual razonable, moneda dos decimales; valor exacto preservado en datos/cálculo. Una explicación principal del pedido, sin duplicarla con un bloque técnico completo.
- IDs internos, JSON, checksums y escenarios técnicos bajo detalles plegables; procedencia simulada, fecha histórica y límites científicos visibles en lenguaje sencillo. No ocultar que RF no ganó ni que más servicio usó más stock.
- Mejorar espaciado, cabeceras, foco/teclado y tablas adaptables; una tipografía y estilos globales coherentes. Mantener carga/sin datos/error/sesión vencida y no usar mocks como fallback. No instalar frameworks o plugins innecesarios.

Capturas de comparación y pedido corregidos en artifacts/private/t08r/, junto con un flujo navegador de login→corrida nueva→casos de pedido→comparación filtrada→logout. Comprobar vista de la corrida antigua sustituida y fallo de API. Usar cuentas locales existentes por mecanismo seguro, sin imprimir credenciales. No confundir esta comprobación con aceptación humana final.

## 5. Pruebas, cierre y siguiente paso

Probar fracciones 1/7 y 3/7 que producen objetivos enteros, sumas próximas a enteros por debajo/encima, cero, ventana con ausentes y SKU sin snapshot. Añadir los casos independientes exactos anteriores. Verificar reintento idempotente de nueva versión, preservación de antigua, fallo de publicación conserva última válida, y rechazos de señales/métricas no concordantes. Mantener regresiones auth/API existentes.

Ejecutar pruebas afectadas y build/tests frontend, más E2E de regresión pertinente; no repetir la suite con entrenamiento real de 509 s ni T07 completo salvo nueva causa documentada. Auditoría real de todas las recomendaciones no exige reentrenar. Guardar logs/auditoría extensa privados y versionar resumen T08R con commit, run_id nuevo, diferencias corregidas, pruebas ejecutadas, evidencia, límites y siguientes pendientes.

Actualizar ESTADO/TRASPASO/BACKLOG/HISTORIAL y guías/contrato. El resumen vigente debe sustituir las frases obsoletas que aún dicen solo healthcheck, mocks sin auth o congelación pendiente: describir código comprobado y defectos actuales sin reescribir historia. Revisar exclusiones y comprometer cambios locales.

Detener esta entrega para revisión de Codex tras las correcciones, sin empezar T10 ni abrir agosto. Después de aceptarla se emitirá carga/batch y ejecución final en el orden adecuado. El despliegue sigue pendiente de accesos/presupuesto y las recomendaciones siguen siendo hipotéticas con inventario simulado.
