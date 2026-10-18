# Etapa17: terminar UX01 con recuperación clara y Evaluación breve

Leer REVISION_CODEX_16.md, docs/UX01_BRIEF.md y estado vigente. Conservar el rediseño implementado: no reiniciar ni cambiar paleta/framework. Fecha23/10/2026 Lima. Publicación sigue sin autorizar. Los cálculos y el nuevo filtro de lectura fueron revisados; no repetir modelos, T12, Azure ni suites grandes.

## 1. R17

Corregir el bucle effect/ensure de AnalysisBar y RunsStore. Carga inicial compartida una vez; un error de /runs queda visible con **No pudimos cargar tus análisis** y **Reintentar**, sin peticiones nuevas hasta acción explícita. Cargando/error/ningún análisis/ID inexistente deben ser estados distintos. No reemplazar la selección por defecto tras un error.

La reproducción privada `artifacts/private/codex_review16_probe.spec.ts` mostró otra petición automática tras503. Incorporar una regresión definitiva y comprobar que falla antes del arreglo. Cubrir Inicio y Ventas previstas; posterior recuperación por botón y consumidores compartidos sin duplicación. No ocultar el error para pasar la prueba. Si se trata la caché entre sesiones, hacerlo con una invalidación pequeña y prueba de identidad, sin refactorizar autenticación.

## 2. Evaluación comprensible antes del detalle académico

La captura de Evaluación final todavía muestra muchas advertencias, conclusión, hallazgo primario, tabla y lista de reglas simultáneamente. Aplicar el brief también a esta pantalla:

- Vista inicial: pregunta clara, contexto de análisis/fechas, explicación corta del resultado, un aviso pertinente breve y acción **Ver cómo se evaluó**. Presentar el resultado principal y su alcance con palabras sencillas, sin ocultar que el error por producto es alto. Explicar WAPE distinto de acierto, mantener inventario simulado cuando se muestra simulación y no declarar ganador/impacto real.
- Tabla primaria detallada, regla de selección, cohortes, control cero, sesgos y métodos de cálculo en una sección académica expandible bien rotulada. Conservar datos desfavorables y controles, sin cambiar cifras ni su orden para aparentar éxito. No duplicar tres veces la misma explicación entre avisos y conclusión.
- Las dos secciones «Estimaciones frente a ventas registradas» y «Reposición simulada» pueden ser pestañas o secciones claramente diferenciadas; solo mostrar las advertencias completas relevantes a lo que está abierto. Mantener todos los textos publicados/localizables, y el aviso esencial de simulación junto a cualquier stock/costo/pedido. No cambiar contratos de backend ni guardar preferencias como controles de acceso.
- El alcance principal en palabras simples: productos con historia suficiente, acumulado14días, número de productos. La definición exacta de cohorte y SKU-almacén queda en detalle. Diferenciar «Métrica del01al14agosto» de «Bloque de prueba disponible01al21agosto» según datos; el pronóstico fijo de21días no cambia.

## 3. Precisiones de lenguaje

Arreglar los cinco puntos de revisión16: agregado de folds distinto de media aritmética; promedio sobre ventana de calendario/días válidos/ceros; análisis generado sin evaluación no significa inexistencia de ventas; fechasH14 frente a bloque21; guion comprueba presencia de análisis/puntero y no exactamente tres registros. Corregir el espacio entre fecha y paréntesis de la barra común.

No añadir columnas, nuevos indicadores, proveedores ni nombres comerciales inventados. No quitar trazabilidad, advertencias de versiones reemplazadas, falta de inventario o motivos de indisponibilidad de la final.

## 4. Verificar y entregar

- Pruebas dirigidas del frontend afectado y regresiónR17. No repetir los167backend sin cambio deAPI; no todos los212frontend si los cambios y dependencias quedan cubiertos por los tests pertinentes. Si se detecta un nuevo fallo fuera del alcance, comprobarlo y explicar su impacto.
- Una comprobación de producción en la demo: Inicio y Evaluación con detalle cerrado/abierto, error de carga controlado en prueba aislada (sin apagar Mongo de la demo), fechas/selección correctas, móvil/teclado si cambia la estructura. La caída se simula en prueba, no deteniendo servicios del usuario. No repetir51acciones ni crear más análisis de ensayo.
- Reconstruir/actualizar imagen identificada, conservar df-demo/base/volúmenes/credenciales y puntero; dejarla encendida en la misma URL. Avisar de una interrupción breve necesaria y comprobar health al volver. Nunca down-v ni tocar v1/v2/pub. Capturas del antes/después de Evaluación y error recuperable, sin claves.
- Registrar reporte breve docs/UX01R_REPORTE.md, evidencia privada artifacts/private/ux01r/, commit y continuidad. R17 cerrado solo con evidencia; no afirmar aceptación humana.
- Respuesta final breve para Rogelio: qué se simplificó, si debe recargar, URL activa y las mismas tres tareas de comprensión. No solicitar autorización Azure mientras espera validar la interfaz; no transformar el cierre en otra propuesta de diseño sin implementar.
