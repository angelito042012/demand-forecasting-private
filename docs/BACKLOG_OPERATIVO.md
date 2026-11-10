# Backlog operativo — tareas pendientes post-entrega

Actualizado: 2026-11-10 (revision final). Contexto: la entrega academica del 23/10 esta congelada
(`t22g-a9119ae`). Este backlog cubre el trabajo restante hacia la version v3 y el
cierre del 100% del entregable Capstone.

---

## Prioridad Alta — Datos e infraestructura

| # | Tarea | Que se necesita | Estado |
|---|---|---|---|
| 1 | Flujo de importacion operativa | CLI para recibir nuevos cortes de ventas+stock sin mongorestore | **HECHO** (commit `114efcd`, `scripts/import_operativo.py`, `politica_operativa` en config) |
| 2 | Levantar politica real de reposicion | Entrevista con el responsable de compras de la MYPE: como decide cuanto pedir, cada cuanto, que reglas usa, umbrales de minimo/maximo | **DOCUMENTADO CON SUPUESTOS** (`docs/POLITICA_REPOSICION_PROPUESTA.md`): politica propuesta por el equipo, etiquetada como no validada; pendiente confirmacion de la empresa |
| 3 | Resolver compras 11452/11455 y 13 diferencias de inventario | Respuesta de la empresa explicando discrepancias entre conteo+kardex y sistema. Sin codigo; es gestion | **DOCUMENTADO CON ESCENARIOS** (`docs/DISCREPANCIAS_INVENTARIO_ESCENARIOS.md`): 3 escenarios de resolucion por tipo; decision actual = existencia reconstruida con pendientes marcados |
| 4 | Definir fuente de stock para nuevos cortes | Decision de la empresa: (A) paquete del kardex o (B) conteo fisico nuevo. Afecta como se usa la tarea 1 | **DOCUMENTADO CON RECOMENDACION** (`docs/RECOMENDACION_FUENTE_STOCK.md`): equipo recomienda Alt. A (kardex) + reconteo puntual de 13; pendiente decision de la empresa |

## Prioridad Media — Evaluacion academica

| # | Tarea | Que se necesita | Estado |
|---|---|---|---|
| 5 | Diccionario de variables con procedencia | Codigo y config existentes | **HECHO** (`docs/DICCIONARIO_VARIABLES.md`) |
| 6 | Reproducir evaluacion T06/T07 | Tarea 5 (hecha). Documentacion ya esta en `T12_RESULTADOS.md` | **HECHO** (`docs/EVALUACION_T06_T07_METRICAS.md`) |
| 7 | Formalizar metricas del informe (MAPE, R²) | Tarea 6 (hecha). MAPE con cobertura, R² con definicion explicita | **HECHO** (incluido en EVALUACION doc) |
| 8 | Disenar comparacion justa: politica simulada vs propuesta | Tarea 2 (politica real levantada). Mismo horizonte, demanda, stock inicial y restricciones | **DISEÑO METODOLOGICO + CODIGO** (`docs/COMPARACION_POLITICA_SIMULADA_VS_PROPUESTA.md` + `scripts/compare_policies.py`): marco de comparacion con variables controladas, metricas y protocolo; script usa `pipeline.sim.engine` con mismo stock/demanda; no ejecutado (requiere ventas de noviembre) |
| 9 | Definir y calcular indicador de rotacion | Movimientos reales del kardex + formula aprobada por asesor | **DEFINIDO + CODIGO** (`docs/INDICADOR_ROTACION.md` + `scripts/calc_rotation.py`): formula, variantes, interpretacion; script calcula rotacion por producto y categoria desde MongoDB; pendiente validacion con asesor |

## Prioridad Baja — Automatizacion y cierre

| # | Tarea | Que se necesita | Estado |
|---|---|---|---|
| 10 | Activar scheduler con trazabilidad | Tareas 1 y 4 estables. Habilitar scheduler (existe pero deshabilitado), reintentos, alertas | **CONFIGURACION DOCUMENTADA + CODIGO** (`docs/ACTIVACION_SCHEDULER.md` + flag `--operational` en `pipeline/jobs/scheduler.py`): soporte de `politica_operativa` (origen sin tope de julio); 19 tests pasan; no activado (requiere fuente de stock estable) |
| 11 | Rotar credencial de Atlas | Autorizacion del titular (Rogelio). Cambiar credencial, actualizar secret en Azure, verificar conexion | **PROCEDIMIENTO LISTO** (`docs/PROCEDIMIENTO_ROTACION_CREDENCIAL.md`): 4 pasos documentados, checklist de prerrequisitos; pendiente autorizacion y acceso de Rogelio a Atlas |
| 12 | Manuales y recorrido del equipo | Actualizar manuales con cambios recientes; equipo reproduzca restauracion + caso 3110044 + explique limitaciones | **HECHO** (manuales actualizados 10/11: import_operativo en MANUAL_OPERACION, setup+limitaciones en DEMOSTRACION_3110044, refs en MANUAL_USUARIO; pre-aceptacion Milton 06/11) |

## Transversal

