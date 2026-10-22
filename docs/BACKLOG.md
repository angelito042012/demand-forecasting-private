# Backlog de ejecución

**21/10 — R21 cerrado por Codex (ffa877f/5a3d535):** rutas y flujo del plan vigente revisados; 8 pruebas frontend dirigidas propias aprobadas. Sigue despliegue condicionado a presupuesto concreto, credito y accesos Atlas; verificar capacidad real con indices y mantener acceso limitado. Publicacion HTTPS y aceptacion humana aun pendientes. Ver cierre en REVISION_CODEX_20.md.

**21/10 — revision Codex T20:** checkpoint 3c94ab8/8a66457 revisado en alcance dirigido: 54 pruebas propias aprobadas y 100 compras sin diferencias al repetir recalculo contra evidencia guardada. Pendiente R21: Inicio y Ventas previstas aun llevan al ejemplo historico; conectar al plan v2 y preservar historicos en apartado academico. Leer REVISION_CODEX_20.md. Preparacion de nube puede continuar; presupuesto concreto, saldo de credito, publicacion verificada y aceptacion humana pendientes.

**18/10 — R19/R20 cerrados en revisión Codex (462e7f5):** reproducciones propias de fallo de purga y respuesta incierta conservan resultados (1/1); reintento reused. Recorrido lector listo para comenzar; aceptación humana pendiente. Navegador del ejecutor 23/25: quedan casos 17/18 de generación de variante/fechas para validación administrativa, sin acreditar 25/25 ni repetir suites completas. Ver cierre final de REVISION_CODEX_19.md.

**Revisión Codex de f0bae1d, 18/10:** fallo de purga posterior cerrado con reproducción propia (conserva 1/1 filas). R19 aún requiere proteger respuesta incierta de publicación: actualización aplicada seguida de AutoReconnect deja completed con 0/1 filas en reproducción propia. Ver última adenda de REVISION_CODEX_19.md y check_uncertain_publish.py. R20 cerrado; recorrido lector puede comenzar, generación administrativa y cierre técnico pendientes de ese caso. No repetir T19/T12/modelos.

**Revisión Codex posterior, 18/10 (a728017 / 667828b):** R20 cerrado con 11 pruebas propias aprobadas. R19 original atendido, pero pendiente caso residual de limpieza posterior a publicación: un error puede dejar completed sin resultados. Ver adenda final de REVISION_CODEX_19.md y reproducción privada check_post_publish.py. Corregir únicamente ese manejo de error, con regresión dirigida; no repetir T19/modelos/T12. Aprendizaje de lectura del plan existente puede comenzar; creación de planes y aceptación técnica final después de la corrección. Aceptación humana pendiente.

**18/10 — revisión Codex de T19 terminada:** integración y cálculos base entregados; pendientes R19 (publicación/limpieza por intento) y R20 (contrato real de pantalla, fechas, parámetros, serie y pedidos). Encargo `REVISION_CODEX_19.md`; 119 pruebas propias aprobadas, 100 recálculos sin diferencias, 4 regresiones frontend fallando y fallo de relevo reproducido. No repetir T19 completo/modelos/T12; corregir y revisar solo estos bloques antes de aceptación técnica y prueba humana.

**Nueva prioridad uno, 18/10 — T19:** ETAPA_19_CLAUDE.md preparado para implementar integración de 14 fuentes, previsión de noviembre y compra única para cubrir el mes (elección humana confirmada), 50 productos y plazos supuestos de 7/14 días. Incluye proyección desde conteo, consumo previo, fechas y faltantes; ensayo aislado en 8445. Implementación pendiente de Claude. Sin nuevos modelos/selección ni reejecución de T12; nube sin autorización. La prueba humana y los entregables finales permanecen, pero el cierre documental no sustituye T19.

**18/10 — R18 cerrado por Codex:** T18 aceptada técnicamente en alcance local; 39 pruebas propias aprobadas. Próximo: aceptación humana de Rogelio, actualización T14 (informe/manuales/matriz aún anteriores al conteo), preparación de sustentación/video y paquete T15, resolución de publicación conforme al alcance. No ampliar modelos/datos por rutina; 14 fuentes preparadas no equivalen a importación/estudio nuevo. Ver cierre de `REVISION_CODEX_18.md`. Los estados R18 pendientes de abajo son históricos.

**18/10, revisión Codex 18 terminada:** T18 requiere R18 antes de aceptación técnica: verificar correspondencia del CSV importado con el Excel revisado antes de primera carga. Encargo y reproducción en `REVISION_CODEX_18.md`; 22 validaciones propias aprobadas. Claude conserva ejecución; revisión posterior acotada, aceptación humana pendiente, sin nube/modelos/T12. Esta anotación sustituye la revisión todavía pendiente del párrafo siguiente.

