# Revision Codex 20 — checkpoint T20

21/10/2026, Lima. Entrega 3c94ab8 + 8a66457. Revision acotada de actualizacion local; no certifica nube ni aceptacion humana.

## Verificaciones propias

- Leidos reporte/contrato T20, importadores dataset_v2 y reconstructed, cambios en motor/publicador/API y navegacion principal.
- 19 pruebas puras de reconstruccion aprobadas; 21 de dataset v2/caso manual de motor aprobadas; 14 frontend t20-v2 aprobadas: 54 en total. Evidencia privada codex_review20. Primer intento de las 19 no ejecuto aserciones por faltar carpeta padre temporal; ejecucion repetida valida en inventory_retry.xml. No atribuirle fallos de producto.
- Reejecutado el recalculo independiente del ejecutor, sin importar motor, contra CSV y respuesta API guardada: 100 compras, cero diferencias; 19 productos con compra por cada plazo. Es reejecucion del script del ejecutor, no un segundo metodo propio ni consulta API en vivo. Script/resultados privados codex_review20/recalculate.py y recalculation.json.
- Los 657/162/294 y 16 navegador del reporte son evidencia del ejecutor. No reejecutados completos. No se operaron SQL, Mongo, Docker, Azure o Atlas; no se modifico aplicacion.

## R21 [P2] — flujo principal aun conduce al ejemplo historico

frontend/src/app/app.html mantiene nav-ventas-previstas -> /pronosticos. forecasts.page.ts utiliza RunsStore y api.forecasts con run_id, no el plan v2 de noviembre. home.page.ts mantiene el encabezado «Explora las ventas previstas y una simulacion de reposicion», la descripcion de datos del ejemplo, la barra de analisis historica y accesos principales al ejemplo. app.html muestra el aviso global «Ejemplo con datos historicos de 2026» tanto en Inicio como en /pronosticos. Solo mover Reposicion simulada al menu Mas no completa el flujo principal solicitado.

Consecuencia: tras iniciar sesion o pulsar Ventas previstas, el usuario encuentra los analisis historicos en vez de la previsión de noviembre ya calculada en Compra recomendada. No borrar las advertencias de esos analisis ni renombrar su contenido como noviembre.

Correccion acotada: Inicio y Ventas previstas deben consultar/presentar el plan vigente y su previsión mensual, corte de ventas y procedencia. Reutilizar los resultados del plan; sin otro motor ni recalculo en navegador. Conservar las rutas/datos historicos en el apartado academico claramente identificado. Actualizar enlaces de orientacion que devuelvan al flujo historico cuando prometen planificacion actual. Pruebas dirigidas de login->Inicio->Ventas previstas->Compra recomendada: mismo plan/corte/producto y cantidad prevista; historicos accesibles con sus etiquetas. No repetir modelos/T12 ni rediseño general.

## Continuacion

Datos y calculo base sin discrepancias en las comprobaciones ejecutadas; cerrar R21 antes de presentar la interfaz publica como terminada. Claude puede continuar preparando la nube mientras corrige este flujo. Autorizacion humana de integrar/publicar existe desde 21/10; presupuesto concreto todavia pendiente, no inferirlo de la captura. Saldo de credito pendiente de lectura humana del portal. No se auditaron tarifas ni se confirma un techo automatico de gasto. Aceptacion humana y comprobacion HTTPS real siguen pendientes.


## Cierre R21 — 21/10/2026, ffa877f + 5a3d535

Revisadas rutas, CurrentPlanStore, nueva PlanForecastsPage y enlace a Compra recomendada. /pronosticos ahora lee los resultados del plan y el historico conserva ruta /evaluacion/ventas-previstas. Ejecutada suite dirigida t21-current-plan.spec.ts: 8/8 aprobadas (incluye recorrido entre las tres pantallas, cantidades, corte, versiones, errores y vacio). R21 cerrado en alcance local revisado. 302 pruebas y navegador9/9 son evidencia del ejecutor, no comprobaciones en vivo de Codex. No se tocaron servicios ni datos.

Puede continuar la publicacion una vez autorizado el presupuesto y disponibles accesos/credito. No equivale a publicacion o aceptacion humana completadas. Las lecturas independientes de resultados no justifican por si solas diferencias: comprobar en nube mismo plan_id y version ante recargas y nuevas generaciones.

Observaciones al plan de nube (preparacion, no fallo local): el tamano del paquete no acredita ocupacion de Atlas incluyendo indices y margen para trabajos nuevos; verificar tras restauracion. No abrir acceso global a Atlas por mero aviso: mantener alcance limitado y solicitar decision expresa si existe impedimento tecnico. Si se propone omitir historia por capacidad, identificar el contenido y las funciones afectadas antes de cambiar el alcance; conservar fuentes y respaldos locales. Las cifras de costo no fueron auditadas por Codex en esta revision.
