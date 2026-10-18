# UX01: una aplicación comprensible desde la primera visita

## Hallazgo real del usuario

Rogelio abrió la demostración y comunicó que no entiende cómo usarla. Las pantallas de historial, comparación y recomendaciones muestran términos de investigación, identificadores y párrafos técnicos antes de orientar la tarea. Esta observación es evidencia de comprensión insuficiente en su primera visita; no se reemplaza por las pruebas automáticas previas. Aceptación humana: pendiente, con esta observación abierta.

Objetivo: que una persona que gestiona una tienda pueda identificar para qué sirve la aplicación, qué datos está viendo y qué puede hacer a continuación. La primera pantalla debe orientarla sin exigir leer el informe académico. El alcance sigue siendo demostración histórica con ventas observadas e inventario simulado; mejorar la interfaz no convierte esos datos en inventario real ni en pronósticos actuales.

## Organización de tareas

Navegación principal propuesta, corta y estable:

1. **Inicio**: orientación y acciones claras.
2. **Ventas previstas**: consultar las cantidades estimadas para un producto o categoría y un período.
3. **Reposición simulada**: explorar las cantidades sugeridas por el escenario, con su explicación.
4. **Mis análisis**: elegir qué resultado consultar; distinguir el ejemplo histórico, los generados y la evaluación de agosto.

Navegación secundaria, siempre localizable: **Ventas registradas**, **Evaluación de resultados**, **Ayuda**. Para administración: **Cargar datos**, **Crear análisis** y **Estado del sistema**, respetando los permisos existentes. El lector puede conservar acceso secundario a la lista de datos cargados que ya permite la API; no necesita ver como acción principal una carga que no puede ejecutar.

No esconder funciones para hacer espacio. Los nombres técnicos y las rutas actuales pueden conservarse internamente. Los enlaces existentes y el parámetro `run` siguen funcionando; el menú no debe perder la selección de análisis. Usar la plantilla común y componentes reutilizables, no pantallas de estilos inconexos.

## Inicio: una orientación, no un informe

Encabezado sugerido: **Explora las ventas previstas y una simulación de reposición**.

Explicación corta: «Consulta cuánto se estimó vender y cómo se calculó una sugerencia de reposición con los datos del ejemplo».

Una franja de contexto visible explica sin códigos: «Ejemplo con datos históricos de 2026. El inventario es simulado; no representa las existencias actuales». Detallar fechas concretas cuando se muestra un análisis. No llamar ficticias a las ventas reales ni reutilizar el banner de `?demo=1` para este caso: la demo actual usa ventas observadas, no mocks.

Tres tarjetas de tarea, con una frase y un botón real:

- **Consultar ventas previstas** → «Elige un producto y revisa las unidades estimadas para las fechas del ejemplo» → **Ver previsión**.
- **Entender una reposición** → «Revisa una sugerencia y los datos utilizados para calcularla» → **Explorar reposición simulada**.
- **Consultar otro análisis** → «Cambia entre el ejemplo de julio y la evaluación de agosto» → **Ver mis análisis**.

Ayuda al empezar: tres pasos visibles y breves, accesibles otra vez desde Ayuda. Puede recordarse su cierre por usuario/localmente; no convertirlo en un modal obligatorio ni usar la preferencia como control de permisos. Una única acción principal visual por pantalla. Las tarjetas deben llevar al análisis correcto; nada de accesos de adorno.

El resumen de ventas reales puede vivir en una sección secundaria o pantalla propia. No poner como bienvenida una tabla de calidad de datos ni el historial de fallos técnicos. Las cifras de portada se obtienen de endpoints existentes y se etiquetan con período, universo y filtro. Si no hay un total global, omitir la tarjeta o decir que es de la página; nunca sumar 50 filas paginadas como si fueran todo el conjunto.

## Lenguaje que utilizará la interfaz

| Actual | Texto principal propuesto | Información técnica disponible aparte |
|---|---|---|
| Corrida | Análisis | run_id y tipo interno |
| Corte / origen | Ventas utilizadas hasta | fecha de corte/origen exacta |
| Horizonte / h | Período estimado / día de la previsión | h y definición técnica |
| SKU | Código del producto | SKU original |
| Tránsito | Por recibir (simulado) | in_transit |
| promedio_28 | Promedio de los últimos 28 días | identificador del método |
| RF distribuido | Modelo experimental | Random Forest y desagregación |
| Backtest | Comparación con ventas registradas | folds, metodología y métricas completas |
| Cohorte | Tipo de historial | definición y código en filtros avanzados |
| T07 / T12 | Ejemplo de julio / Evaluación de agosto | identificador de etapa en metodología |
| Activa | En uso por defecto | puntero original, sin modificarlo |

