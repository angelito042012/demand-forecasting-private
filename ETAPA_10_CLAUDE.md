# T12: evaluación final de agosto bajo selección congelada

Lee `RETOMAR_CLAUDE.md`, `docs/ESTADO.md`, `docs/TRASPASO.md`, `docs/REVISION_CODEX_10.md`, `docs/SELECCION_CONGELADA.md`, `config/seleccion_congelada.json` y `docs/DECISIONES_DATOS.md`. T10R/6212f6a aceptado; R07–R10 cerrados en el alcance local. **Continuar el proyecto, no repetir etapas cerradas. Fecha final 23/10/2026 Lima.**

## 1. Autorización específica y límites

Este es el encargo explícito posterior de Codex exigido por la congelación. **Autoriza consultar agosto exclusivamente desde la ruta dedicada de evaluación final**, después de verificar hashes y preparar las salidas predictivas iniciales con marzo–julio. No es autorización para re-seleccionar modelos, buscar hiperparámetros, retocar categorías/políticas tras ver resultados, abrir agosto en cargas web/entrenamiento general, consultar reference_v1 ni desplegar/gastar.

No modificar el documento/JSON/checksum congelados para cambiar sus indicadores históricos «sin ejecutar»: son el registro de lo decidido antes del test. El estado real de la ejecución se guarda en un manifiesto T12 separado y en ESTADO/TRASPASO. Si aparece una incompatibilidad metodológica sustancial que impide cumplir el protocolo, registrarla y detener la ejecución del test para revisión; no cambiar la congelación en silencio ni pedir permiso para decisiones rutinarias de implementación ya cubiertas aquí.

Un integrador, hasta tres agentes independientes cuando ayude: adaptador/runner, auditoría y pruebas, reporte. El integrador controla el acceso al test; no permitir que un agente explore agosto mientras otro aún elige/diseña método. Checkpoints/traspaso por unidad y durante procesos largos, sin esperar al final.

## 2. Preflight y adaptación antes de consultar el test

- Crear `scripts/run_final.py` y un módulo específico de evaluación final, contrato/protocolo de ejecución `docs/T12_PROTOCOLO.md` y pruebas pequeñas sintéticas. Fijar interfaz de fases prepare/evaluate/resume o equivalente; errores no pueden marcar una ejecución como completa.
- Verificar sha256 normalizados CRLF→LF del JSON congelado, documento contra su referencia previa (9596d26), config T07 y 14 archivos del módulo experimental contra el commit y hashes registrados. **No presumir que todos los archivos vivos conservan esos hashes**: importer, training_access y engine recibieron endurecimiento posterior. Recuperar desde Git una copia aislada con hashes exactos para los cálculos experimentales congelados, o demostrar una adaptación equivalente con esas referencias sin reescribirlas. Registrar qué código se usa y sus hashes. No ejecutar de nuevo scripts/run_t07 ni sus cuatro folds.
- Base principal solo lectura para T12. Fuentes aprobadas completas y conciliadas, sin conflictos; cargar historia ≤31/07 con la barrera existente. Nunca cambiar la base v1/v2, Excel, cargas previas o puntero histórico para evaluar.
- Preparar universo SKU-almacén, catálogo y cohortes conocidos al31/07. Inicialización/costos y todo ajuste inicial usan solo marzo–julio. Créditos fuera del objetivo; máscaras y días sin registros conservados sin ceros ficticios ni calendario comprimido.
- Antes de leer agosto: guardar paquetes/modelos, predicciones fijas completas 01–21/08, configuración/fingerprints y manifiesto de preparación; fijar sus hashes. Commit de código/protocolo y pruebas antes de ejecutar la fase real. Los artefactos con datos/modelos permanecen privados, fuera de Git. No repetir entrenamiento T06/T07; entrenar únicamente lo necesario para este protocolo final.

## 3. Evaluación predictiva fija

- Origen único **31/07/2026**, bloque **01–21/08**, h1…21. Método operativo **promedio_28 por SKU**, control cero y RF por categoría distribuido a SKU como comparador experimental con exactamente parámetros/features/pesos/semilla/horizontes T07 congelados.
- No actualizar predicciones ni señales iniciales con ventas del bloque. Generarlas y sellarlas antes de leer los reales; cargar agosto mediante `load_final_test_sales(..., frozen_selection_confirmed=True)` y una frontera dedicada/revisable. No debilitar `load_training_data`/`load_fold` ni los límites HTTP de T10 para acceder al test.
- Para categorías, el baseline operativo es **suma de los pronósticos SKU**, como fija la congelación; no sustituirlo por una media independiente de la serie agregada si difieren los días disponibles por SKU. RF mantiene conservación categoría→SKU y fallbacks documentados.
- Métrica primaria: **WAPE acumulado H14, SKU, cohorte primaria, universo común**. Informar H10/H14/H21 y diario, SKU/categoría, primaria/historia corta, cobertura/universo excluido, MAE, RMSE, sesgo/sub/sobre y MAPE solo con reales positivos y denominador/cobertura. R² solo si es definible y con cobertura, sin infinito/NaN engañosos.
- Reportar SKU cuya primera venta es posterior al31/07 aparte: número/unidades/cobertura, sin inventar historia, stock o categoría entrenada. Catálogo al31/07 no se corrige con agosto (incluido SKU16140041).
- Con un bloque no hay evidencia para declarar RF ganador por la regla de tres folds. Conservar todos los resultados, incluidos desfavorables y control cero; no modificar método operativo por el test.

