# Informe final (BORRADOR)

**Estado: borrador Markdown del 17/10/2026, no es el informe definitivo.** Sin firmas, encuestas, aprobaciones ni aceptación humana (pendiente). El sistema no está desplegado en la nube. Todas las cifras proceden de documentos auditados del repositorio y se citan por archivo. Donde se necesita bibliografía figura "[PENDIENTE: verificar fuente]".

**Rótulo obligatorio:** Inventario simulado con supuestos; no corresponde al inventario real de la empresa.

## 1. Problema

Según la fuente (`docs/FUENTE_EXTRAIDA.txt`, objetivos y situación problemática), una MYPE de productos de cuidado personal en Lima decide la reposición principalmente por experiencia, observación del stock y ventas recientes. La fuente plantea que un algoritmo de machine learning para pronosticar demanda mejoraría la gestión de inventarios. El análisis (`docs/ANALISIS_Y_PLAN.md`) advierte que la magnitud de los problemas de quiebre y sobrestock debe corroborarse y que ausencia de ML no prueba mala gestión. Esta cadena causal sigue sin comprobación con datos reales de inventario, que no se tienen.

Objetivos de la fuente: (general) determinar en qué medida un algoritmo de ML para pronóstico mejora la gestión de inventarios; (1) pronosticar demanda por categoría con MAPE < 15 % y R² > 0,85 (metas declaradas, no resultados garantizados); (2) evaluar el efecto sobre quiebres y sobrestock por backtesting frente a la política actual; (3) determinar el impacto sobre la rotación.

## 2. Alcance real

Lo que se hizo (`docs/ESTADO.md`, `docs/T11B_REPORTE.md`):

- Importación y auditoría de seis Excel de ventas (marzo a agosto de 2026), pronóstico de demanda por SKU con agregación a categoría, evaluación temporal, simulación de reposición con inventario sintético, API, interfaz web, generación en contenedor, respaldo y restauración locales.

Lo que no se hizo o no puede afirmarse:

- No hay datos reales de inventario, costos, proveedores ni lead times. La política actual de la MYPE no se reconstruyó: se compara una referencia sintética con políticas basadas en pronóstico. El usuario autorizó este cambio (`docs/DECISIONES_DATOS.md`); su aceptación académica final corresponde al asesor y no se presume.
- No se mide impacto real ni causal en la MYPE.
- Despliegue HTTPS en nube, prueba con cinco usuarios en nube (A13) y aceptación por una persona real (A14): pendientes (`docs/MATRIZ_CIERRE.md`).
- Rotación de inventario: no se encontró un índice de rotación en los resultados auditados.

## 3. Arquitectura

(`docs/ANALISIS_Y_PLAN.md`, `docs/T11_CONTRATO.md`, `docs/T11B_REPORTE.md`)

- Angular (`frontend/`), FastAPI (`backend/`), Python 3.12 y PyMongo, MongoDB (`pipeline/`, `backend/`). Autenticación por sesión HttpOnly con CSRF y roles; los lectores no tienen permisos de mutación (ESTADO.md, T08/T10).
- Cadena: dataset validado, preparación, pronóstico, simulación y recomendaciones, persistencia de una corrida completa, API, pantallas. Las corridas se publican solo si están completas; histórica, generada y final se mantienen separadas.
- Cola durable y worker para cargas y generación; el pronóstico no se entrena al abrir una pantalla (ESTADO.md, T10).
- Empaquetado: imagen única, compose de ensayo (ESTADO.md, T11A). La propuesta de nube (Azure Container Apps, Files, ACR y MongoDB Atlas Free) es un plan con costos estimados y varias cifras no verificadas (`docs/T11_PLAN_DESPLIEGUE.md`); no está desplegada.
- Cambio respecto a la fuente: PyMongo en lugar de Motor (ANALISIS_Y_PLAN.md); Azure Functions timer no es el mecanismo vigente, el timer manual está deshabilitado por defecto y la generación va por worker (ESTADO.md).

## 4. Datos y decisiones

Hechos auditados:

