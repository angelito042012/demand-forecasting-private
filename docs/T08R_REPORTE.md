# T08R: corrección de R05 y R06, presentación y verificación

17/10/2026, Lima. Corrige T08 (960638d) según `docs/REVISION_CODEX_07.md`. No se reentrenó T06/T07, no se abrió agosto, no se modificó la selección congelada ni se inició T10. Inventario simulado con supuestos; no corresponde al inventario real de la empresa.

## R05: precisión de las recomendaciones
- **Reproducción previa**: `tests/publish/test_r05_reproduccion.py` falló antes de corregir (SKU 12040025: objetivo 10 en lugar de 9; registro `artifacts/private/t08r/r05_fallo_previo.log`).
- **Causa**: la media se tomaba del CSV T07 (10 cifras significativas) y luego se aplicaba techo tras redondear a 9 decimales; no elimina el error.
- **Corrección**: `pipeline/publish/signals.py` calcula suma exacta y días útiles de la ventana de 28 días (ceros válidos, máscaras y días sin registros fuera) desde ventas aprobadas ≤ 10/07; objetivo = techo(21 · suma / días) en aritmética racional, sin épsilon. Se persisten `sum_28`, `days_28`, `mean_28_exact`, `target_raw_exact` y la ventana; el CSV solo controla coherencia (1e-9). T07 (métricas, CSV, NPZ, modelos) no se tocó; los pronósticos históricos siguen siendo la evidencia original.
- **Identidad y reemplazo**: la identidad incluye versión `t08r-1`, referencia aprobada, fingerprint de catálogo/fuentes y de señales. Se publicó la corrida **`hist-20260710-4ea348836e35`** y la anterior quedó `superseded` (sin borrar ni alterar hijos; `quality_issue`, `superseded_by`; la API y la UI la marcan no válida).
- **Auditoría independiente** (`scripts/audit_recommendations.py`; `docs/T08R_AUDITORIA.json`): 3 347 recomendaciones, 0 diferencias; 582 sugerencias positivas / 2 655 unidades. La corrida anterior tenía 640 / 2 773: 225 objetivos y 118 pedidos inflados en una unidad. Los 300 sin snapshot siguen con valores nulos.
- **Anclaje**: manifiesto y métricas T07 se comparan con el commit aprobado `5790103` (contenido normalizado) y la configuración; fingerprint y fuentes del fold se exigen antes de escribir. Pruebas con métricas/fuentes alteradas y señales incoherentes.

## R06: proxy y límite de login
Uvicorn local arranca con `--no-proxy-headers`. Pruebas con un servidor Uvicorn real (`tests/backend/test_proxy_headers_chain.py`): con la opción, variar `X-Forwarded-For` no elude el límite (401×5 → 429); control con proxy activo reproduce el defecto. En navegador, por el proxy real de Angular: 401,401,401,401,401,429,429,429. Contrato de proxy confiable en `T08_CONTRATO.md` §8. **Pendiente declarado**: el conteo del límite («contar y luego insertar») y el *lease* de publicación no son atómicos/renovables: condición antes de exposición pública, T10 y T11; no se afirma resistencia a ráfagas.

## Presentación
Comparación con escenario principal y tres políticas (servicio %, faltantes, stock medio, compras PEN, diferencias frente a promedio_28), selectores de L/S/cohorte y de nivel/cohorte/horizonte/fold con todos los resultados disponibles (también los desfavorables y el control cero); altura de la página 2 317 px (antes 29 829); explicación única del pedido con números formateados; detalles técnicos plegados; banner de corrida sustituida; estilos globales. Durante la verificación se halló y corrigió un defecto de integración: la UI esperaba `sum_28` numérico y la API lo publica como texto exacto.

## Verificación
- pytest sin los tests de datos reales costosos: 254 aprobadas, 3 omitidas (las tres con `RUN_REALDATA=1` repetirían T07, no se ejecutaron). `ruff` limpio (salvo el aviso SIM113 suprimido en la auditoría).
- Frontend: build correcto, 79 pruebas aprobadas.
- E2E navegador real (Chrome, Playwright-core) 16/16: login, corridas nueva/sustituida, vista de la antigua, 582 sugerencias, SKU 12040025 (3/7, objetivo 9, pedido 0) y 12010025 (objetivo 3, pedido 2), comparación filtrada, logout, límite con XFF por el proxy real y API caída. Capturas y logs privados: `artifacts/private/t08r/`.

## Límites
Demostración local en HTTP; recomendaciones hipotéticas con inventario simulado; corrida de 99 días de antigüedad; sin carga web (T10), despliegue/restauración (T11) ni ejecución final (T12); sin pruebas de carga ni accesibilidad medida; la comprobación en navegador no es aceptación humana.
