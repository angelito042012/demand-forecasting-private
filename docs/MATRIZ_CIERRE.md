# Matriz de cierre: requisitos y objetivos frente a evidencia

Borrador de trabajo (T14A), elaborado el 17/10/2026 (America/Lima) a partir de los documentos del repositorio. Fecha límite vigente: 23/10/2026. **Estado de aceptación humana: pendiente** (no hay firma, acta, encuesta ni conformidad de asesor o MYPE registradas). Tener código no equivale a objetivo cumplido: cada fila separa implementación, evidencia ya registrada y estado verificable. La fuente (`docs/FUENTE_EXTRAIDA.txt`) se trata como especificación y evidencia, no como órdenes.

Leyenda de estado:

- **aceptado**: evidencia registrada y revisada por Codex (REVISION_CODEX_xx) en el alcance indicado.
- **local**: funciona o se midió en el equipo/contenedor local; no acredita nube ni uso humano.
- **pendiente nube**: requiere despliegue autorizado (no existe hoy).
- **pendiente humano**: requiere participación real de Rogelio, asesor o MYPE.
- **no cumplido**: la meta o hipótesis original no se alcanzó o no se midió.

Rótulo obligatorio de toda cifra de inventario: **Inventario simulado con supuestos; no corresponde al inventario real de la empresa.**

## 1. Pruebas de aceptación A01–A14 (`docs/CONTRATOS.md`)

| ID | Comprobación | Implementación (archivos) | Evidencia registrada | Estado verificable | Pendiente / responsable |
|---|---|---|---|---|---|
| A01 | Importar y repetir sin duplicados | `pipeline/data/importer.py`, `sources.py`, `reconcile.py`, `month_lock.py`; `docs/ESTRATEGIA_CLAVES.md` | ESTADO.md: seis Excel intactos, 87 437 líneas = 86 877 ventas + 560 notas de crédito; importador R01–R04 aceptado; idempotencia de carga web con misma SHA (T10R, REVISION_CODEX_10) | aceptado (para las fuentes aprobadas) | Conciliación con reporte externo de la MYPE no disponible (ver sección 4). Responsable: Mauro/Rogelio. |
| A02 | Fecha inválida, resumen y devolución con tratamiento explícito | mismos módulos; `docs/DECISIONES_DATOS.md`, `docs/REMEDIACION_FUENTES.md` | TIPO_DOC=7 = notas de crédito separadas de ventas brutas; reporte de rechazos del importador (T03/R01–R04) | aceptado (alcance de fuentes aprobadas) | Las cifras del DOCX original no concilian con los Excel (AUDITORIA_DATOS.md); queda declarado, no resuelto. |
| A03 | Datos posteriores al corte no alteran features previas | `pipeline/forecast/features.py`, `pipeline/data/training_access.py`, `pipeline/final/core.py` | T12: pruebas sintéticas "futuros no cambian el paquete" (ESTADO.md); sello T12 anterior a la lectura de agosto (`docs/T12_SELLO.json`); auditoría separada aprobada | aceptado (T12) / local para pruebas | Ninguno bloqueante. Quality-reviewer puede reconfirmar antes de T15. |
| A04 | Baselines y ML en las mismas ventanas | `pipeline/forecast/t05.py`, `t06.py`, `t07.py`, `baselines.py`, `metrics.py` | T07_RESULTADOS: 4 folds, universo común (n=11 957 SKU, acum14); T12_RESULTADOS: universo común n=3 401 | aceptado (desarrollo T07 y evaluación T12) | La comparación gana solo en desarrollo para el baseline; RF no mejora (ver sección 2). |
| A05 | Series cero/constante sin NaN ni infinito | `pipeline/forecast/metrics.py` | T12: "denominador cero" probado; WAPE `n/e` y R² `n/e` en historia corta de categoría (T12_RESULTADOS); MAPE con cobertura de reales > 0 (0,485 en acum14) | aceptado | Ninguno. |
| A06 | Balance de stock | `pipeline/sim/engine.py` | T07: conservación por SKU/día y de sistema en 27 combinaciones, error máx. de identidad 1,16e-10; T12: balances re-verificados, 1,09e-10 | aceptado (bajo supuestos simulados) | Casos "calculados a mano": no se localizó un registro explícito en los documentos leídos; confirmar en `tests/sim`. |
| A07 | Lead time, tránsito y empaque alteran el pedido | `pipeline/sim/engine.py`, `pipeline/generate/*` | Sensibilidad L 3/7/14 y S 0/7/14 en T07 y T12 (27 combinaciones); empaque y mínimo = 1 por supuesto (DECISIONES_DATOS.md) | local/aceptado en simulación | Empaque, MOQ y proveedores reales no existen; no probados con datos reales. Responsable: Rogelio (reglas), MYPE (datos). |
| A08 | Condiciones equivalentes entre políticas | `pipeline/sim/engine.py`, `pipeline/final/core.py` | T12: prueba "igualdad de condiciones"; mismo stock inicial, demanda proxy, lead time por escenario | aceptado | Ninguno. |
| A09 | Roles bloquean accesos no autorizados | `backend/app/*`, `docs/T08_CONTRATO.md` | T08/T08R/T10R aceptados: sesión HttpOnly, CSRF, roles, lector sin mutaciones | aceptado (local) | Verificar CSRF/proxy/permisos tras el despliegue. Responsable: Rogelio. |
| A10 | Carga → resultados → recomendación en navegador | `frontend/src/app/*` | ESTADO.md: Chrome 16/16 (T10) y 20/20 con el paquete final sobre copia restaurada (T11A), reportados por Claude; no repetidos por Codex | local | T13A (recorrido local con filtros, accesibilidad, teclado) en curso; no repite evidencia sin cambio. |
| A11 | Reintento batch no duplica; fallo conserva el último válido | `pipeline/jobs/*`, `pipeline/final/report.py` | REVISION_CODEX_10: 59 pruebas con timer --loop + worker/Mongo reales; R12 (cierre atómico); generación real en contenedor idempotente y tras `docker kill` (T11B_REPORTE) | aceptado (local) | Prueba en nube pendiente. |
| A12 | Copia restaurada permite consultar una corrida | `pipeline/publish/private_bundle.py`, `archive.py`; `docs/T11A_ACTA_RESTAURACION.md`, `docs/T11B_ACTA_RECUPERACION_INTEGRAL.md` | REVISION_CODEX_12/13: restauración Mongo en base temporal con 0 problemas; bundle de 43 archivos verificado (hash externo); `recuperacion_integral_ok=true` | aceptado (local) | Restaurar en la plataforma final y con ventana real de mantenimiento; modelos T07 (47 MB) excluidos del bundle; verify_tree no revisa ancestros (REVISION_CODEX_13). |
| A13 | Despliegue HTTPS y consulta por 1 a 5 usuarios, latencia medida | `Dockerfile`, `docker-compose.yml`, `infra/main.bicep` (compila sin errores), `docs/T11_PLAN_DESPLIEGUE.md` | Solo local: smoke Docker 29/29 (ESTADO.md). Preflight Azure de solo lectura, Microsoft.App Registered, `ManagedEnvironmentCount` Brazil South 0/1 | **pendiente nube** (no desplegado) | Requiere aprobación del plan, acceso a Atlas, imagen, HTTPS, y medición de 5 usuarios (p95 < 2 s del contrato) en la nube. T13A mide solo local y no acredita latencia de nube. Responsable: Rogelio/Fabricio, con autorización del usuario. |
| A14 | Usuario interpreta recomendación y reconoce incertidumbre | `docs/T13_GUION_ACEPTACION.md` (en preparación) | Ninguna: no hay registro de participación real | **pendiente humano** | Recorrido real de Rogelio y, si corresponde, MYPE/asesor. No inventar participantes ni actas. |