- Seis Excel originales intactos; 87 437 líneas = 86 877 ventas + 560 notas de crédito; 31 columnas homogéneas (ESTADO.md).
- Marzo a julio (T04, `docs/T04_PERFIL_CALIDAD.md`): 71 931 líneas de venta, 3 758 SKU, un almacén, 37 categorías al corte, unidad base UND. Proporción de ceros observados sobre días usables 0,8796; 459 375 filas SKU-día con 54 266 con venta.
- Agosto: 14 946 líneas y 24 404 unidades (01 a 31/08), leídas solo en la evaluación final T12 (T12_RESULTADOS, ESTADO.md).

Decisiones cerradas (`docs/DECISIONES_DATOS.md`):

1. TIPO_DOC=7 son notas de crédito; se separan de las ventas brutas y no implican devolución física.
2. Se excluyen del entrenamiento y las métricas el 03/04, 12/04 y 07/06 de 2026, sin comprimir el calendario ni etiquetarlos como cero.
3. Catálogo de categorías por fecha de corte; el SKU 16140041 queda en MAQUILLAJE PARA ROSTRO al 31/07.
4. Inventario sintético autorizado y rotulado, con parámetros: lead time 7, revisión 7, seguridad 7 días, costo 65 % de la mediana de precio, holding 20 % anual, empaque y mínimo 1. Son supuestos.

Limitación de datos: la venta observada puede estar censurada por faltante de stock desconocido; un cero observado no significa ausencia de demanda (T04). Cinco meses no permiten estacionalidad anual (T04). Las cifras del DOCX original no concilian con los Excel (`docs/AUDITORIA_DATOS.md`), y se usan los conteos auditados.

## 5. Metodología temporal

(`docs/T07_RESULTADOS.md`, `docs/T12_RESULTADOS.md`, `docs/SELECCION_CONGELADA.md`)

- Partición temporal; el último mes (agosto) reservado. Transformaciones ajustadas en train; rezagos anteriores al corte; sin ventas futuras reales en el horizonte múltiple.
- Desarrollo (T07): 4 folds de bloques de 21 días con cortes 31/05, 14/06, 28/06 y 10/07 (bloques solapados, no independientes) y simulación 01/06 a 31/07. Meses ya usados en T05/T06, sin independencia respecto de la elección de métodos.
- Evaluación final (T12): selección congelada antes de leer agosto (JSON sha256 `8a913805…`), predicciones iniciales selladas antes de la lectura, un solo bloque 01 a 21/08 con origen 31/07, y simulación secuencial 01 a 31/08 con revisiones los días 1, 8, 15, 22 y 29. Auditoría separada aprobada, recomputada desde predicciones selladas.
- Métodos comparados: control cero, promedio_28 (promedio móvil de 28 días por SKU, método operativo), referencia fija 0531 (solo en T07) y Random Forest por categoría distribuido a SKU (comparador).
- Métricas: MAE, RMSE, WAPE, sesgo, MAPE solo sobre reales > 0 con cobertura informada, R². WAPE es un error ponderado por volumen (suma del error absoluto sobre el total observado); no es una precisión porcentual, y 1,00 equivale a 100 % del volumen. Cuando el total observado es cero, WAPE y R² son indefinidos (`n/e`).
- Escenarios de sensibilidad: lead time 3/7/14 y seguridad 0/7/14 (27 combinaciones).

## 6. Resultados

### 6.1 Desarrollo T07 (`docs/T07_RESULTADOS.md`)

SKU primaria, universo común, acum14, agregado de 4 folds (n = 11 957 observaciones SKU-fold, no SKU únicos; T07_RESULTADOS no informa el número de SKU únicos):

| Método | WAPE | Sesgo (pred - obs) | R² |
|---|---|---|---|
| cero | 1,0000 | -37 791 | -0,130 |
| promedio_28 | 0,8726 | 2 172,6 | -0,121 |
| referencia_fija_0531 | 1,0345 | 10 320,9 | -1,138 |
| rf_distribuido | 0,9292 | 6 326,5 | -0,443 |

La regla provisional no se cumplió: RF no mejoró a promedio_28 (mejora relativa -0,0649; folds favorables ninguno). El sesgo/observado de RF fue 0,167. Por fold (H14): promedio_28 0,923, 1,035, 0,810 y 0,762; RF 1,060, 1,068, 0,865 y 0,773.

