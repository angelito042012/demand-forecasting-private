# Backlog operativo — tareas pendientes post-entrega

Actualizado: 2026-11-07. Contexto: la entrega academica del 23/10 esta congelada
(`t22g-a9119ae`). Este backlog cubre el trabajo restante hacia la version v3 y el
cierre del 100% del entregable Capstone.

---

## Prioridad Alta — Datos e infraestructura

| # | Tarea | Que se necesita | Estado |
|---|---|---|---|
| 1 | Flujo de importacion operativa | CLI para recibir nuevos cortes de ventas+stock sin mongorestore | **HECHO** (commit `114efcd`, `scripts/import_operativo.py`, `politica_operativa` en config) |
| 2 | Levantar politica real de reposicion | Entrevista con el responsable de compras de la MYPE: como decide cuanto pedir, cada cuanto, que reglas usa, umbrales de minimo/maximo | No iniciado (depende de la empresa) |
| 3 | Resolver compras 11452/11455 y 13 diferencias de inventario | Respuesta de la empresa explicando discrepancias entre conteo+kardex y sistema. Sin codigo; es gestion | No iniciado (depende de la empresa) |
| 4 | Definir fuente de stock para nuevos cortes | Decision de la empresa: (A) paquete del kardex o (B) conteo fisico nuevo. Afecta como se usa la tarea 1 | No iniciado (depende de la empresa) |

## Prioridad Media — Evaluacion academica

| # | Tarea | Que se necesita | Estado |
|---|---|---|---|
| 5 | Diccionario de variables con procedencia | Codigo y config existentes | **HECHO** (`docs/DICCIONARIO_VARIABLES.md`) |
| 6 | Reproducir evaluacion T06/T07 | Tarea 5 (hecha). Documentacion ya esta en `T12_RESULTADOS.md` | **HECHO** (`docs/EVALUACION_T06_T07_METRICAS.md`) |
| 7 | Formalizar metricas del informe (MAPE, R²) | Tarea 6 (hecha). MAPE con cobertura, R² con definicion explicita | **HECHO** (incluido en EVALUACION doc) |
| 8 | Disenar comparacion justa: politica simulada vs propuesta | Tarea 2 (politica real levantada). Mismo horizonte, demanda, stock inicial y restricciones | No iniciado (bloqueado por tarea 2) |
| 9 | Definir y calcular indicador de rotacion | Movimientos reales del kardex + formula aprobada por asesor | No iniciado (bloqueado por tareas 3 y 4) |

## Prioridad Baja — Automatizacion y cierre

| # | Tarea | Que se necesita | Estado |
|---|---|---|---|
| 10 | Activar scheduler con trazabilidad | Tareas 1 y 4 estables. Habilitar scheduler (existe pero deshabilitado), reintentos, alertas | Parcial (tarea 1 hecha; bloqueado por tarea 4) |
| 11 | Rotar credencial de Atlas | Autorizacion del titular (Rogelio). Cambiar credencial, actualizar secret en Azure, verificar conexion | No iniciado (pospuesto post-23/10) |
| 12 | Manuales y recorrido del equipo | Actualizar manuales con cambios recientes; equipo reproduzca restauracion + caso 3110044 + explique limitaciones | Parcial (manuales existen, recorrido T13 pre-aceptacion hecho por Milton el 06/11) |

## Transversal

| # | Tarea | Que se necesita | Estado |
|---|---|---|---|
| 13 | Completar secciones del informe Capstone (OE01-OE03, Conclusiones, Recomendaciones) | Evidencia de tareas anteriores. No rellenar con promesas; solo con datos reales. Informe .docx en `documentacion/`. Guia de correcciones en `documentacion/Guia_de_correcciones_del_informe.md` (35 secciones) | No iniciado |
| 14 | Video de sustentacion (10 min: 3 teorica + 7 producto) | Formato ISC Capstone. App funcionando (local o nube) | No iniciado |

---

## Completadas en esta sesion (06-07/11)

| # | Tarea | Evidencia |
|---|---|---|
| S1 | Parametrizar constantes del pipeline | 3 archivos editados, commit `a409bd1` (sesion anterior) |
| 5 | Diccionario de variables | `docs/DICCIONARIO_VARIABLES.md` (sesion anterior) |
| 6+7 | Evaluacion y metricas formalizadas | `docs/EVALUACION_T06_T07_METRICAS.md` (sesion anterior) |
| T13 | Recorrido de aceptacion humana (pre-aceptacion Milton) | `docs/T13D_ACTA_RECORRIDO.md` (commit `6172649`), guion llenado (commit `e407ac2`) |
| 1 | CLI de importacion operativa | `scripts/import_operativo.py`, `politica_operativa` en config, fix de xlsx_check (commit `114efcd`) |

## Resumen: que se puede hacer YA (sin la empresa)

- **Tarea 12** — actualizar manuales y completar el recorrido del equipo
- **Tarea 13** — redactar resultados OE01-OE03 del informe con la evidencia existente
- **Tarea 14** — preparar el guion y estructura del video

## Que esta bloqueado por la empresa/asesor

- Tareas 2, 3, 4 (entrevistas y datos de la empresa)
- Tareas 8, 9 (dependen de 2 y 3)
- Tarea 10 (depende de 4 estable)
- Tarea 11 (autorizacion de Rogelio)
