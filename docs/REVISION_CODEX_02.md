# Segunda revisión de Codex

## Resultado del código revisado

R01, R02 y R03 de REVISION_CODEX_01.md se consideran corregidos para la carga de los seis archivos canónicos auditados. Se acepta avanzar a T04 con los límites indicados aquí. La interfaz y el entorno completo siguen pendientes de Angular. No se autoriza aún iniciar entrenamiento.

R01 ahora propaga errores reales, limita la recuperación a duplicados y verifica persistencia. R02 usa identidad normalizada para ventas y créditos, conserva fuentes y registra conflictos de documento. R03 distingue las entradas de cada importación del conjunto lógico único. La barrera temporal aplica corte al 31 de julio o anterior, máscara de exclusión y catálogo al corte. El acceso a agosto se declara explícitamente como evaluación final, sin ser un control de seguridad de MongoDB.

Los límites de archivos parciales, documentos corregidos, líneas desaparecidas y resolución de conflictos no se consideran funcionalidades completas para uso operativo general. Para esta etapa usar exclusivamente las seis fuentes verificadas, sin sustituciones silenciosas. La conciliación lógica basada en límites de conteos es un control de consistencia; no sustituye una comparación exacta contra el manifiesto de líneas del conjunto aprobado.

## Comprobaciones independientes

Se revisaron importador, conciliación, barrera temporal, estrategia de claves y pruebas de regresión. El análisis de estilo de backend, pipeline y tests pasó. La base original conserva 86 877 ventas y 560 créditos; ambas colecciones mantienen schema_version=1. Las pruebas y reproducciones de Codex se ejecutan en bases temporales exclusivas, conservando la base original.

Suite completa independiente con RUN_REALDATA=1: **46 passed, 1 warning en 59,57 segundos**. El aviso es de deprecación httpx/Starlette; no causó fallo. Incluye carga/recarga de los seis Excel en bases temporales, conciliación por mes y corte de entrenamiento. No se modificó código de aplicación durante esta revisión.

## R04 Protección antes de preparar datos para modelos

Reproducción adicional en una base temporal: simular error tras insertar una de dos ventas deja una importación failed y una venta parcial persistida. load_training_data devuelve esa venta como entrenamiento, sin bloquear ni advertir que su fuente está incompleta. El control de fechas no garantiza que la carga esté completa.

Incorporar a T04 una comprobación obligatoria de fuentes y calidad en la ruta pública de acceso a datos. Las ventas y categorías elegibles deben proceder de fuentes/cargas completas y aprobadas para el corte; una carga parcial, conflicto abierto relevante o una fuente no reconocida no puede entrar silenciosamente. Una solución conservadora puede detener la construcción del dataset y explicar la causa. El catálogo debe obedecer la misma selección de fuentes que las ventas.

Pruebas necesarias: carga parcial fallida bloquea/excluye sus filas; reintento completo permite usarlas una sola vez; conflictos relevantes no entran silenciosamente; filas sin fuente válida no se aceptan; meses esperados ausentes se informan; registros posteriores al corte no cambian un conjunto previamente aprobado. La reconciliación no debe considerar ausencia de importaciones como aprobación por una condición vacía.

El fingerprint del futuro dataset debe cubrir contenido y decisiones que afectan al modelo: fechas, cantidades, categorías/catalogo, almacén/unidades, máscara, parámetros de agregación y manifiesto de fuentes. El fingerprint actual de líneas es útil para sus pruebas temporales, pero no es todavía una firma completa de un dataset de features.

## Preparación de la base v2

Aprobada técnicamente la estrategia de reconstrucción en una base nueva. Crear demand_forecasting_v2 desde los seis Excel originales usando el importador v2; comprobar conteos, importes y correspondencia de líneas normalizadas contra la base v1. Repetir la carga y comprobar cero inserciones adicionales y cero conflictos. No borrar ni modificar v1.

Si todo coincide, configurar localmente la aplicación y las tareas para usar v2, conservando documentado el nombre anterior para revertir. Es un cambio local reversible dentro de la preparación autorizada. No se requiere detener esta tarea para solicitar nuevamente autorización de desarrollo; cualquier borrado de la base anterior queda fuera de este encargo.

## Entrega T04

Entregar perfil de calidad, diccionario, serie diaria por SKU/almacén y agregado por categoría usando exclusivamente marzo-julio y la ruta de datos validada. Mantener calendario natural y tres días enmascarados. Definir inicio de observación por producto: los días anteriores a su primera evidencia no deben convertirse automáticamente en demanda cero conocida. Para ausencia de venta después de su primera observación, marcar la interpretación como venta observada cero bajo cobertura válida, sin afirmar ausencia de demanda perdida o stock disponible.

No materializar millones de filas sin medir necesidad y tamaño. Preferir un formato tabular adecuado para la serie derivada, con hash y procedencia; no versionar datos comerciales en Git. No generar features para agosto ni abrirlo como validación de selección. Presentar cobertura, ventanas de historia y series intermitentes para decidir el siguiente paso de ML.

Mantener el bloqueo npm visible y continuar el trabajo de datos. No desactivar TLS ni instalar paquetes desde espejos sin verificar. No entrenar, realizar selección de modelos o inventar métricas en esta entrega.