Categoría, acum14: promedio_28 WAPE 0,2018 y R² 0,952; rf_categoria WAPE 0,2548 y R² 0,915 (n = 144).

### 6.2 Evaluación final T12 (`docs/T12_RESULTADOS.md`)

Hallazgo primario, SKU-almacén primaria, universo común n = 3 401, WAPE acum14: promedio_28 **0,7810**; RF distribuido **0,7910**; control cero 1,0000. Mejora relativa de RF -0,0129 (RF no es mejor). Sesgo/observado: promedio_28 0,020 y RF 0,030. Un solo bloque: RF no puede declararse ganador; el método operativo no cambia.

| Horizonte (SKU primaria) | promedio_28 WAPE | RF WAPE |
|---|---|---|
| acum10 | 0,8165 | 0,8308 |
| acum14 | 0,7810 | 0,7910 |
| acum21 | 0,7512 | 0,7590 |
| diaria | 1,5048 | 1,5009 |

Otras métricas de promedio_28 en acum14 (SKU primaria): MAE 2,380; RMSE 7,288; R² 0,321; MAPE 0,9599 con cobertura 0,485. En acum14 la unidad es la entidad SKU-almacén (n = 3 401): el MAPE excluye las entidades cuyo total observado a 14 días es cero, y 0,485 es la fracción de entidades incluidas (no de SKU únicos ni de días). La cobertura de MAPE de la serie diaria (0,097) usa otro denominador: n = 71 421 entidad-días, de los cuales solo el 9,7 % tiene venta observada positiva (MAPE diario de promedio_28 0,7591).

Categoría (promedio_28 = suma de SKU, n = 36), acum14: promedio_28 WAPE 0,1170, RF 0,1166; R² 0,994 en ambos; MAPE 0,4187 y 0,3693 (cobertura 0,889 de las 36 entidades categoría con total observado a 14 días mayor que cero).

Historia corta (357 SKU), acum14: promedio_28 WAPE 1,0618 y R² 0,623; RF WAPE 0,8009 y R² 0,741. Aquí RF supera a promedio_28 en este único bloque; es un resultado secundario, no el hallazgo primario.

SKU nuevos: 103 SKU con venta en el bloque 01 a 21/08 (353 unidades; cobertura de unidades 0,9785 del universo conocido, que tuvo 16 064 unidades); 141 SKU y 568 unidades en todo agosto quedan fuera del universo simulado.

### 6.3 Simulación (inventario simulado con supuestos; no corresponde al inventario real de la empresa)

T12, L = 7, S = 7, total (demanda elegible 23 836 unidades):

| Política | Fill rate | Perdidas | Stock medio/día | Compras (supuesto) |
|---|---|---|---|---|
| referencia_fija | 0,7561 | 5 813 | 12 648 | 267 440 |
| promedio_28 | 0,7792 | 5 262 | 13 881 | 309 792 |
| rf_categoria_distribuido | 0,7812 | 5 216 | 13 973 | 326 713 |

Frente a la referencia, promedio_28 aumenta el fill rate en 0,0231 con +9,7 % de stock medio y +15,8 % de compras. RF frente a promedio_28: +0,0019 de fill rate con +5,5 % de compras y +5,9 % de valor de stock final; RF tiene mayor fill rate en 6 de 9 escenarios y más compras en 9 de 9 (ESTADO.md). Balances re-verificados en las 27 combinaciones (identidad de valor máx. 1,09e-10).

T07 (01/06 a 31/07), L = 7, S = 7: fill rate 0,7410 (referencia), 0,7968 (promedio_28) y 0,8086 (RF).

## 7. Discusión