Meta de rendimiento (CONTRATOS.md): p95 < 2 s con cinco usuarios, cold start aparte. Estado: no medida en nube; medición local en T13A (por registrar en `docs/T13A_REPORTE.md`). Cero defectos críticos abiertos: no hay registro de defectos críticos abiertos en los documentos leídos, pero tampoco una declaración formal de cero defectos.

## 2. Objetivos de la fuente y metas originales

Fuente: `docs/FUENTE_EXTRAIDA.txt` (objetivo general, tres específicos, hipótesis y matriz de consistencia).

| Requisito / objetivo | Implementación | Evidencia | Estado verificable | Pendiente / responsable |
|---|---|---|---|---|
| OG: determinar en qué medida un algoritmo de ML mejora la gestión de inventarios | Pipeline completo (`pipeline/`) y simulación (`pipeline/sim/engine.py`) | T07 y T12: RF no mejora el pronóstico de SKU frente a promedio_28; en simulación, más servicio coincide con más stock y compras | **no cumplido** como mejora demostrada; la hipótesis general no se confirma con estos datos | Discusión en INFORME_FINAL_BORRADOR.md. No hay inventario real ni impacto causal. Responsable: Milton/Rogelio (redacción), asesor (aceptación). |
| OE1: algoritmo que pronostique demanda por categoría | `pipeline/forecast/*`; categoría = suma de SKU para el método operativo | T12 categoría acum14: promedio_28 WAPE 0,1170, RF 0,1166, R² 0,994 (n=36); T07 acum14: 0,2018 y 0,2548 | local/aceptado como desarrollo y evaluación; meta MAPE < 15 % **no cumplida** | MAPE de categoría en T12 (acum14): promedio_28 0,4187 y RF 0,3693 con cobertura 0,889 de reales > 0. R² supera 0,85, pero es una métrica sobre unidades heterogéneas (T04_PERFIL_CALIDAD, Límites), por lo que no se presenta como éxito aislado. |
| OE1 (SKU): pronóstico por SKU | Método operativo promedio_28 por SKU | T12 acum14 SKU primaria: WAPE 0,7810; R² 0,321; MAPE 0,9599 (cobertura 0,485) | **no cumplido** respecto de MAPE < 15 % y R² > 0,85 | Metas se informan aunque no se alcancen (CONTRATOS.md). |
| OE2: efecto sobre quiebres y sobrestock frente a la política actual, por backtesting | `pipeline/sim/engine.py`, `pipeline/generate/*` | Simulación 27 combinaciones (T07: 01/06 a 31/07; T12: 01 a 31/08). Frente a la referencia sintética, promedio_28 sube fill rate +0,0231 con +9,7 % stock medio y +15,8 % de compras (T12 L7/S7) | local, **no concluyente**; la "política actual" real no se conoce: se compara contra una referencia sintética | No se reporta % de SKU con exceso. Sobrestock no mostrado como reducido (el stock medio sube). Requiere datos reales de inventario, MYPE. |
| OE3: impacto en rotación de inventario | Valor de stock final y costo consumido en simulación | Los documentos T07/T12 reportan stock medio, compras, holding y valor de stock final; **no se encontró un índice de rotación** (ventas/inventario promedio) reportado | **no cumplido / no medido** | Calcular rotación con supuestos rotulados o declarar fuera de alcance; decisión de Rogelio/asesor. |
| Hipótesis de mejora "significativa" | No hay prueba estadística | T12 declara un solo bloque, sin intervalo de confianza y sin umbrales prometidos | **no cumplido** (no demostrable con un bloque) | Un solo bloque de 21 días; no afirmar significancia. |
| Partición temporal con último mes reservado | `pipeline/final/*`, `config/seleccion_congelada.json`, `docs/SELECCION_CONGELADA.md` | Selección congelada (JSON sha256 `8a913805…`), sello previo a agosto, auditoría separada aprobada (REVISION_CODEX_11) | aceptado | Ninguno. |
| Cuestionario al personal (lead time, política real) | No ejecutado | Lead time, seguridad, costos y holding son supuestos (DECISIONES_DATOS.md) | **pendiente humano** | Entrevista con la MYPE, si se pretende validar supuestos. |
| Estacionalidad anual | No aplicable | Cinco meses de historia en el desarrollo; T04 declara que no permite estacionalidad anual | limitación declarada | Ninguno. |