## 4. Simulación secuencial, separada de la predicción fija

- Ventana **01–31/08**, universo conocido al31/07, tres políticas (`referencia_fija`, `promedio_28`, RF distribuido), nueve escenarios L{3,7,14}×S{0,7,14}, R7; principal L7/S7. Son **27 combinaciones**, siempre bajo las mismas condiciones y demanda proxy exógena.
- Stock inicial, media inicial y costos se estiman exclusivamente ≤31/07 con ecuaciones congeladas: stock ceil(media·(L+R)), costos supuestos65% de mediana de precio base con fallbacks, holding20%/365; mantener orden de eventos, tránsito y regla de techo/redondeo T07. No reemplazar la simulación experimental congelada por la fórmula exacta de la vista previa T08R sin registrar/revisar un cambio de protocolo.
- Revisiones al final de los días **1,8,15,22,29 de agosto**. Cada revisión recibe únicamente historia disponible hasta ese día, matrices físicamente truncadas y etiquetas de entrenamiento ≤origen. RF reentrena solo según parámetros congelados; baseline actualiza su ventana; referencia fija permanece congelada al inicio. No usar ventas futuras reales dentro de los21 días pronosticados.
- La incorporación semanal de pasado de agosto está autorizada **solo para esta simulación secuencial**; no puede contaminar las predicciones fijas del punto3. Implementar adaptador final acotado; no ampliar la ruta general de entrenamiento ni el scheduler/web.
- Días sin demanda conocida: sin evento/denominador, no ventas0 ni servicio perfecto. SKU nuevos de agosto separados, sin introducirlos en el universo simulado inicial.
- Informar servicio, pérdidas, días-SKU con faltante, stock medio/final, pedidos, tránsito final, compras desembolsadas, costo consumido y holding **supuestos**, total y cohortes. Diferencias absolutas/relativas frente a referencia y promedio_28; denominador0 no evaluable. Conservar saldos e identidad de valor para todas las combinaciones; separar mejora de servicio de mayor stock/compras.

## 5. Pruebas y ejecución real controlada

Antes del test real, pruebas sintéticas de: bloqueo sin confirmación/congelación alterada; datos posteriores al origen no cambian predicciones fijas; truncamiento de cada revisión; categorías=sumSKU; conservación RF→SKU; catálogo/cohortes/universo al31/07; faltantes y ceros; SKU nuevos; igualdad de condiciones entre políticas; conservación de unidades/valor y métricas con denominador0. Pruebas y código se fijan antes de observar resultados reales.

Ejecutar el procedimiento final una vez, por fases idempotentes con checkpoints. Guardar intención, estado/fase, hashes, timestamps, entorno/semillas/commit y errores. Si un proceso técnico se interrumpe, retomar artefactos válidos sin volver a seleccionar ni reemplazar evidencia; cualquier repetición técnica o corrección tras leer el test debe quedar explícita con motivo, versión anterior y efecto. No repetir toda la evaluación solo para confirmar que sale igual.

Auditoría separada sin entrenar de nuevo: recomputar métricas primarias desde predicciones/reales guardados (no desde el JSON de métricas), contar universo/cobertura, revisar fechas/fingerprints y todos los balances de simulación. Cambiar datos futuros en pruebas sintéticas debe dejar intacto el paquete inicial y la revisión anterior.

## 6. Artefactos y reporte

- Privados: `artifacts/private/final/` con manifiesto de preparación/ejecución, paquetes, vocabulario/pesos, predicciones, reales mínimos necesarios sin identificadores personales, cohortes/catálogo, revisiones, arrays/ledger, métricas y logs; checksums de bytes más firmas de contenido lógico cuando ZIP/NPZ tenga metadatos variables. No usar `data/synthetic/reference_v1` para suplir el test.
- Versionados sin datos comerciales: `docs/T12_PROTOCOLO.md`, `T12_RESULTADOS.md`, `T12_METRICAS.json`, `T12_MANIFIESTO.json`, código/pruebas y explicación de límites. Resultados relativos al control/baseline y escenarios con inventario simulado, sin afirmar impacto real en la empresa o cumplir umbrales que no se alcanzan.
- Esta fase deja un **paquete de evaluación final identificable y validado**, distinto de T07/T10. No insertar masivamente nuevas corridas en demand_forecasting_v2 ni activar puntero/nube: la base ronda459,39MB. Integración del paquete en web/publicación con capacidad/restauración verificada queda para T11/siguiente encargo. No afirmar que ya está publicado porque existen archivos locales.
- Actualizar ESTADO/TRASPASO/BACKLOG/HISTORIAL con fase real alcanzada y próximos pasos. Commit local revisando exclusiones; terminar con resumen breve, hashes/commit, pruebas, hallazgo primario, limitaciones y archivos de revisión. Detener para revisión de Codex.

## 7. Lo que sigue, sin ejecutarlo en T12

T11: alojamiento HTTPS de API/frontend/worker/timer, almacenamiento durable de subidas/modelos, usuario Atlas mínimo y credencial rotada, plan de capacidad/archivo sin pérdida, copia/restauración probadas y presupuesto concreto dentro de recursos autorizados. Azure estudiantes y Atlas Free ya creados; no volver a pedir alta ni secretos por chat. No hay presupuesto de bolsillo ni conversión a pago por uso autorizados. T13 aceptación/latencia/accesibilidad y T14/T15 informe/manual/video/entrega antes del23/10.
