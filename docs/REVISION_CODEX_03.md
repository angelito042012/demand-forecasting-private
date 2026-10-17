# Revisión de R04 y T04

Fecha: 17/10/2026. Código de la entrega revisada: commit 269e15b y sus antecedentes. Resultado: R04, preparación de v2 y T04 aceptados para las seis fuentes canónicas auditadas; se puede ejecutar ETAPA_03_CLAUDE.md.

## Evidencia revisada

Codex revisó sources.py, training_access.py, catalog.py, daily_series.py, la generación de T04, el comparador v1/v2, pruebas pertinentes y archivos de entrega. Git estaba limpio al comenzar. Se leyó compare_v1_v2.json: comparación de conteos, importes y multiconjuntos de líneas coincide en ambas colecciones y seis meses; recarga no-op, sin conflictos ni rechazos. Esa comparación guardada se acepta como evidencia de Claude revisada en código; no se volvió a ejecutar la migración ni la carga completa.

Verificación independiente acotada de Codex:

- 14 pruebas de aprobación de fuentes e invariancia temporal aprobadas en bases temporales, 2,84 segundos.
- 6 pruebas de series diarias aprobadas, 0,81 segundos.
- Análisis de estilo de backend, pipeline, tests y los dos scripts nuevos: correcto.
- Hash de los tres archivos derivados coincide con T04_FIRMA.json; también coincide el hash del contenido descomprimido de las dos series.
- Se recorrieron las 459 375 filas SKU-día: ninguna posterior al 31/07, 54 266 con venta, 396 339 ceros observados y 8770 enmascaradas con cantidad vacía. Las sumas por mes de cantidades e importes coinciden con el perfil de T04.

Claude reportó 65 pruebas completas aprobadas, cero omitidas y un aviso de deprecación. Codex no repitió esas 65: las 20 pruebas seleccionadas y los controles anteriores constituyen esta revisión. No confundir el resultado reportado del ejecutor con verificaciones repetidas por el revisor.

## Límites aceptados para esta etapa

Una sola fuente aprobada por mes es una restricción deliberada para estos seis archivos. No constituye un importador de reemplazos/correcciones sin intervención. Si llegan archivos diferentes, validar y resolver la fuente activa antes de seguir; no borrar estados o conflictos para eludir la comprobación.

El informe de generación registra un commit anterior y git_sucio=true porque el dataset se produjo antes del commit final. Los hashes permiten identificar los datos, pero la próxima entrega debe incluir también un hash determinista de los archivos de código pertinentes y de la configuración, evitando depender de un árbol de trabajo sucio sin identificar.

Los puntos menores declarados en TRASPASO.md deben cerrarse al comenzar T05: unidad_base en fingerprint; catálogo consistente con la ventana start y máscara de ventas; céntimos sin truncado silencioso; diccionario con SIN_REGISTROS_DIA y conservación de ese estado en el agregado por categoría. No afectan los totales de este conjunto canónico, pero afectan la reutilización correcta en folds y nuevos datos.

Un inicio de observación tardío no prueba que el producto sea una alta real. Conservar esa distinción al definir cobertura. Los ceros representan ventas observadas, no stock disponible ni demanda perdida conocida.

## Siguiente incremento

T05: protocolo de validación temporal, baselines simples, comparación reproducible y métricas con cobertura; solo marzo-julio. Reconstruir datos y catálogo por corte de fold: el dataset final de T04 al 31/07 no se puede reutilizar como si fuera el conocimiento de mayo o junio.

En paralelo y con archivos separados, intentar preparar Angular ahora que Claude reportó npm ping correcto; probar compilación de una base mínima. No bloquear T05 si vuelve a fallar, ni ampliar a pantallas funcionales en esta entrega.

No iniciar Random Forest/boosting ni evaluar agosto todavía. El resultado de T05 definirá la referencia y el contrato para comparar ML en T06.
