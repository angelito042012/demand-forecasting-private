# T07 Protocolo: horizontes de reposición y simulación junio-julio (congelado antes de evaluar)

Fecha: 17/10/2026, America/Lima. Configuración: `config/t07_config.json` (t07-1). Se compromete en Git antes de producir resultados T07. Solo se leen ventas hasta el 31/07/2026; agosto (ventas y movimientos sintéticos `reference_v1`) no se consulta. **Inventario simulado con supuestos; no corresponde al inventario real de la empresa.** El código y los artefactos T06 se conservan sin cambios (T06 se identifica por sus commits y hashes); no se reentrena T06.

## Hipótesis y alcance

- H-pred (predictiva, provisional): un Random Forest global por categoría entrenado directamente para h=1..21 y distribuido a SKU con pesos históricos reduce el WAPE acumulado a H=14 de los SKU frente a `promedio_28`. Puede no cumplirse; no se fuerza.
- H-sim (descriptiva, sin dirección asumida): bajo supuestos idénticos, las tres políticas difieren en nivel de servicio, stock y compras. No se asume ganadora ninguna ni se llama ahorro/utilidad a menores compras con distinto servicio o stock terminal.
- La ventaja predictiva (si la hay) no implica mejor inventario; la simulación usa demanda proxy (ventas positivas observadas) y supuestos no verificados con la MYPE.

## Prerrequisito (cumplido antes de este protocolo)

La inferencia valida fecha de inicio y fin reales del contexto, dimensiones, número de entidades, identidad del vocabulario con que se construyeron los códigos (`Vocab.id`, `encode_with_vocab`), versión de features (`t07-1`) y horizonte entrenado; rechaza paquetes T06 salvo `allow_legacy=True` (solo h≤7). Semántica extendida de rezagos: para h>7 el mismo día de la semana se busca en la última semana ya observada, índice o+h−7·⌈h/7⌉, y siete días antes para el segundo rezago (idéntico a T06 para h≤7).

## Parte A: evaluación predictiva de horizontes 10/14/21

- Folds de desarrollo: cortes 31/05, 14/06, 28/06 y 10/07; bloque de 21 días naturales siguientes (el último termina el 31/07). Entrenamiento expansivo desde 01/03, calendario y máscaras originales (07/06 no entra en métricas ni entrenamiento, pero conserva su fecha). **Los bloques se solapan** (G1/G2 comparten 7 días, G2/G3 7, G3/G4 9): las cifras agregadas suman bloques de origen distinto, no unidades únicas; no se hacen pruebas de significación que supongan independencia.
- Población y cohortes por corte (T05): primaria (≥56 días de historia y ≥21 observaciones utilizables en 28 días), historia corta y nuevos/desconocidos aparte. Catálogo y universo al corte de cada fold, regenerados desde la ruta de fuentes aprobadas.
- Métodos SKU: `cero` (control), `promedio_28` (media de observaciones utilizables de 28 días al origen × días), `referencia_fija_0531` (media 28 días congelada al 31/05) y `rf_distribuido`. Nivel categoría: `cero`, `promedio_28`, `rf_categoria` (categoría = productos conocidos al corte).
- RF por categoría: parámetros de T06 (100 árboles, profundidad 12, hoja mínima 20, max_features 0,5, seed 20261017), **un hilo** (enmienda de cómputo declarada aquí: el conjunto es pequeño y así la suma es determinista), etiquetas h=1..21 con o+h ≤ corte, orígenes cada 3 días alineados hacia atrás, ceros válidos conservados, etiquetas ausentes/enmascaradas excluidas. Modelo directo; no se multiplica el pronóstico de 7 días ni se reutiliza un modelo entrenado a h≤7.
- Distribución a SKU: peso = unidades positivas de 28 días ≤ origen del SKU / suma de su categoría (SKU conocidos). Si la categoría suma cero: proporción histórica de unidades positivas hasta el origen; si aún sin masa: reparto uniforme. Se cuentan fallbacks y se verifica conservación del total de categoría. Se asigna a todos los SKU conocidos antes de filtrar cohortes. Cantidades continuas.
- Evaluación: acumulado de los primeros H días (H=10, 14, 21) del bloque y diario (21 días), sobre días evaluables (se informa cuántos); métricas WAPE, MAE, RMSE, sesgo, proporciones sub/sobre, cobertura y fallbacks, por fold/nivel/cohorte; universo común entre candidatos. Denominador cero ⇒ no evaluable.
- Regla provisional del candidato distribuido: criterio primario SKU acumulado H=14, cohorte primaria, universo común: mejora relativa ≥2 % frente a `promedio_28`, favorable en ≥3 de 4 folds y |sesgo|/observado ≤0,25. Se reportan igualmente H10/H21 y categoría; no se elige por el horizonte más favorable ni se congela selección para agosto.

## Parte B: simulación 01/06–31/07/2026

