# Hechos y evidencias para alinear el informe académico (no es el informe)

Este documento solo entrega hechos verificados y su fuente; **no completa ni modifica el informe Word**. Fecha de los datos: 23/10/2026. Usar con las advertencias de cada sección.

## 1. Alcance y estado de la entrega
- Aplicación Angular + FastAPI + Python 3.12 + MongoDB (PyMongo) publicada en Azure Container Apps (Brazil South) con MongoDB Atlas Free; versión `t22g-a9119ae` (`docs/CONGELACION_ENTREGA_20261023.md`).
- Plan operativo de **noviembre de 2026**, versión 2: ventas y existencias al corte del **20/10/2026**, escenarios de entrega de 7 y 14 días, 50 productos con conteo físico informado (18/10/2026 17:00, almacén 1).
- **Fuera de alcance / trabajo futuro:** actualización operativa autónoma con nuevos cortes (requiere un procedimiento técnico; `docs/T22_VIABILIDAD_ACTUALIZACION_OPERATIVA.md`), ejecución de compras, medición de impacto en la empresa.
- **Aceptación humana final: pendiente. Credencial de Atlas expuesta: rotación pendiente.**

## 2. Datos
- 15 libros Excel (ventas marzo–octubre, compras marzo–setiembre); `octubre.xlsx` hasta el 20/10 con contraste registro a registro contra SQL Server (solo lectura): coincide (`docs/CONCILIACION_SQL_20261021.md`). Dataset operativo `plds-1f4717744dc3` (116.378 registros); el 21/10 (318 líneas, hasta 16:26) queda aparte y sin usar.
- Decisiones cerradas: TIPO_DOC=7 son notas de crédito (separadas de las ventas brutas); fechas 03/04, 12/04 y 07/06 de 2026 excluidas sin comprimir el calendario (`docs/DECISIONES_DATOS.md`).
- Ventas históricas del análisis académico: marzo–julio (86.877 líneas); agosto 2026 reservado como prueba final.
- Sin datos personales de clientes, vendedores ni proveedores en la nube.

## 3. Método y partición temporal
- Método operativo: **`promedio_28`** (media de las observaciones utilizables de los 28 días hasta el origen; ceros válidos incluidos, días ausentes excluidos; constante para el horizonte). En el plan v2: ventana 23/09–20/10.
- Partición temporal, último mes reservado, transformaciones ajustadas en entrenamiento, rezagos anteriores al corte; selección **congelada el 17/10/2026** antes de leer agosto (`docs/SELECCION_CONGELADA.md`, `config/seleccion_congelada.json`, sha256 `8a913805…ef8d`).
- La venta observada puede estar censurada por stock; no se infieren compras por SKU a partir de categorías sin método explícito.

## 4. Resultados de modelos (cifras literales; WAPE = razón, menos es mejor)
- **T06 (5 folds de desarrollo, SKU, 7 días):** cero 1,000 · último día 1,312 · naive semanal 1,057 · `promedio_28` 0,992 · Random Forest 1,058 (1/5 folds) · XGBoost 1,017 (2/5). Sin ganador ML en SKU. Categoría: RF 0,394 frente a `promedio_28` 0,403 (3/5; cumple regla); XGBoost 0,437 (no cumple). (`docs/T06_RESULTADOS.md`)
- **T07 (4 folds, SKU, acumulado 14 días):** `promedio_28` 0,873 · RF distribuido 0,929 · referencia fija 1,035 · cero 1,000; RF 0/4 folds favorables. (`docs/T07_RESULTADOS.md`)
- **T12 (agosto de 2026, una sola vez, SKU-almacén primaria n = 3.401, 14 días):** `promedio_28` **0,7810** · RF 0,7910 · cero 1,0000; sesgo relativo 0,020 / 0,030; RF no puede declararse ganador (un solo bloque). 10 días: 0,8165 / 0,8308; 21 días: 0,7512 / 0,7590. Historia corta (357 SKU), 14 días: RF 0,8009 frente a `promedio_28` 1,0618. SKU nuevos informados aparte (103 SKU, 353 unidades). (`docs/T12_RESULTADOS.md`, `T12_SELLO.json`)
- **Simulación de agosto (inventario simulado con supuestos; L = 7, S = 7, demanda elegible 23.836):** fill rate referencia fija 0,7561 · `promedio_28` 0,7792 · RF 0,7812; compras supuestas 267.440 · 309.792 · 326.713. Ventaja de servicio con más stock/compras **no se presenta como mejora**; no hay ahorro ni utilidad calculados.
- **Limitaciones literales:** un bloque de 21 días; demanda proxy; costos, plazo, seguridad y holding son supuestos; un almacén; sin MOQ ni proveedores; no demuestra impacto en la empresa.

## 5. Plan de noviembre (v2) — cifras verificadas en la versión publicada
- Parámetros configurados (no condiciones del proveedor): decisión 21/10, plazos 7/14, reserva 7 días, mínimo 1, múltiplo 1; sin pedidos adicionales registrados (supuesto sin confirmar).
- 50 productos: compra recomendada en 19 a 7 días y en 19 a 14 días; 10 «llega tarde» a 14 días; 13 con diferencia entre existencia reconstruida y sistema; pendientes de la empresa: compras 11452/11455 y las 13 diferencias.
- Recálculo independiente (sin importar el motor): 100 de 100 compras (50 × 7/14) coinciden con la API (`artifacts/private/t20/recalculo_independiente_v2.json`).
- **Producto 3110044:** previsión 18,214 en noviembre (0,607/día = 17 ÷ 28), existencia 0; 7 d: llega 28/10, compra 25, faltante antes 4,25 / mes 0; 14 d: llega 04/11, compra 21, faltante antes 6,679 / mes 1,821 (llega tarde); ventas atendibles 18,214 frente a 16,393.
- v1 (18/10, corte 30/09) conservado; existencias de v1 y v2 son de fechas distintas.

## 6. Calidad y seguridad
- Pruebas: frontend 312/312; backend 657 aprobadas y 5 omitidas en el checkpoint T20 (`docs/T20_REPORTE.md`), sin cambios de código de backend después; navegador: recorrido público 12/12, pantallas 36/36 · 20/20 · 22/22 · 7/7.
- Seguridad: HTTPS/HSTS, CSP, cookie HttpOnly/Secure/SameSite=Strict, CSRF, roles lector/administrador, límite de intentos por cliente con `TRUSTED_PROXIES=192.168.0.1/32` (medido y probado), sin `0.0.0.0/0`; credencial de Atlas expuesta: pendiente.
- Costos: US$ 1,544 observados hasta el 22/10/2026 (proyección ≈ US$ 3,5 al 23/10), crédito Azure for Students sin cargos de bolsillo.

## 7. Qué no debe afirmarse
Ahorro o mejora en inventario real; que Random Forest o XGBoost superen al método operativo; que el stock del plan sea un conteo físico nuevo; que no existan pedidos por recibir; que haya actualización autónoma de datos; que la aceptación humana o la rotación de la credencial estén completas.