**18/10, R19/R20 corregidos (a728017, 667828b); pendiente revisión de Codex y recorrido acompañado.** **18/10, etapa 19 entregada (commits 2e99534, 7dbb30b; docs/T19_REPORTE.md): plan de compra de noviembre en ens19/8445; pendiente acompañamiento y aceptación de Rogelio, revisión de Codex y ventas de octubre.** **18/10, R18 corregido (commit 616b5ef; docs/T18_REPORTE.md §5); pendiente revisión de Codex solo de ese cambio.** **Etapa 18 entregada (commit 464eb0c; docs/T18_REPORTE.md):** inventario informado integrado en ensayo aislado (puerto 8444); pendiente la prueba humana de Rogelio, la revisión de Codex y las ventas del 01/10 al corte del conteo. Sin nube.

**18/10, prioridad de datos:** preparación académica v1 completada por Codex; ver `PREPARACION_DATOS_ACADEMICA_V1.md`. Pendiente revisar/explicar el paquete y definir contrato de integración; no existe nuevo entrenamiento/importación autorizados. Mantener los saldos retrospectivos fuera del modelo y de T12. Revisión UX01R/R17 ya aceptada en REVISION_CODEX_17: las menciones de revisión pendiente abajo son históricas.

**UX01R entregado y aceptado localmente por Codex (REVISION_CODEX_17); pendiente la nueva prueba de comprensión de Rogelio.** R12–R16 aceptados localmente; no repetir. A13 (nube) y A14 (participación humana) pendientes; T14 debe reflejar las pantallas finales; T15 hasta el 23/10. Publicación en nube solo con autorización explícita.

Estado al 17/10: R12-R14 aceptados localmente; R15/R16 cerrados (T13B); demostración local activa en https://localhost:8443; publicación en nube pendiente de una única autorización (docs/T11_PLAN_DESPLIEGUE.md); aceptación humana (A14) y A13 pendientes; T14 final y T15 hasta el 23/10.

T01 está parcial; T03 aceptado para seis fuentes auditadas tras R01–R04. T02A tiene controles de importación pero no conciliación con reporte externo de la MYPE. T04–T07 aceptados como desarrollo; T08/T09/T10 aceptados para alcance local. Resultados T12 validados, cierre administrativo R11 pendiente; T11A es el encargo vigente, T11real/T13–T15 pendientes. Método operativo promedio_28; RF comparador, no ganador. Congelación registrada antes del test; no modificarla para acomodar resultados. Ver ANALISIS_Y_PLAN.md y DECISIONES_DATOS.md.

| ID | Entrega | Dependencia | Responsable / agente | Fecha objetivo | Aceptación |
|---|---|---|---|---|---|
| T01 | Adoptar repo, fijar versiones, estructura, CI básica | Ruta del repo o ausencia confirmada | Rogelio / principal | 17 | Instalación limpia y healthcheck |
| T02A | Ventas recibidas: conciliar y cerrar reglas de limpieza y uso | Archivos actuales + MYPE | Mauro / data-engineer | 17 | Manifiesto, conciliación, diccionario |
| T02B | Integrar escenario sintético ya generado y sus supuestos | reference_v1 y DECISIONES_DATOS.md | Rogelio | 17 | Procedencia visible, balance y cobertura |
| T03 | Importador validado e idempotente | T01, formato | Mauro / data-engineer | 17 | A01–A02 |
| T04 | Serie diaria, perfil y conciliación | T02A, T03 | Mauro / data-engineer | 18 | Totales y tratamiento de faltantes |
| T05 | Baselines, folds, features sin fuga | T04 | Blanca / forecasting | 18 | A03–A05 |
| T06 | RF y boosting, selección provisional; final pendiente | T05 | Blanca / forecasting | 19 | Registro de experimentos |
| T07 | Simulación de referencia sintética y política con ML | T02B, T05 | Rogelio / backend-inventory | 19 | A06–A08 |
| T08 | API autenticada y persistencia versionada | T01, contratos | Rogelio / backend-inventory | 20 | A09 |
| T09 | Pantallas conectadas, filtros y estados | T08; mocks antes | Fabricio / frontend | 20 | A10 |
| T10 | Flujo local aceptado tras T10R/6212f6a | T06–T08 | Fabricio y Rogelio | 20 | A11 local; revisión10 y59 pruebas |
| T11 | T11B vigente: R12–R14, generación en imagen/recuperación integral y preflight; despliegue pendiente | Accesos, T08–T10 | Fabricio | 21 | A12–A13 |
| T12 | Resultados validados por Codex11; cierre de checkpoints R11 pendiente | T06–T07 congelados; T10 aceptado | Blanca y Mauro | 21 | Predicción fija/simulación separadas, auditoría, sin re-selección |
| T13 | Revisión independiente y aceptación | T09–T12 | Fabricio / quality-reviewer | 22 | A14, sin críticos |
| T14 | Informe, manual, fuentes y video | Evidencia acumulada | Milton y equipo | 23 | Anexos y conclusiones verificables |
| T15 | Versión final y entrega | T13–T14 | Rogelio y Milton | 23, 18:00 Lima | Repositorio, URL, copia recuperable |

Antes de marcar una tarea completa: enlazar evidencia, pruebas ejecutadas, versión del código y limitaciones. Si una dependencia falta, marcar bloqueada y avanzar en una tarea independiente; no convertirla en completada por tener una pantalla de ejemplo.
