# Revisión Codex 18 — inventario informado

18/10/2026, America/Lima. Entrega examinada: código `464eb0c`, documentación `a9c8b35`. **Resultado: requiere una corrección acotada R18 antes de aceptación técnica.** Aceptación humana sigue pendiente. Claude continúa como ejecutor; Codex no cambió la aplicación, las fuentes, las bases ni los servicios.

## R18 — vincular el derivado importado con el documento revisado [P2]

En `pipeline/inventory/reported_count.py`, `prepare()` verifica el SHA del Excel contra las referencias incluidas en el CSV y `review.json`, pero no contrasta las cantidades, presentación, filas y fecha del CSV con las celdas del Excel ni con un manifiesto independiente que autentique ese derivado. Calcula el SHA del CSV que recibe y lo guarda; ese cálculo por sí solo no acredita su correspondencia con la fuente.

Reproducción sobre copias del paquete v2, sin base de datos: aumentar en uno disponible y total de una fila mantiene las reglas aritméticas y `prepare()` lo acepta con el mismo identificador y SHA del Excel. En una segunda variante, cambiar la fecha de todas las filas al 19/10 también se acepta sin cambiar el Excel ni `review.json`. En una primera importación a una base vacía no existe un CSV previamente guardado contra el cual comparar. Por tanto, un error de edición del derivado puede atribuir al documento empresarial datos que este no informa. La comprobación de CSV distinto en una reimportación no cubre esa primera carga.

No se demuestra que el inventario ya importado sea erróneo: el hallazgo es una validación ausente. Evidencia privada: `artifacts/private/codex_review18/check_integrity.py` e `integrity_result.json`. La fuente original permaneció intacta.

### Encargo de corrección

Validar antes de cualquier escritura la correspondencia de cada registro con el Excel revisado, o con un manifiesto independiente verificado que ancle el contenido semántico completo del derivado a esa fuente. Cubrir código/fila, cantidades, unidad/presentación, fecha/hora y metadatos aplicables; preservar las confirmaciones humanas separadas y la diferencia entre vacío y cero. No basta con recalcular el SHA del CSV recibido o confiar en hashes que el mismo CSV declara. Una fuente modificada legítimamente requiere su revisión y versión correspondientes.

Añadir regresiones que fallen con el código entregado: CSV con cantidad y total coherentes pero distintos del Excel; fecha uniforme distinta del documento; presentación cambiada; derivado legítimo intacto aceptado e idempotente. Las fuentes de prueba deben permitir comprobar esa correspondencia; los archivos de bytes arbitrarios llamados `.xlsx` actuales no ejercitan esa garantía. Probar la corrección de forma dirigida y actualizar contrato/reporte/estado. Reutilizar el ensayo aislado; no reconstruir/restaurar la demo anterior, repetir modelos/T12 ni publicar. Si es necesario actualizar la imagen de ensayo, conservar su base y documentar imagen/puerto.

## Comprobaciones de esta revisión

- Árbol limpio al recibir la entrega; los dos commits existen. Lectura de contrato, reporte, importador, API, pantalla, cambios de entorno y pruebas relevantes.
- `prepare()` sobre la fuente v2 intacta: 50 productos, 48 con existencia, 2 sin, SHA del Excel esperado. No se escribió en Mongo.
- Pruebas propias dirigidas del validador: **22 aprobadas, 8 fuera de selección**, 1,68 s. Log y XML en `artifacts/private/codex_review18/validation_tests.*`.
- Intento inicial de 64 pruebas: **62 errores de preparación y 2 omitidas**, no aprobadas. El entorno temporal por defecto no permitió crear directorios; el problema se resolvió usando un directorio temporal privado para las 22 pruebas de validación anteriores. No se repitió la batería de base de datos tras constatar las limitaciones de acceso del entorno.
- `demo_local status` de ambos entornos no pudo acceder al motor Docker (permiso denegado). Su salida «contenedores: ninguno» **no demuestra que estén detenidos o ausentes**. No se operó sobre servicios ni se solicitó detenerlos.
- Revisados el resultado de navegador 22/22, el registro de aislamiento y la captura de inventario aportados por Claude; son evidencia del ejecutor, no un recorrido propio ni una nueva comprobación en vivo.

## Siguiente paso

Claude corrige R18 y entrega commit, pruebas y evidencia. Codex revisa solo ese cambio y sus efectos relevantes. Rogelio puede explorar la pantalla de ensayo; su aceptación de comprensión solo se registra con respuestas reales. La cuarta tarea de Claude incluye ese acompañamiento y no demuestra por sí sola un proceso de desarrollo aún activo. Sin nube ni ampliación del estudio.
