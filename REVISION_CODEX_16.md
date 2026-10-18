# Revisión Codex16: UX01

Entrega revisada: 96adbf2, 0478868, 269a9cd y 272ca78. Fecha: 17/10/2026 America/Lima. No se leyeron contraseñas, no se inició sesión en la demo, no se modificó su base ni se detuvieron servicios. No se repitieron ciencia, evaluación final, build de producción ni E2E completo.

## Resultado

Inicio y reposición mejoran de forma visible la orientación. Integridad de cifras, aritmética y filtro nuevo aceptables en el alcance revisado. La revisión encuentra un fallo de recuperación de la lista de análisis (R17), reproducido con una prueba propia, y ajustes de claridad especialmente en Evaluación. No se declara aprobación humana: Rogelio debe volver a probar. Publicación aún no autorizada.

## Comprobaciones propias y evidencia

- Revisión visual de capturas reales: Inicio, detalle de reposición y Evaluación. Inicio ahora ofrece tres tareas; reposición separa sugerencia breve y cálculo completo. Evaluación sigue mostrando, antes de detalles plegados, varias advertencias, conclusión, hallazgo primario, tabla y reglas técnicas repetidas; necesita jerarquía adicional para el objetivo UX solicitado.
- Backend: `tests/backend/test_data_api.py`, **35 aprobadas, 0 omitidas, 8,50s**, un aviso deprecación Starlette/httpx. Incluye `no_orders`, paginación, permisos, validación/inyección, barreras temporales y lecturas sobre base temporal. Evidencia: `artifacts/private/codex_review16_backend.xml/.log`.
- Frontend: **81 pruebas existentes UX aprobadas** en tres archivos. La prueba propia R17 falla como se esperaba al reproducir el defecto: **82 ejecutadas, 81 aprobadas, 1 fallida**. Evidencia JUnit en `artifacts/private/codex_review16_frontend.xml`. No presentar esa tanda como verde.
- Primer intento frontend no ejecutó las pruebas por EPERM en el directorio temporal del sandbox; evidencia separada `codex_review16_frontend_sandbox.xml`. Repetido con TEMP/TMP en directorio propio de workspace: se ejecutaron las82 pruebas. No es un defecto de la aplicación.
- Prueba temporal retirada de frontend después de ejecutarla y guardada en `artifacts/private/codex_review16_probe.spec.ts`; no se deja código productivo ni suite del usuario modificados. Claude puede incorporarla con nombre definitivo al corregir R17.
- Evidencias212frontend/167backend/51E2E de la entrega son de Claude, revisadas como tales, no repetidas en su totalidad por Codex.

## R17, P2: reintento automático sin límite y error invisible del historial

`ui/analysis-bar.ts` crea `effect(() => this.store.ensure())`. `RunsStore.ensure()` lee el estado reactivo y, cuando está en error, llama a reload. Así cada fallo de /runs reactiva el efecto y crea una nueva petición sin pausa, backoff ni acción humana. La barra no tiene rama de error visible.

Reproducción propia con HomePage real y HttpTestingController: primera respuesta /runs503; al estabilizar aparece otra petición /runs antes de pulsar nada. La aserción esperaba0 y obtuvo1. Si la nueva petición falla, vuelve a ocurrir. La prueba existente de RunsPage no cubría la barra montada en Inicio.

Corregir la carga inicial y el reintento para que un fallo persistente quede visible con botón de Reintentar, sin bucle reactivo. Distinguir servidor no disponible de análisis inexistente; no sustituir el seleccionado por otro. Comprobar Inicio y Ventas previstas; una petición inicial, cero reintentos espontáneos y una petición al reintentar explícitamente. Reusar una sola carga compartida cuando varios componentes consumen el historial.

Límites no bloqueantes de esta demo: RunsStore conserva datos entre sesiones y solo lee primera página de50. Antes de escalar historial o cambiar de usuario, invalidar caché según identidad y resolver el ID seleccionado fuera de esa página mediante lectura específica/paginación; no afirmar «no existe» solo porque no está entre los primeros50. La demo actual tiene pocos análisis; no requiere migración ni repetición científica.

## Integridad aceptable

- no_orders filtra order_qty=0 antes de count/paginación y excluye null/sin_snapshot; only_orders incompatible422 para las corridas con recomendaciones.
- simpleSteps usa valores del cálculo exacto anterior, no fórmulas redondeadas nuevas. Se mantienen alertas de incoherencia y ausencias.
- Parámetro run conservado y final sin pedidos ajenos por sustitución silenciosa; versiones anteriores accesibles y señaladas. Cifras adversas/control/cohortes/27simulaciones disponibles; no hay ganador ni impacto real inventados en el alcance revisado.

## Textos a precisar sin recalcular nada

1. `comparison.page.ts::scopeText`: «promedio de4bloques» es incorrecto: el agregado suma estadísticas y calcula la métrica conjunta. Usar «resultado agregado de4bloques».
2. Glosario ux-text: «últimos28días con ventas registradas» puede excluir ceros en la interpretación del lector. Explicar ventana de calendario, días válidos que incluyen ventas cero y días excluidos, sin afirmar que toda serie tiene28días de historia.
3. Análisis generado: no afirmar que no existen ventas posteriores; lo correcto es que ese análisis no incluye evaluación contra ventas registradas, por diseño.
4. Evaluación final: alcance de métricaH14 corresponde a01–14agosto; el bloque disponible es01–21. Mostrar ambos períodos con etiquetas distintas, sin adjudicar el WAPEH14 al bloque completo.
5. Guion de aceptación conserva «debe listar tres corridas», pero E2E creó un análisis adicional. Verificar presencia de los tipos/IDs esperados y puntero, no un número fijo falso. Detallar las advertencias donde se muestra la información relevante, conservando el significado y los valores originales.

## Continuación

ETAPA_17_CLAUDE.md: R17 y ajustes breves de Evaluación/lenguaje; demo conservada y nueva prueba humana. No crear recursos, transferir datos ni pedir nuevo acceso Azure. Mantener el avance UX, sin reiniciar el diseño ni ampliar stack/cálculos.
