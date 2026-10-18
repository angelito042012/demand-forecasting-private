# Guion del video de sustentación (borrador)

Estado: borrador de estructura. **No se ha grabado ni publicado nada.** Código de referencia `f95092f` (interfaz UX01). Duración máxima 10 min: 3 de teoría + 7 de producto (según la fuente del curso). No afirma despliegue (URL: [PENDIENTE: no existe publicación]) ni aceptación humana (pendiente). Todo el producto se muestra en **ejecución local**. Antes de grabar: cifras revisadas contra `docs/T07_RESULTADOS.md` y `docs/T12_RESULTADOS.md`; sin credenciales a la vista; no grabar a terceros sin su consentimiento.

## Tabla de tiempos

| Tiempo | Bloque | Qué se muestra |
|---|---|---|
| 0:00–0:30 | Apertura | Título, nombre del autor, problema en una frase |
| 0:30–1:30 | Teoría 1: problema y datos | Diapositiva: MYPE, ventas de marzo a agosto de 2026 en seis Excel; notas de crédito separadas; días excluidos; ventas observadas posiblemente censuradas por stock |
| 1:30–2:30 | Teoría 2: método | Diapositiva: partición temporal, agosto reservado, transformaciones ajustadas en train, sin fuga; `promedio_28` operativo; RF comparador; control cero |
| 2:30–3:00 | Teoría 3: evaluación y límites | Diapositiva: WAPE no es precisión porcentual; inventario simulado con supuestos; qué no se afirma |
| 3:00–3:30 | Producto: acceso e Inicio | Acceso (certificado local: «Avanzado» → «Continuar»); ingreso con cuenta propia (contraseña no visible); **Inicio**: barra de análisis («En uso por defecto», «Ventas utilizadas hasta el 10/07/2026», período estimado) y menú (Inicio, Ventas previstas, Reposición simulada, Mis análisis; «Más») |
| 3:30–4:15 | Producto: Mis análisis | Tarjetas «Ejemplo de julio», análisis creado en la aplicación y «Evaluación de agosto»; «En uso por defecto» frente a «Seleccionado para consultar» (**Elegir este análisis**); **Ver versiones anteriores** con el aviso de versión reemplazada |
| 4:15–5:15 | Producto: Ventas previstas | Buscar un producto por «Código del producto» y **Buscar**; cantidad estimada y «Vendido (registrado)»; **Comparar métodos / ver detalles** (modelo experimental y control cero); «no evaluable» no es cero |
| 5:15–6:30 | Producto: Reposición simulada | Aviso «Inventario simulado con supuestos; no corresponde al inventario real de la empresa»; vistas «Con sugerencia de reposición / Sin necesidad de reponer en el ejemplo / Sin datos de inventario»; **Entender sugerencia** de un producto en tres pasos y **Ver cálculo completo y supuestos** |
| 6:30–7:30 | Producto: Evaluación de resultados | «Evaluación de resultados» (menú «Más»): vista breve con el error del promedio de 28 días («cerca del 78 % del volumen vendido»), el botón «Ver cómo se evaluó» que abre el detalle académico; «el error no es porcentaje de acierto»; simulación de tres políticas: más servicio con más stock; MAPE con cobertura y R² «no evaluable» en el detalle académico |
| 7:30–8:30 | Producto: evaluación de agosto | Elegir «Evaluación de agosto»: advertencias, un solo bloque de 21 días, sin ganador; Reposición simulada dice «Este análisis no genera pedidos» |
| 8:30–9:30 | Producto: administración | Admin: «Cargar datos» (pasos 1-2-3; reenvío «sin duplicar») y «Crear análisis»; mencionar que el lector no ve estas acciones y que solo ve «Datos cargados». Solo con un caso mínimo ya probado; no entrenar en vivo |
| 9:30–10:00 | Cierre | Resumen honesto: qué funciona en local, qué está pendiente (publicación, aceptación humana), qué no se concluye |

## Narración propuesta