- **Pronóstico.** promedio_28 supera o iguala a RF en el hallazgo primario, tanto en T07 (0,8726 frente a 0,9292) como en T12 (0,7810 frente a 0,7910). RF es un comparador que no mejora el hallazgo principal. La diferencia en T12 (0,0100 en WAPE) proviene de un solo bloque y no permite concluir superioridad. No se atribuye a RF más que un resultado secundario en historia corta.
- **Metas originales.** MAPE < 15 % no se alcanza en ninguna de las granularidades evaluadas (SKU 0,9599; categoría 0,4187 en T12 acum14, calculados sobre días con reales > 0). R² > 0,85 se supera solo a nivel categoría (0,994 en T12), con unidades heterogéneas sumadas (T04: serie orientativa) y con categorías que son sumas de SKU; a nivel SKU el R² es 0,321. Estas metas no se reescriben como cumplidas: el pronóstico por SKU con 88 % de ceros diarios (T04) es intermitente y difícil, y el WAPE de 0,78 indica un error ponderado alto.
- **Gestión de inventarios.** En simulación, una mejora de fill rate coincide con más stock y más compras. Sin una comparación a stock o compras equivalentes la ventaja de servicio no es concluyente (T07 y T12). No se demostró reducción de sobrestock (el stock medio sube). Por tanto, la hipótesis de mejora significativa de la gestión no se confirma con esta evidencia, y tampoco se refuta: la evidencia es de simulación bajo supuestos, sobre un bloque.
- **Censura.** Las ventas observadas pueden estar censuradas por stock; el pronóstico estima ventas observadas, no demanda latente.
- **Antecedentes.** La fuente cita estudios previos en MYPE con Random Forest. Su cita y cifras requieren comprobación: [PENDIENTE: verificar fuente].

## 8. Limitaciones

- Un solo bloque de 21 días en T12, sin intervalo de confianza; T07 usa folds solapados y meses ya empleados en el desarrollo (T12_RESULTADOS, T07_RESULTADOS).
- Inventario, costos, holding, lead time y seguridad son supuestos; no hay MOQ, proveedores ni backorders; un almacén.
- Demanda proxy = ventas observadas; 07/06 sin demanda conocida en la simulación T07.
- Universo fijo y catálogo de categorías al corte; SKU nuevos informados aparte.
- RF por categoría usa solo 36 series; las variables mes y día del mes salen del rango de entrenamiento al predecir y pueden explicar parte de su desempeño (no investigado; T07).
- Estado de la nube: sin despliegue; costos de Azure son estimaciones y una cuota de entorno 0/1 en Brazil South no demuestra cuotas de cómputo, permisos ni egreso efectivos (REVISION_CODEX_13).
- Respaldo: los modelos T07 (47 MB) quedan fuera del bundle; la restauración debe hacerse con escritores detenidos (REVISION_CODEX_13).
- Las pruebas de navegador, Docker y la suite grande son resultados reportados por Claude; Codex repitió solo pruebas selectivas (REVISION_CODEX_10 a 13).

## 9. Conclusiones basadas en evidencia

1. Se construyó localmente una cadena reproducible de datos a recomendación simulada, con partición temporal, selección congelada, sello previo a la lectura de agosto y auditoría separada de T12.
2. El método operativo promedio_28 obtuvo en el hallazgo primario de T12 un WAPE de 0,7810 frente a 0,7910 del comparador RF; RF no mejoró el hallazgo principal. Un WAPE de 0,78 no es una precisión de 22 %.
3. Las metas MAPE < 15 % y R² > 0,85 no se lograron a nivel SKU; a nivel categoría R² las supera, pero MAPE no.
4. La simulación muestra que un mayor fill rate va acompañado de mayor stock y compras. No se demuestra mejora de gestión, ahorro ni impacto causal en la MYPE.
5. Los resultados desfavorables se conservan (control cero, historia corta, RF sin ventaja).
6. La aceptación por una persona real, el despliegue y la conciliación con reporte externo de la MYPE siguen pendientes.

## 10. Pendientes antes del informe definitivo

- Aprobación del plan de nube, despliegue HTTPS, prueba con cinco usuarios y latencia en nube (A13).
- Recorrido de aceptación humana real (A14) y, si corresponde, validación de supuestos con la MYPE; entrevista sobre lead time y política.
- Conciliación con reporte externo; instalación limpia y CI.
- Cálculo o exclusión explícita de rotación de inventario y % de SKU con exceso.
- Verificación de bibliografía y antecedentes: [PENDIENTE: verificar fuente]. Resumen/abstract, anexos y matriz de trazabilidad definitivos (ver `docs/MATRIZ_CIERRE.md`).
- Conformidad académica del asesor sobre el cambio a evaluación por simulación sintética.