«En uso por defecto» y «seleccionado para consultar» son estados distintos: cambiar la selección de la interfaz no activa otra corrida en Mongo. Nombres de períodos/fechas deben provenir de la API, no estar escritos solo para los tres registros de hoy. Estados queued/running/failed/superseded y códigos de error se traducen a mensajes cortos con siguiente paso; el código y texto original quedan en detalles, sin revelar secretos.

No inventar nombres comerciales de productos. El contrato actual devuelve principalmente código y categoría. Si no hay descripción autorizada, mostrar «Producto 12020040 · Higiene capilar» o el código con una etiqueta clara; no crear una marca o producto inexistente. No releer los Excel para enriquecer la presentación ni alterar el catálogo por datos futuros.

## Mis análisis: elegir antes de inspeccionar

Vista inicial compacta con nombre comprensible, fechas utilizadas, período previsto, estado y acciones **Ver previsión**, **Ver reposición** cuando corresponda y **Ver evaluación**. La estructura puede ser tarjetas o tabla de 4–5 columnas; no diez columnas de metadatos, ni un identificador que se parte en cuatro líneas.

Ejemplo histórico vigente identificado como predeterminado. Evaluación de agosto identificada como evaluación, con una frase: «Permite comparar estimaciones con ventas registradas; no genera pedidos». Análisis generados identificados como tales, sin atribuirles backtest si no existe.

Versiones reemplazadas accesibles en **Ver versiones anteriores**, sin borrarlas ni validarlas por comodidad. Si se abre una, aviso visible y breve: «Esta versión fue reemplazada. No uses sus sugerencias», con enlace a la corregida. El motivo largo, hash, UTC, semillas, sello y fases quedan en detalles. Un registro no válido nunca puede aparentar ser el resultado recomendado.

## Reposición simulada: entender una sugerencia

Arriba: título claro, una línea de propósito, análisis seleccionado con fechas y un aviso de simulación. Evitar apilar varias cajas que repiten el mismo aviso. El rótulo «Inventario simulado con supuestos; no corresponde al inventario real de la empresa» debe seguir visible junto a los resultados. Los datos históricos nunca se presentan como una orden para comprar hoy.

Filtros simples: buscar código, categoría y tres vistas comprensibles: **Con sugerencia de reposición**, **Sin necesidad de reponer en el ejemplo**, **Sin datos de inventario**. Se permite iniciar mostrando las sugerencias positivas si el filtro está claramente seleccionado y las otras vistas siguen accesibles. Usar los filtros/paginación del servidor; no filtrar solo la página recibida ni fabricar totales.

Tabla principal corta: producto/categoría, disponible simulado, cantidad sugerida y **Entender sugerencia**. Por recibir y valor supuesto pueden ir en detalle o columnas secundarias. No dejar una fila casi vacía de diez columnas cuando faltan datos: mostrar un estado claro y **Qué información falta**. Desconocido sigue siendo desconocido, nunca cero.

Al abrir una sugerencia: panel con título del producto y resultado destacado «En este ejemplo se sugieren N unidades», fecha del inventario y tres pasos sencillos basados en los valores reales de la respuesta:

1. **Con qué se cuenta**: disponible y por recibir simulados; posición de inventario explicada con una suma.
2. **Qué se busca cubrir**: ventas previstas y reserva de seguridad para los días del escenario.
3. **De dónde sale la cantidad**: objetivo menos disponible/por recibir, respetando el cálculo exacto ya existente.

La persona puede abrir **Ver cálculo completo y supuestos** para ver todos los pasos técnicos, precisión racional, plazo y política. No recalcular con números redondeados de la pantalla ni mostrar una explicación que no cuadre con el resultado. No deducir urgencia o «riesgo alto» si el modelo de datos no define ese indicador.

Si el análisis final no tiene recomendaciones: mensaje corto, causa comprensible y botón **Abrir el ejemplo con reposición simulada**. El botón cambia de análisis explícitamente; no mezclar cifras del histórico con el contexto de la final ni cambiar silenciosamente a otro resultado.

## Ventas previstas: cantidad, producto y fechas

Tabla inicial centrada en producto/categoría, fecha y cantidad estimada del método operativo. Explicar las unidades; conservar decimales cuando son previsiones, sin hacer pasar un redondeo por la predicción guardada. Comparador RF, control cero, cohorte/h, observados/evaluable y metadatos se consultan en **Comparar métodos / Ver detalles**, sin perderlos.

En un análisis generado, observado=null significa que todavía no hay valor para comparar; no cero. En una evaluación histórica, la persona puede ver previsto vs registrado. Si se añade gráfico, usar solo datos del mismo análisis/entidad/período y completar toda la serie consultada: no graficar una página como si fuera el universo. Mantener máscara/faltantes como huecos, no ceros. Gráfico accesible con resumen textual y tabla; evitar librerías pesadas por adorno.