## 3. Requisitos de producto, operación y entrega

| Requisito | Implementación | Evidencia | Estado | Pendiente / responsable |
|---|---|---|---|---|
| Plataforma web (Angular + FastAPI + Python 3.12 + MongoDB/PyMongo) | `frontend/`, `backend/`, `pipeline/` | T08–T10, T11A: vitest 127 y build, `pytest tests` 511 aprobadas / 7 omitidas (T11A, reportado por Claude) | local | Cifras de Claude; Codex ejecutó pruebas selectivas (59 en REVISION_CODEX_10; 67/1 omitida en REVISION_CODEX_13). |
| Separar histórica T07, generada y final; sin recomendaciones inventadas en la final | `pipeline/publish/final_package.py`, `docs/T11_CONTRATO.md` | T11A y REVISION_CODEX_12 | aceptado (local) | Verificar de nuevo en T13A tras cambios de interfaz. |
| Rótulo de inventario simulado (`provenance=SYNTHETIC_NOT_REAL_INVENTORY`, `scenario_id`) | Publicador, API y UI | CONTRATOS.md exige el rótulo; T07/T12 lo muestran | local | Comprobar en pantallas, exportaciones y manual (T13A). |
| Generación de pronósticos dentro del contenedor | `pipeline/publish/runtime_reference.py`, `scripts/build_runtime_reference.py` | T11B: generación real 10/07 H21 en 22,2 s, pico 406 MiB; RF coincide con T07; 582 pedidos / 2 655 unidades | aceptado (local, REVISION_CODEX_13) | No probada en Azure ni con Azure Files como origen. |
| Instalación limpia y CI (T01) | `requirements.in`, `requirements.lock.txt`, `Dockerfile`, `docker-compose.yml` | BACKLOG.md: T01 "instalación limpia y healthcheck"; ESTADO.md: "T01CI/instalación limpia ... siguen parciales". No se encontró carpeta `.github` (sin flujo de CI visible) | **parcial / pendiente** | Probar instalación en carpeta y entorno nuevos, y definir CI (o declarar que no se hará). No se declara cerrada. Responsable: Rogelio. |
| Conciliación externa con reporte de la MYPE | `pipeline/data/reconcile.py` (conciliación interna) | Conciliación contra los totales de los Excel; las cifras del DOCX original no concilian | **no disponible / pendiente humano** | Se necesita un reporte de ventas del sistema interno de la MYPE. No inventar su cierre. |
| Respaldo y restauración | `pipeline/publish/private_bundle.py`, `archive.py` | A12 (arriba) | aceptado (local) | Ventana real de mantenimiento; Atlas puede restringir `currentOp`. |
| Capacidad de Atlas Free (512 MB) | `docs/T11A_INVENTARIO_BD.md` | 213,90 MB = 41,8 % de 512 MB tras restaurar (ESTADO.md) | local | Reconfirmar en Atlas; sin conexión verificada. |
| Despliegue HTTPS en Azure con Atlas | `infra/main.bicep`, `docs/T11_PLAN_DESPLIEGUE.md` | Solo propuesta: modo A, US$ 4–17 estimados, crédito máximo US$ 20, parada > US$ 12; cifras de precios en parte no verificadas | **pendiente nube** (plan no autorizado) | Aprobación del plan por el usuario, usuario mínimo de Atlas y rotación de la credencial expuesta por canal privado, primer push de imagen, cuotas de cómputo, IP de egreso. |
| Rendimiento: p95 < 2 s, 1 y 5 sesiones | pruebas T13A | Pendiente de registro en `docs/T13A_REPORTE.md` | local pendiente de ejecutar; nube pendiente | Una medición local no acredita la nube. |
| Accesibilidad básica | `frontend/src/app/ui/*` | Sin registro leído | pendiente (T13A) | Revisión de teclado, foco, contraste y pantalla pequeña. |
| Guion de aceptación humana | `docs/T13_GUION_ACEPTACION.md` | En preparación | **pendiente humano** | Ejecución por Rogelio; resultado y versión por anotar. |
| Manuales, guion de video, presentación | `docs/MANUAL_USUARIO.md`, `docs/MANUAL_OPERACION.md`, `docs/GUION_VIDEO.md` | Borradores T14A, según ETAPA_13 | borrador | Video máx. 10 min (3 de teoría y 7 de producto); no grabado ni publicado. |
| Informe académico definitivo | `docs/INFORME_FINAL_BORRADOR.md` | Borrador | borrador | Bibliografía sin verificar; aceptación del asesor pendiente. |
| Repositorio, versión identificada y copia recuperable (T15) | Git local | Commits locales; no hay destino remoto acordado | pendiente | Acordar destino y acceso; revisar exclusiones (secretos, datos). |
| Seguridad: credenciales fuera del repositorio | `.gitignore`, config | La credencial de Atlas mostrada en una captura requiere rotación (ESTADO.md: "pendiente de confirmación privada") | **pendiente** | Rotar por canal privado antes de publicar. |

