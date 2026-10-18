# UX01 — Decisiones de diseño (mapa de navegación, glosario, jerarquía y advertencias)

Fecha: 17/10/2026. Complementa `docs/UX01_BRIEF.md` (que manda) y `ETAPA_16_CLAUDE.md`. Origen: observación de Rogelio, «No comprendió el uso en su primera visita» (observación abierta hasta que vuelva a probar; no es un defecto de cálculo demostrado ni una nueva aceptación). Nada de lo siguiente cambia cálculos, resultados, permisos, fechas ni advertencias esenciales: solo los reorganiza y los traduce.

## 1. Mapa de navegación

| Menú (texto visible) | Ruta (se conserva) | Quién | Qué responde |
|---|---|---|---|
| **Inicio** | `/inicio` (también `/`) | todos | Para qué sirve, qué datos hay y tres acciones |
| **Ventas previstas** | `/pronosticos` | todos | Unidades estimadas por producto/categoría y fechas |
| **Reposición simulada** | `/recomendaciones` | todos | Sugerencias del escenario simulado y cómo se calcularon |
| **Mis análisis** | `/corridas` | todos | Elegir qué resultado consultar (ejemplo, creados, evaluación, versiones anteriores) |
| Ventas registradas (Más) | `/resumen` | todos | Ventas reales ya cargadas (resumen secundario) |
| Evaluación de resultados (Más) | `/comparacion` | todos | ¿Qué tan cerca estuvieron las estimaciones de las ventas registradas? |
| Datos cargados (Más, solo lector) | `/cargas` | lector | Lista de archivos ya cargados (solo lectura) |
| Ayuda (Más) | `/ayuda` | todos | Primeros pasos, glosario, qué no hace la aplicación |
| Cargar datos (Administración) | `/cargas` | admin | Subir un Excel mensual en 3 pasos |
| Crear análisis (Administración) | `/crear-analisis` | admin | Generar un análisis nuevo (promedio de 28 días) |
| Estado del sistema (Administración) | `/sistema` | admin | Salud del servicio |

- Las rutas y el parámetro `run` no cambian: los enlaces existentes y las pruebas siguen valiendo. Todos los enlaces del menú conservan `run` (`queryParamsHandling="preserve"`), de modo que cambiar de pantalla, volver atrás o recargar mantiene el análisis elegido.
- El permiso real lo decide siempre el servidor; ocultar un enlace al lector es solo orientación. `/crear-analisis` o la carga, abiertas por un lector, muestran un mensaje de «solo administrador» y ninguna acción.
- Navegación: barra lateral en pantallas ≥ 900 px; en pantallas estrechas, botón «Menú» (aria-expanded) que despliega la misma lista y se cierra al navegar.
- «Elegido para consultar» (solo la interfaz) y «En uso por defecto» (el puntero del servidor, que no se modifica) son estados distintos y se rotulan distinto.

## 2. Glosario (texto principal → información técnica disponible aparte)

La tabla oficial vive en `frontend/src/app/core/ux-text.ts` (`GLOSSARY`) y se muestra en **Ayuda**:

| Texto principal | Técnico (en detalles / filtros avanzados / metodología) |
|---|---|
| Análisis | corrida, `run_id`, tipo interno |
| Ventas utilizadas hasta | corte / origen (fecha exacta) |
| Período estimado · día de la previsión | horizonte / `h` |
| Código del producto | SKU |
| Por recibir (simulado) | tránsito / `in_transit` |
| Promedio de los últimos 28 días | `promedio_28` |
| Modelo experimental | RF distribuido (Random Forest y desagregación) |
| Comparación con ventas registradas | backtest, folds, metodología, métricas completas |
| Tipo de historial | cohorte (códigos en filtros avanzados) |
| Ejemplo de julio / Evaluación de agosto | T07 / T12 (el nombre se **deriva de las fechas que publica la API**: `analysisName()`) |
| En uso por defecto | corrida activa (puntero original, intacto) |

Productos: «Producto 1010004 · Higiene capilar» (código y categoría tal como los publica la API). No se inventan nombres comerciales ni se releen los Excel. Estados de trabajo en palabras sencillas (`jobStatusWords`): esperando turno, en curso, terminado, no se pudo completar; el código y el texto originales quedan en detalles.

## 3. Jerarquía y qué se ve frente a qué se pliega