**Apertura.** «Presento un sistema de pronóstico de demanda y recomendación de reposición para una MYPE, desarrollado con datos históricos de marzo a agosto de 2026. Mostraré el método y luego el producto funcionando en mi equipo.»

**Teoría 1.** «Las ventas vienen de seis archivos Excel. Las notas de crédito se informan aparte y no se interpretan como devoluciones físicas. Algunos días se excluyen del entrenamiento y de las métricas. La venta observada puede estar limitada por falta de stock, por lo que no es la demanda real.»

**Teoría 2.** «Se evalúa con partición temporal: el último mes queda reservado y las transformaciones se ajustan solo con entrenamiento. El método operativo es el promedio móvil de 28 días. Un bosque aleatorio actúa como comparador y no mejora el hallazgo principal; el pronóstico cero es solo un control.»

**Teoría 3.** «La métrica principal es el WAPE: error absoluto total sobre las unidades observadas. No es un porcentaje de acierto. En desarrollo, por SKU y horizonte de 14 días, el promedio de 28 días tuvo un WAPE de 0,87; por categoría, 0,20. En la evaluación final de agosto, un solo bloque de 21 días, fue 0,78 por SKU (RF 0,79) y 0,12 por categoría. [Cifras comprobadas contra T07_RESULTADOS (0,8726 y 0,2018) y T12_RESULTADOS (0,7810; 0,7910; 0,1170) el 17/10/2026; volver a comprobar si cambia algún documento antes de grabar.] El inventario de las simulaciones es simulado, con supuestos; no corresponde al inventario real, y no se afirma mejora real.»

**Producto.** Seguir el orden de la tabla. Frases clave por pantalla:
- Mis análisis: «Este es el ejemplo de julio, con ventas utilizadas hasta el 10 de julio; este fue creado desde la aplicación; esta es la evaluación de agosto. “En uso por defecto” lo fija el servidor; “seleccionado para consultar” es solo lo que yo miro. Son datos históricos, no las ventas de hoy.»
- Reposición simulada: «Cada sugerencia se explica en tres pasos: con qué se cuenta, qué se busca cubrir y de dónde sale la cantidad. El disponible es simulado; la cantidad es hipotética, no una compra.»
- Evaluación de resultados: «El error absoluto no es porcentaje de acierto. Más servicio llegó con más stock y más compras; eso no es una ganancia neta.»
- Evaluación de agosto: «Aquí no hay pedidos por diseño: solo se compara el pronóstico fijado el 31/07 con lo registrado del 1 al 21 de agosto.»
- Administración: «Cargar un Excel o crear un análisis encola un trabajo que procesa un worker. Reenviar el mismo archivo no duplica.»

**Cierre.** «El sistema funciona en ejecución local con evidencia de pruebas. La publicación en la nube y la validación con usuarios reales están pendientes. Los resultados describen datos históricos y un inventario simulado; no demuestran impacto real en la empresa.»

## Estructura de sustentación (preguntas a preparar)

1. Por qué `promedio_28` y no el RF (evidencia T07 y T12; el RF no mejora el hallazgo principal).
2. Qué significa WAPE y por qué no es precisión.
3. Cómo se evitó la fuga temporal (corte, rezagos, agosto reservado, sello previo de las predicciones finales).
4. Qué es el inventario simulado, qué supuestos tiene y por qué no prueba impacto.
5. Qué limita la venta censurada y los folds solapados.
6. Qué está probado en local y qué falta para publicar y aceptar.

## Lista de comprobación previa a grabar (pendiente)

- [ ] Servicios locales arrancados con `scripts/start-local.ps1`; cuentas propias creadas.
- [ ] Cifras de la teoría contrastadas con los documentos de resultados.
- [ ] Sin credenciales, `.env` ni datos comerciales sensibles en pantalla.
- [ ] Ensayo cronometrado; si excede 10 min, recortar Administración antes que la teoría.
- [ ] Decidir con el usuario destino y acceso del video antes de publicarlo.