## Evaluación: responder una pregunta antes de mostrar métricas

Dividir claramente **Estimaciones frente a ventas registradas** y **Comparación de reposición simulada**. Una conclusión corta depende de los datos, período y nivel elegidos. No imponer «RF siempre peor» a una vista donde un indicador sea menor; conservar que el método operativo elegido no cambia y que no se declaró ganador experimental.

Mostrar el error en lenguaje llano y su alcance. Ejemplo para WAPE0,78: «El error absoluto acumulado equivale aproximadamente al 78 % del volumen observado. No significa un 78 % de acierto». No convertir un error alto en una insignia de calidad ni reemplazarlo por una métrica más favorable. Indicar si la vista es por producto o categoría y el período.

El detalle académico conserva todos los métodos, controles, cohortes, folds/escenarios y métricas, incluidos resultados desfavorables y casos no evaluables. Se puede plegar, pero debe encontrarse fácilmente. No atribuir impacto real a mayor servicio simulado ni ocultar el mayor stock/compras que lo acompaña. El texto «agosto sigue reservado» no describe correctamente el estado de una evaluación ya ejecutada: distinguir resultado final disponible de la prohibición de usar agosto en desarrollo/carga general.

## Diseño y estados de la aplicación completa

Aplicar la misma jerarquía al acceso, inicio, ventas, historial, previsiones, reposición, evaluación, carga/generación y sistema. Menú lateral en escritorio o navegación equivalente clara, encabezados legibles, fondo neutro, tarjetas y espaciado consistentes, color de acento sobrio. Menú accesible en móvil. Tipografía del sistema, cuerpo de al menos16px, sin reducir letra para hacer caber diez columnas. Un resumen útil antes de tablas extensas; no llenar la portada de indicadores que no guían decisiones.

Las fechas se muestran en español y las marcas técnicas en zona America/Lima donde se presenten al usuario. Importes con Intl.NumberFormat de PEN, unidades y fechas siempre etiquetados. Mantener fechas exactas/UTC en detalles si se necesitan para auditoría. El estado histórico/antigüedad es visible en palabras sencillas; los errores reales y versiones inválidas sí requieren aviso destacado, no todas las explicaciones de la aplicación.

Cargas con pasos: elegir archivo → revisar resultado → consultar análisis; solo administradores. Generación: explicar qué hará el botón y qué fechas admite esta versión, confirmar el resultado de un trabajo y ofrecer **Ver previsión**. No ampliar rangos de fechas ni quitar controles temporales para que parezca más operativa. Navegar/abrir ayudas no crea trabajos ni ejecuta modelos.

Carga, vacío, error, falta de conexión y permiso denegado deben decir qué ocurrió y ofrecer una acción válida. No mostrar códigos internos o un párrafo del servidor como explicación principal. Ningún elemento clicable puede ser decorativo o una función sin implementar.

## Criterios de aceptación UX01

- Primera entrada: identifica propósito, naturaleza histórica/simulada y tres acciones concretas sin leer metodología.
- Sin abrir información avanzada, no se exhiben run_id, hashes, nombres de campos, T07/T12, folds o códigos en el contenido principal. Permanecen localizables en detalles.
- Se puede llegar del inicio a una sugerencia positiva y su explicación en como máximo tres acciones de navegación, sin introducir un código de producto conocido de antemano. Las acciones para iniciar sesión no cuentan.
- Se puede cambiar de análisis y navegar entre previsión/reposición/evaluación manteniendo contexto; volver atrás o recargar conserva la selección. La final no muestra pedidos de otra corrida.
- Una versión reemplazada y un producto sin inventario siguen reconocibles; no hay acciones de compra real ni cifras inventadas.
- Teclado/foco/etiquetas, móvil375px y escritorio1366px, zoom200 %; sin texto cortado, controles inaccesibles ni scroll horizontal de toda la página. Las tablas que lo requieren pueden tener desplazamiento identificado, sin meter toda la experiencia en un cuadro de scroll.
- La interfaz de producción conserva CSP y CSS correcto. La validación tiene capturas de las pantallas reales con datos de la demo, no solo maquetas.
- Rogelio vuelve a probar y puede explicar propósito, fechas, ventas previstas y una sugerencia. Su respuesta real decide la aceptación de comprensión; no inferirla de un E2E.

No están autorizados publicación, gasto, transferencia a nube, nuevos modelos o cambios de conclusiones científicas. El rediseño local sí está autorizado por el usuario y debe implementarse completo, no detenerse tras una propuesta o cambio de colores.