Siempre visible en el contenido principal:
1. **Franja de contexto** (shell): «Ejemplo con datos históricos de 2026. El inventario es simulado; no representa las existencias actuales».
2. **Barra de análisis** (`app-analysis-bar`): nombre derivado, estado («En uso por defecto», «Seleccionado para consultar», «Versión reemplazada»), «Ventas utilizadas hasta», período estimado y «Cambiar de análisis».
3. **Aviso de simulación** junto a cada resultado con stock/por recibir/costos/pedidos: la frase exacta «Inventario simulado con supuestos; no corresponde al inventario real de la empresa».
4. **Errores reales y versiones reemplazadas** (aviso destacado y breve: «Esta versión fue reemplazada. No uses sus sugerencias», con enlace a la corregida).
5. **Advertencias esenciales de la evaluación**: WAPE no es exactitud (con el valor concreto y su lectura), categoría = suma de unidades heterogéneas, un solo bloque de 21 días sin declarar ganador, evaluación sobre datos históricos (no pronostica octubre), «no evaluable» ≠ cero, observado `null` ≠ cero, sin recomendaciones en la evaluación.

Plegado (siempre localizable, nunca eliminado): identificadores (`run_id`, hash, sello, fases, semillas, UTC), tipo interno, `h`, cohortes y códigos, columnas RF/cero, métricas completas (folds, escenarios, 27 combinaciones), cálculo completo con precisión racional, texto técnico del servidor, procedencia (`SYNTHETIC_NOT_REAL_INVENTORY`, `OBSERVED_EXCEL`), motivo largo de una versión reemplazada.

## 4. Conservación (trazabilidad de «qué se movió»)

| Antes | Ahora |
|---|---|
| Banner `run-banner` con corte y «Corrida antigua (>7 días; umbral supuesto)» | Barra de análisis: «Ventas utilizadas hasta … (hace N días; datos históricos, no las ventas de hoy)»; el umbral de 7 días ya no se usa como aviso, la antigüedad se lee en palabras |
| `app-superseded-banner` | Aviso breve en la barra + motivo plegado; enlace a la corregida |
| `app-sim-notice` (detalle técnico) | Se conserva junto a los resultados de Reposición y en la evaluación de reposición |
| `FinalWarnings` (4 textos de la API) | Se conservan visibles en Evaluación; en Ventas previstas de la evaluación, versión breve + «Ver advertencias» |
| Tabla con 10 columnas de pronósticos | 3–4 columnas por defecto; resto en «Comparar métodos» |
| Tabla de 8 columnas de recomendaciones | 4 columnas; por recibir y valor supuesto en el detalle |
| Detalle de corrida con JSON, hashes y fases | «Detalles técnicos» plegado por análisis |
| Resumen de ventas y calidad de datos como bienvenida | «Ventas registradas» (menú «Más») |
| Pasos de cálculo (`calcSteps`) | Resumen en 3 pasos sencillos + «Ver cálculo completo y supuestos» (mismos 8–9 pasos, misma aritmética) |

## 5. Reglas de implementación (acuerdo entre pantallas)

- Una sola lista de análisis: `RunsStore` (`core/runs-store.ts`; una petición a `/runs`). Las pantallas no llaman a `api.runs` por su cuenta; tras crear un análisis, `RunsStore.refresh()`.
- Cada pantalla de resultados muestra `<app-analysis-bar [runId]="choice.id()" />` y usa `<app-page-header>` (un `<h1>` por pantalla). Textos de interfaz solo de `ux-text.ts` y de plantillas; nada escrito para tres registros concretos.
- Conservar los `data-testid` existentes de los datos de negocio y las pruebas de: permisos, selección entre análisis, resultados adversos, null≠0, no evaluable, sin snapshot, final sin recomendaciones, versiones reemplazadas, paginación/filtros, errores.
- Totales: nunca sumar una página como total global; usar `total` del servidor o no mostrar total.
- Un único botón primario (`.btn`) por pantalla; los demás `.secondary`. Tipografía ≥ 16 px; sin ancho fijo que provoque desplazamiento horizontal de la página.
- Acciones: ningún elemento clicable decorativo; consultar nunca crea trabajos ni ejecuta modelos.

## 6. Extensión mínima de la API (única)

`GET /recommendations?no_orders=true` (solo SKU con inventario simulado y pedido sugerido 0; incompatible con `only_orders`; no incluye «sin inventario»). Motivo: la vista «Sin necesidad de reponer en el ejemplo» debe filtrarse **en el servidor** (no sobre la página recibida) y ningún filtro existente la expresa. Es una lectura sobre los mismos datos, con las mismas reglas de rol/corrida; prueba en `tests/backend/test_data_api.py::test_recommendations_no_orders_view`. No se alteran contratos científicos.