| # | Tarea | Que se necesita | Estado |
|---|---|---|---|
| 13 | Completar secciones del informe Capstone (OE01-OE03, Conclusiones, Recomendaciones) | Evidencia de tareas anteriores. No rellenar con promesas; solo con datos reales. Informe .docx en `documentacion/`. Guia de correcciones en `documentacion/Correcciones_Informe_T13.md` (35 secciones) | **HECHO** (35 correcciones aplicadas al informe 0911→1011, marco metodologico con T13-eval, compromisos eticos de Milton escritos; residuales menores delegados al equipo) |
| 14 | Video de sustentacion (10 min: 3 teorica + 7 producto) | Formato ISC Capstone. App funcionando (local o nube). Guion existente en `docs/GUION_VIDEO.md` | No iniciado (guion listo, falta grabar) |

---

## Completadas en esta sesion (06-07/11)

| # | Tarea | Evidencia |
|---|---|---|
| S1 | Parametrizar constantes del pipeline | 3 archivos editados, commit `a409bd1` (sesion anterior) |
| 5 | Diccionario de variables | `docs/DICCIONARIO_VARIABLES.md` (sesion anterior) |
| 6+7 | Evaluacion y metricas formalizadas | `docs/EVALUACION_T06_T07_METRICAS.md` (sesion anterior) |
| T13 | Recorrido de aceptacion humana (pre-aceptacion Milton) | `docs/T13D_ACTA_RECORRIDO.md` (commit `6172649`), guion llenado (commit `e407ac2`) |
| 1 | CLI de importacion operativa | `scripts/import_operativo.py`, `politica_operativa` en config, fix de xlsx_check (commit `114efcd`) |
| 12 | Manuales y recorrido del equipo | Manuales actualizados (10/11): import_operativo en MANUAL_OPERACION, setup+limitaciones en DEMOSTRACION_3110044, refs nuevas en MANUAL_USUARIO |
| 13 | Informe Capstone completo | 35 correcciones aplicadas (Correcciones_Informe_T13.md), marco metodologico con T13-eval, compromisos eticos de Milton |
| 2 | Politica de reposicion propuesta | `docs/POLITICA_REPOSICION_PROPUESTA.md` — supuestos del equipo, no validada |
| 3 | Discrepancias con escenarios | `docs/DISCREPANCIAS_INVENTARIO_ESCENARIOS.md` — 13 discrepancias + compras 11452/11455 |
| 4 | Recomendacion fuente de stock | `docs/RECOMENDACION_FUENTE_STOCK.md` — Alt. A kardex recomendada |
| 11 | Procedimiento rotacion credencial | `docs/PROCEDIMIENTO_ROTACION_CREDENCIAL.md` — listo para ejecutar |
| 8 | Comparacion justa politica simulada vs propuesta | `docs/COMPARACION_POLITICA_SIMULADA_VS_PROPUESTA.md` + `scripts/compare_policies.py` — diseno metodologico y script de simulacion |
| 9 | Indicador de rotacion | `docs/INDICADOR_ROTACION.md` + `scripts/calc_rotation.py` — definido con script de calculo |
| 10 | Activacion scheduler | `docs/ACTIVACION_SCHEDULER.md` + flag `--operational` en scheduler.py — configuracion documentada y codigo |

## Residuales del informe Capstone (correccion 34 — delegados al equipo)

Referencia: `documentacion/Correcciones_Informe_T13.md` §34. Estos puntos NO son tareas tecnicas;
son redaccion/formateo que cada integrante debe completar antes de la evaluacion del 13/11.

| Pendiente | Responsable | Notas |
|---|---|---|
| Abstract en ingles | Cualquier integrante | Traducir el resumen final |
| Matriz de trazabilidad de requisitos | Equipo | Vincular requisito → modulo → prueba → evidencia → estado |
| Cronograma y EDT | Equipo | Fechas planificadas vs ejecutadas; no inventar hitos |
| Compromisos eticos individuales | Cada integrante (el suyo) | Milton ya escribio el suyo; faltan los demas |
| Anexos 1-2 (video + repositorio) | Tras grabar video (tarea 14) | Enlace real, no placeholder |
| Anexos 3-4 (instrumentos y respuestas) | Equipo | Incorporar o retirar referencias |
| Indices de tablas y figuras | Ultimo paso | Renumerar figuras (se reutiliza «Figura 1») |
| Correccion 24: imagen matriz de riesgos | Equipo | Editar archivo fuente de la imagen y reinsertarla |

## Resumen: que se puede hacer YA (sin la empresa)

- **Tarea 14** — grabar el video de sustentacion (guion en `docs/GUION_VIDEO.md`, checklist lista)
- **Residuales del informe** — redaccion individual y formateo (ver tabla arriba)

## Que esta bloqueado por la empresa/asesor (documentado con supuestos para la evaluacion del 13/11)

- Tareas 2, 3, 4: documentadas como propuestas/escenarios del equipo, pendientes de validacion real
- Tareas 8, 9 (dependen de 2 y 3): documentadas con diseno metodologico/definicion + scripts listos; ejecucion completa requiere datos de la empresa
- Tarea 10 (depende de 4 estable): configuracion documentada + codigo con `--operational`; activacion requiere fuente de stock estable
- Tarea 11: procedimiento listo, falta autorizacion y acceso de Rogelio