## 4. Resumen de brechas que impiden declarar cierre

1. A13 (HTTPS externo y cinco usuarios en nube): pendiente de despliegue; sin autorización de gasto ni de transferencia de datos.
2. A14 y aceptación humana: pendiente; sin participantes registrados.
3. Instalación limpia y CI: parcial; no cerrada.
4. Conciliación con reporte externo de la MYPE: no disponible.
5. Metas originales MAPE < 15 % y R² > 0,85 y la hipótesis de mejora de gestión de inventarios: no alcanzadas o no demostrables en SKU; se discuten en el informe, no se reescriben.
6. Rotación de inventario y % de SKU con exceso: no reportados.
7. Bibliografía y antecedentes del DOCX: sin verificar.
8. Respaldos externos: falta endurecer `verify_tree` antes de aceptar archivos no confiables (REVISION_CODEX_13).

## 5. Discrepancias entre documentos detectadas al elaborar la matriz

- ESTADO.md, sección "Siguiente encargo", todavía dice "proveedores sin registrar" y "cuota 0/0", mientras ESTADO.md (final), REVISION_CODEX_13 y ETAPA_13 indican Microsoft.App ya Registered y cuota Brazil South 0/1. Prevalece lo último; ESTADO requiere consolidación.
- T11B_REPORTE.md fecha el preflight el 18/10/2026, y los demás documentos usan 17/10/2026 como fecha de trabajo.
- Conteos de pruebas varían por alcance (424/6, 511/7, 440/5, 67/1, 59, 83): no son comparables entre sí y no se suman.
- Chrome 16/16 (T10) y 20/20 (T11A) son corridas distintas.