**Universo y datos.** SKU conocidos al 31/05 (primera venta ≤31/05); catálogo fijado al 31/05 para todo el experimento (los agregados por categoría de orígenes posteriores usan solo ese universo y ese catálogo). Los SKU con primera venta posterior se excluyen y se reportan aparte (unidades y cobertura). Todo lo inicial (stock, medias, costos) se calcula solo con datos ≤31/05, sin reutilizar `reference_v1` (calibrado con julio).

**Calendario y orden de eventos.** Cada día natural d, para cada SKU: (1) se reciben pedidos con llegada d; (2) demanda proxy = ventas positivas observadas del día (excepto 07/06, ver abajo); (3) se atiende min(disponible, demanda); el excedente es faltante perdido (sin backorder; las notas de crédito no crean entradas ni devoluciones); (4) si d ∈ {01/06, 08/06, …, 27/07} (revisión al final del día) se calcula el objetivo y se pide q = ⌈max(0, objetivo − (disponible + tránsito))⌉ con llegada en d+L (se recibe en el paso 1 de ese día; puede ser posterior al 31/07 y entonces queda en tránsito final); (5) se registra el saldo final y el holding del día. Empaque y mínimo 1. Saldo y posición nunca negativos. Demanda en unidades base enteras.

**Políticas (R=7, S días de buffer calculados con historia pasada, H=L+R).**
1. `referencia_fija` (sintética, no es política de la empresa): objetivo = ⌈media_inicial·(L+R+S)⌉ con media_inicial = promedio de observaciones utilizables de los 28 días ≤31/05, congelada.
2. `promedio_28`: en cada revisión, objetivo = ⌈Σ pronóstico próximos H días + S·media_28(d)⌉, con pronóstico = media_28(d) por día (d = día de la revisión; historia común ≤d).
3. `rf_categoria_distribuido`: misma ecuación; solo cambia el pronóstico (RF por categoría reajustado en cada origen de revisión con etiquetas ≤ origen, distribuido por pesos del origen). Misma seguridad (S·media_28 histórica), reglas, costos e inicialización que 2.
Los objetivos se redondean a 9 decimales antes del techo. Inicialización común por escenario: stock = ⌈media_inicial·(L+R)⌉, tránsito 0.

**Escenarios.** Principal L=7, S=7; matriz completa L∈{3,7,14}×S∈{0,7,14}, R=7: los nueve se muestran. Los pronósticos de cada origen se calculan una vez y se reutilizan en los escenarios (no se reentrena por escenario). Los pronósticos cubren fechas posteriores al 31/07 (para pedidos terminales) sin consultar sus reales ni evaluarlos.

**Señal exógena.** Todas las políticas ven la misma historia de demanda proxy observada hasta el día de la revisión; no se realimenta con ventas servidas por cada política (cambiaría la señal entre políticas). Es un escenario con demanda exógena observada, no una demostración causal.

**07/06 enmascarado.** No contiene demanda conocida: no hay evento de demanda ni denominador de servicio ese día; calendario, recepciones, revisiones y paso del tiempo continúan. No se escribe como venta cero. Supuesto del escenario: no descontar demanda desconocida; limita los estados posteriores. Las otras máscaras (03/04, 12/04) solo afectan entrenamiento.

**Costos (supuestos).** Costo unitario = 65 % de la mediana de precio por unidad base positivo (PRECIO/EQUIVALENCIA de ventas ≤31/05) del SKU; si falta: mediana de medianas de su categoría; si no: mediana global (se cuentan). Holding = 20 %/365 del costo por unidad en stock al final de cada día. Valoración: compras desembolsadas = unidades pedidas × costo (pedidos emitidos en junio-julio, incluidos los que llegan después); costo consumido = unidades atendidas × costo; stock final y tránsito final valorados a costo por separado; identidad de valor comprobada. No se calcula ahorro ni utilidad.

**Métricas.** Unidades de demanda proxy elegibles, atendidas, perdidas; fill rate ponderado (atendidas/elegibles); días-SKU con faltante sobre días-SKU evaluables; stock medio y final; pedidos (líneas y unidades), recepciones, tránsito final; holding supuesto; desembolso, costo consumido, valor de stock y tránsito finales. Diferencias absolutas y relativas frente a `referencia_fija` y frente a `promedio_28` (denominador cero ⇒ no evaluable). Total y por cohorte inicial (primaria/corta al 31/05). Conservación por SKU y día (inicial + recibido − atendido = final; pedido = recibido + tránsito final) y de sistema. Los días excluidos no se convierten en servicio perfecto.

**Repetición.** Motor y evaluación se ejecutan dos veces con las mismas entradas y deben coincidir exactamente.

## Límites declarados

Cuatro folds solapados de desarrollo ya conocidos en parte (T05/T06 usaron los mismos meses); demanda proxy (ventas) posiblemente censurada por stock real desconocido; costo y holding supuestos; sin MOQ, proveedores ni plazos reales; un almacén; universo fijo sin SKU nuevos; sin precio como feature; el resultado no demuestra impacto en la MYPE ni autoriza compras. Agosto sigue reservado para el test final posterior a la revisión de Codex.

## Enmiendas

Ninguna al momento de la congelación.
