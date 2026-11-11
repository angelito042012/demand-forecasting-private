# T13 Guion de aceptación humana

**Estado de la aceptación humana: PENDIENTE.** Este documento no está firmado ni acredita participantes, conformidad de asesor o de la MYPE, ni actas. Lo completará Rogelio al ejecutarlo.

**Observación abierta de Rogelio (primera visita, interfaz anterior):** «No comprendió el uso en su primera visita». Se registra como observación de usabilidad que motivó el rediseño UX01; **no es una aceptación ni un defecto de cálculo demostrado**. Sigue abierta hasta que Rogelio vuelva a probar con la interfaz nueva (bloque «Prueba de comprensión (UX01)»).

- **Versión del sistema:** commit `f95092f` (rama master); imagen `df-app:ux01r-f95092f`. Interfaz rediseñada (UX01). Fecha del guion: 17/10/2026 (America/Lima).
- **Entorno a probar:** demostración local `df-demo` sobre una **copia restaurada** (no es la base v1/v2 ni la publicación original). **URL: `https://localhost:8443`** (solo este equipo; certificado autofirmado: el navegador avisará, elija «Avanzado» → «Continuar»). **Base de ensayo activa:** `df_demo_20261017221940` (compruébela con `status`, abajo). Publicación en la nube: [PENDIENTE: no existe publicación]; este guion no acredita pruebas en nube.
- Fecha y hora de ejecución: 2026-11-06. Ejecutó: Milton (pre-aceptación, equipo de desarrollo). Entorno: `df-equipo` (v2, puerto 8446, base `df_equipo_20261023135040`). La aceptación formal (A14) por Rogelio queda pendiente.
- **Usuarios (sin compartir contraseñas por chat):** existen `demo_admin` y `demo_lector`, con contraseñas generadas guardadas **solo** en `artifacts/private/t13b/demo_credenciales.txt` (ábralo en su equipo; fuera de Git). Para usar su propia contraseña: `.venv\Scripts\python.exe -m scripts.demo_local create-user --username <su_usuario> --role admin` (la pide por consola y no la muestra). No anote contraseñas aquí.
- **Comprobar antes de empezar:** `.venv\Scripts\python.exe -m scripts.demo_local status` debe decir «misma base en api y worker … True» y mostrar, como mínimo, la corrida histórica activa (puntero `hist-20260710-4ea348836e35`), la histórica sustituida (`hist-20260710-52b01cd999dd`) y la evaluación final (`final-20260731-d587255d87fb`); puede haber además análisis creados por pruebas (no se exige un número fijo de corridas). Si la imagen en ejecución no es `df-app:ux01r-f95092f`, avise antes de seguir.

## Prueba de comprensión (UX01)

Hágala **antes** de los pasos detallados, con el usuario `demo_lector`, sin ayuda de quien le explique la aplicación. Puede usar «Ayuda». Anote lo que realmente ocurrió; no se rellena de antemano.

| N.º | Tarea | Qué debería poder hacer (referencia, no resultado) | Resultado real / observación |
|---|---|---|---|
| U1 | (a) Diga con sus palabras **para qué sirve la aplicación** y **de qué fechas son los datos** | Estimar ventas por producto y entender una reposición simulada; datos históricos de 2026 (ventas utilizadas hasta el 10/07/2026 en el ejemplo; evaluación de agosto con ventas del 01 al 21/08/2026); no son las ventas de hoy ni inventario real | |
| U2 | (b) Encuentre **las ventas previstas de un producto** (por ejemplo, el «Producto 1010004 · Higiene capilar») | Entra por «Ventas previstas» (o «Ver previsión» en Inicio), escribe el código en «Código del producto», pulsa **Buscar** y lee fecha y «Cantidad estimada (unidades base)» | |
| U3 | (c) Abra **una sugerencia de reposición** y explique **de dónde sale la cantidad** | Entra por «Reposición simulada», pulsa **Entender sugerencia** y explica los tres pasos: con qué se cuenta (disponible + por recibir), qué se busca cubrir (ventas previstas de 14 días + reserva de 7 días, redondeado hacia arriba) y objetivo − lo que se tiene = cantidad sugerida; aclara que es hipotética y con inventario simulado | |

- ¿Pidió ayuda o tardó en encontrar algo? ¿Qué texto o botón no entendió? ______________________ (completar al ejecutar).

## Inicio rápido: cinco pasos

1. Abra `https://localhost:8443`, acepte el aviso del certificado e ingrese como `demo_lector`. Aparece **Inicio**.
2. En **Mis análisis** identifique «Ejemplo de julio» («En uso por defecto»), el análisis creado en la aplicación y «Evaluación de agosto»; abra «Detalles técnicos» de la evaluación.
3. En **Evaluación de resultados** elija la evaluación de agosto y lea el error del promedio de 28 días frente al modelo experimental (0,78 y 0,79 en la documentación de resultados): **no es 78 % de acierto**; no se declara ganador.
4. En **Reposición simulada** (ejemplo de julio, vista «Con sugerencia de reposición») pulse **Entender sugerencia** en un producto, abra **Ver cálculo completo y supuestos** y lea **«Inventario simulado con supuestos; no corresponde al inventario real de la empresa»**.
5. Salga e ingrese como `demo_admin`: verá «Administración» (Cargar datos, Crear análisis, Estado del sistema); no suba archivos reales ni cree análisis durante esta prueba inicial.

## Pasos

La última columna queda **vacía** hasta la ejecución real. Marque en ella lo que observó (cumple / no cumple / comentario).

| N.º | Paso (qué hacer) | Resultado esperado | Resultado real / observación |
|---|---|---|---|
| **A. Acceso e Inicio** | | | |
| 1 | Abrir `https://localhost:8443` sin sesión | Aparece «Acceso»; no se ve ningún dato | Cumple (Milton, entorno equipo v2 en puerto 8446) |
| 2 | Ingresar con una contraseña incorrecta | Mensaje «Usuario o contraseña incorrectos.» | Cumple |
| 3 | Ingresar con el usuario lector | Entra a **Inicio** (título «Explora las ventas previstas y una simulación de reposición»); arriba se ve `demo_lector (lector)`; la franja dice «Ejemplo con datos históricos de 2026. El inventario es simulado…» | Cumple — interfaz v2: Inicio muestra plan operativo de noviembre; `equipo_lector (lector)` |
| 4 | Mirar el menú | Inicio, Ventas previstas, Reposición simulada, Mis análisis; en «Más»: Ventas registradas, Evaluación de resultados, Datos cargados, Ayuda; no aparece «Administración» | Parcial — menú v2 distinto: Inicio, Ventas previstas, Existencias, Compra recomendada, Mis análisis; MÁS: Ventas registradas, Evaluación de resultados, Evaluación académica, Eval. académica: ventas previstas, Datos cargados, Ayuda. No hay «Reposición simulada» directa ni «Administración» |
| 5 | En Inicio leer la barra de análisis y la cifra | «Ejemplo de julio · En uso por defecto», «Ventas utilizadas hasta el 10/07/2026 (hace N días; datos históricos, no las ventas de hoy)», período estimado 11/07/2026 al 31/07/2026; «N productos con sugerencia de reposición en el ejemplo … inventario simulado; no son existencias reales» | Cumple tras aclaración — v2 muestra «Plan de compra vigente» con Dato real / Dato empresa / Proyección, «19 de 50» |
| 6 | Abrir «Datos cargados» | Mensaje de solo lectura; lista de archivos; no hay botón de carga | Cumple |
| **B. Mis análisis y estados** | | | |
| 7 | Abrir «Mis análisis» | Tarjetas: «Ejemplo de julio» (En uso por defecto, Ejemplo histórico), «Análisis creado con ventas hasta el 10/07/2026» (Creado en la aplicación) si existe, y «Evaluación de agosto» (Evaluación) | Cumple |
| 8 | En la tarjeta de la evaluación pulsar **Elegir este análisis** | Aparece «Estás consultando este análisis» y «Seleccionado para consultar»; «Ejemplo de julio» sigue «En uso por defecto» | Cumple |
| 9 | Pulsar «Ver versiones anteriores» | Lista de versiones reemplazadas con aviso «Esta versión fue reemplazada. No uses sus sugerencias» y enlace a la corregida | Cumple |
| 10 | Explicar con sus palabras la diferencia entre «En uso por defecto» y «Seleccionado para consultar» | El primero lo fija el servidor y no cambia; el segundo es solo lo que usted mira | Cumple tras aclaración |
| **C. Ventas previstas** | | | |
| 11 | Abrir «Ventas previstas» con el ejemplo de julio | Tabla Producto / Fecha / Cantidad estimada (unidades base) / Vendido (registrado) | Cumple |
| 12 | Buscar por «Código del producto» y pulsar **Buscar** | La tabla muestra solo ese producto | Cumple |
| 13 | Pulsar **Comparar métodos / ver detalles** | Aparecen identificador, tipo de historial, día de la previsión, modelo experimental y control «siempre cero» | Cumple |
| 14 | Elegir el análisis creado en la aplicación (si existe) | Aviso: aún no hay ventas registradas para comparar; «no disponible…» no es cero | N/A — no existe análisis creado en entorno equipo |
| **D. Interpretar el error (WAPE)** | | | |
| 15 | Abrir «Evaluación de resultados» (ejemplo de julio) | Vista breve: una explicación del error del promedio de 28 días y del modelo experimental, un aviso, y el botón «Ver cómo se evaluó» (el detalle académico llega cerrado) | Cumple |
| 16 | Cambiar «Nivel» a «Categoría» | El error baja mucho respecto de producto | Cumple |
| 17 | Responder: ¿un error de 87 % significa 87 % de acierto? | No. Es error acumulado equivalente al 87 % del volumen vendido; menor es mejor (también en «Ayuda») | Cumple — Milton entendió que no es acierto |
| 18 | Pulsar «Ver cómo se evaluó» (detalle académico) | Se abre el detalle: tabla con todos los métodos, MAPE con cobertura y ceros excluidos; R² puede decir «no evaluable» | Cumple — tabla completa con WAPE 78.1% (promedio_28) vs 79.1% (RF), advertencias visibles |
| **E. Reposición simulada y su explicación** | | | |
| 19 | Abrir «Reposición simulada» | Aviso «Inventario simulado con supuestos; no corresponde al inventario real de la empresa»; línea con «inventario simulado al cierre del 10/07/2026»; vista «Con sugerencia de reposición» activa | Cumple — accedido vía Más → Evaluación académica (menú v2 no tiene «Reposición simulada» directa) |
| 20 | En un producto pulsar **Entender sugerencia** | «En este ejemplo se sugieren N unidades (hipotético…)» y tres pasos: con qué se cuenta, qué se busca cubrir, de dónde sale la cantidad | Cumple — producto 12010025, «se sugieren 2 unidades (hipotético)», tres pasos visibles |
| 21 | Abrir **Ver cálculo completo y supuestos** y verificar con calculadora: pedido = máx(0, objetivo − (disponible + por recibir)) | Coincide; «posición/objetivo/cantidad coherente»; no aparece «no cuadran con la fórmula» | Parcial — encontró objetivo (7), «en tránsito» en vez de «por recibir»; observó que «Detalle técnico» muestra valores en inglés |
| 22 | Explicar el pedido a otra persona (producto, disponible, por recibir, objetivo, cantidad) y aclarar que es hipotético | Debe poder decir de dónde sale cada número | Cumple — explicó: basado en almacén actual, lo que se recibirá de proveedores y demanda de 28 días |
| 23 | Pulsar la vista «Sin necesidad de reponer en el ejemplo» | Lista de productos con inventario simulado y cantidad sugerida 0 | Cumple — vio cantidad sugerida 0 |
| 24 | Pulsar la vista «Sin datos de inventario» y **Ver qué falta** | «Sin datos de inventario al …» y qué información falta; no se supone stock cero ni se calcula cantidad | Cumple — vio ~300 productos sin datos |
| **F. Evaluación de agosto sin pedidos** | | | |
| 25 | Elegir la evaluación de agosto y abrir «Reposición simulada» | «Este análisis no genera pedidos»; sin existencias ni pedidos; botón para abrir el ejemplo con reposición simulada | Cumple — vio mensaje «Esta pantalla es una evaluación histórica con inventario simulado, separada del flujo principal» |
| 26 | Abrir «Ventas previstas» con la evaluación | Fechas 01/08 a 21/08/2026; nota de evaluación; «no evaluable» no es cero | Cumple |
| 27 | Abrir «Evaluación de resultados» con la evaluación de agosto | Vista breve con «Métrica del 01 al 14 de agosto» y «Bloque de prueba disponible del 01 al 21 de agosto» (etiquetas distintas); al abrir «Ver cómo se evaluó» aparecen las advertencias completas (un solo bloque de 21 días, WAPE no es exactitud) y no se declara ganador | Cumple — WAPE 78.1% vs 79.1%, advertencias visibles, no se declara ganador |
| **G. Ayuda y límites** | | | |
| 28 | Abrir «Ayuda» | Primeros pasos, «Qué no hace esta aplicación», «Cómo leer el error absoluto (WAPE)» y glosario | Cumple |
| **H. Administrador (opcional, caso mínimo ya probado)** | | | |
| 29 | Salir e ingresar como admin; abrir «Cargar datos» | Pasos 1-2-3; «Subir y procesar»; trabajos recientes | Cumple — pasos 1-2-3 visibles, archivos listados (enero a septiembre) |
| 30 | Reenviar un archivo ya aprobado (si hay uno de prueba) | «Este archivo ya había sido enviado» o «Sin cambios»; sin duplicados | Cumple — reenvió marzo.xlsx: «Sin cambios (archivo ya cargado). Este archivo ya estaba cargado; no se modificó ningún dato.» |
| 31 | Abrir «Crear análisis» (sin crear si no es necesario) | Fecha «Ventas utilizadas hasta» con rango permitido; período estimado de 21 días y método fijos; botón «Crear análisis» | Cumple — fecha 10/07/2026, período 21 días (fijo), método promedio_28 (fijo). Milton presionó «Crear análisis» (genera análisis histórico sin consecuencias) |
| 32 | Abrir «Estado del sistema» y salir | «funcionando», base de datos «disponible»; al salir vuelve a «Acceso» | Cumple — «Estado general: funcionando», «Base de datos: disponible», «Versión: 0.1.0» |

## Cierre de la sesión (completar al ejecutar)

- Defectos encontrados (número de paso y descripción): Ningún defecto crítico. (4) Menú v2 difiere del guion — no es defecto del software, el guion fue escrito para df-demo. (5) «Barra de análisis y cifra» poco claro; se sugiere «sección Plan de compra vigente». (14) N/A en entorno equipo. (21) «Detalle técnico» muestra nombres en inglés — observación menor de usabilidad.
- ¿Se pudo explicar WAPE, inventario simulado/antigüedad, los tipos de análisis y un pedido? (Sí / No / Parcial por tema): **Sí en todos.** WAPE: entendió que no es acierto (paso 17). Inventario simulado: explicó componentes correctamente (paso 22). Tipos de análisis: distinguió «En uso» vs «Seleccionado» (paso 10) y que la evaluación no genera pedidos (paso 25). Pedido: explicó la fórmula (paso 22).
- ¿Quedó resuelta la observación «No comprendió el uso en su primera visita»? (Sí / No / Parcial; con evidencia de la Prueba de comprensión): **Parcial.** Milton completó 32 pasos guiados sin bloqueantes críticos y explicó correctamente los conceptos. Sin embargo, fue un recorrido guiado por el asistente, no independiente. La observación de Rogelio sigue abierta hasta que la pruebe con la interfaz nueva sin ayuda.
- Aceptación humana: **PRE-ACEPTACIÓN COMPLETADA** por Milton (equipo de desarrollo), 2026-11-06. La aceptación formal (A14) por Rogelio/MYPE queda **PENDIENTE**.
- Pendientes ajenos a este guion: validación en nube, cinco usuarios en nube y participación humana adicional (A13/A14 según la matriz de cierre).

## Prueba de la versión de ensayo con «Inventario informado» (etapa 18)

- **Dirección:** `https://localhost:8444` (ensayo; la demo anterior sigue en `https://localhost:8443` y no tiene esta pantalla). Usuarios `ens_lector` y `ens_admin`; contraseñas solo en `artifacts/private/t13b/ens18_credenciales.txt` (no las copie a ningún documento). Imagen `df-app:t18r-616b5ef`; base `df_ens18_20261018172811`. Aceptación humana: **PENDIENTE**.
- Las tres tareas de comprensión del bloque «Prueba de comprensión (UX01)» se repiten en esta versión (mismos pasos), y se añaden las siguientes. Complete la columna de resultado real solo con lo que usted observe.

| N.º | Paso | Resultado esperado | Resultado real / observación |
|---|---|---|---|
| I1 | En Inicio, buscar la tarjeta «Consultar el inventario informado» y pulsar «Ver inventario informado» | Se abre «Inventario informado por la empresa» | |
| I2 | Leer la franja del conteo | «Conteo del 18/10/2026, 17:00 (hora de Lima) · Almacén Principal (almacén 1)» y «informado por la empresa; no verificado de forma independiente»; no dice «simulado» | |
| I3 | Leer el aviso amarillo | El inventario es del 18/10; el histórico de ventas termina el 30 de septiembre; faltan las ventas posteriores (no son cero); por eso no hay recomendación actualizada; pedidos por recibir no informados | |
| I4 | Contar las filas y mirar el resumen | 50 productos · 48 con existencia · 2 sin existencia | |
| I5 | Pulsar «Sin existencia» | 2 productos con disponible 0 y la marca «Sin existencia» | |
| I6 | Buscar un producto por código o nombre (por ejemplo, un código de su lista) y leer su presentación | Aparece su cantidad en la presentación indicada (p. ej. caja de 12 o pack de 2: la cantidad no se multiplicó) | |
| I7 | Abrir «Detalles del conteo» | Archivo, huella corta, versión, desconocidos declarados | |
| I8 | Ir a «Reposición simulada» | Sigue siendo el ejemplo histórico con el aviso de inventario simulado; **no** usa el conteo del 18/10 | |
| I9 | Explicar con sus palabras: ¿por qué no aparece una recomendación de compra para hoy? | Faltan las ventas del 01 al 18/10 y los pedidos por recibir; no se supone cero | |

## Prueba guiada de Planificar compras (etapa 19)

- **Dirección:** `https://localhost:8445` (ensayo ens19; las demos 8443 y 8444 no tienen esta pantalla). Usuarios `t19_lector` y `t19_admin`; contraseñas solo en `artifacts/private/t13b/ens19_credenciales.txt`. Imagen `df-app:t19-7dbb30b`. Aceptación humana: **PENDIENTE**; complete la columna de resultado real solo con lo que observe y responda.

| N.º | Paso | Resultado esperado (plan base) | Resultado real / observación |
|---|---|---|---|
| P1 | Abrir «Planificar compras» y leer los dos avisos y «De dónde sale este plan» | Ventas hasta el 30/09; octubre desconocido (no cero); conteo del 18/10 17:00; «no llegan otros pedidos (supuesto)»; el mes está a 32–61 días del último dato | |
| P2 | Buscar el producto 3110044 (LAN KERATIN ACOND X 300 ML) | Stock del conteo 0; ventas previstas del mes 36.429; 7 días: llega 25/10, compra 54; 14 días: llega 01/11, compra 45 | |
| P3 | Pulsar «Entender la compra» en ese producto | 7 días: sin stock hasta el 24/10 (faltan 7.286 u), necesidad 25/10–30/11 + reserva 7 días, compra 54. 14 días: faltan 15.786 u antes de llegar, necesidad noviembre + reserva, compra 45 | |
| P4 | Responder: ¿por qué con 14 días se compra menos pero es peor? | Se pierden más ventas antes de que llegue la orden; la compra menor no es un ahorro | |
| P5 | Buscar 6020011 (REFLEX AMPOLLA CJA X 12) | Stock del conteo 106; compra 0 en ambos plazos («0 (no hace falta comprar)») | |
| P6 | Buscar 12040022 (LANOSTERIN CHAMPU X 1 LT) | Stock 23; ventas previstas del mes 18.214; compra 8 en ambos plazos | |
| P7 | Responder: ¿cuántos productos necesitan compra y por qué hay productos con 0? | 19 con compra (7 y 14 días); 31 con 0 calculado porque su stock cubre el consumo | |
| P8 | Responder: ¿qué cambiaría si entraran las ventas de octubre o si llegara un pedido en camino? | El plan se recalcula como otra versión con esos datos; hoy son desconocidos y no se suponen cero | |
| P9 | (Administrador) Cambiar la fecha de decisión al 25/10 y generar | Se calcula en segundo plano y aparece otra versión con llegadas 01/11 y 08/11 (puede retirarse después) | |

## Recorrido para el equipo entrante (Tarea 12)

Requisito: el equipo nuevo reproduce la restauración del entorno, opera el caso emblemático (producto 3110044) y explica las limitaciones del sistema. Este bloque complementa los pasos anteriores y se ejecuta de forma independiente.

### Prerequisitos

- Python 3.12 con el venv del proyecto (`requirements.lock.txt`)
- Docker instalado (para Compose)
- Acceso al repositorio y a los bundles en `artifacts/private/`

### Documentación de referencia para el equipo

| Documento | Leer antes de | Contenido |
|---|---|---|
| `docs/MANUAL_OPERACION.md` | Restauración | Arranque local, Compose, variables, respaldo, §10 actualización de datos |
| `docs/MANUAL_USUARIO.md` | Recorrido de la app | Pantallas, conceptos, límites, plan operativo v2 |
| `docs/DICCIONARIO_VARIABLES.md` | Revisar el pipeline | Variables, constantes parametrizadas (CLI), features, métricas |
| `docs/EVALUACION_T06_T07_METRICAS.md` | Discusión de resultados | Diseño experimental, fórmulas, resultados T12, reproducción |
| `docs/T12_RESULTADOS.md` | Discusión de resultados | Hallazgo: promedio_28 supera a RF (WAPE 0.7810 vs 0.7910) |
| `docs/DEMOSTRACION_3110044.md` | Caso emblemático | Recorrido completo del producto 3110044 |

### Pasos del equipo

| N.º | Paso | Resultado esperado | Resultado real / observación |
|---|---|---|---|
| E1 | Restaurar el entorno local siguiendo `docs/MANUAL_OPERACION.md` §1–§4 | Demo local arranca en `https://localhost:8443`; `status` muestra la base y las corridas | |
| E2 | Ingresar como lector y navegar Inicio, Ventas previstas y Compra recomendada | Entiende la estructura: plan operativo (v2) vs análisis histórico | |
| E3 | Buscar el producto **3110044** en Compra recomendada y abrir «Entender la compra» | Stock conteo 0, ventas previstas 36.429/mes, compra 54 (7d) / 45 (14d); explica por qué 14d compra menos pero pierde más ventas | |
| E4 | Abrir Existencias y buscar 3110044 | Existencia reconstruida al 20/10; conteo 18/10 + movimientos; puede haber diferencia con el sistema | |
| E5 | Abrir Evaluación de resultados (evaluación de agosto) | WAPE promedio_28 = 0.7810, RF = 0.7910; no se declara ganador; un solo bloque de 21 días | |
| E6 | Explicar con sus palabras: ¿por qué se usa promedio_28 y no el modelo ML? | Porque RF no superó al promedio en la evaluación final; la mejora relativa fue negativa (-0.0129) | |
| E7 | Explicar tres limitaciones del sistema | (1) Inventario simulado con supuestos, no real; (2) ventas censuradas por stock; (3) no incorpora datos posteriores al 20/10 sin procedimiento técnico | |
| E8 | Leer `docs/MANUAL_OPERACION.md` §10 e identificar los argumentos CLI para un nuevo corte | `--last-full-day`, `--book-name`, `--book-window`, `--partial-date-value`, `--as-of-local`, `--base-as-of-local` | |
| E9 | Verificar que `docs/DICCIONARIO_VARIABLES.md` §1 coincide con los valores por defecto del código | Los valores de la tabla coinciden con los defaults en `dataset_v2.py`, `reconstructed.py` y `sql21_prepare.py` | |

### Cierre del recorrido del equipo

- ¿El equipo pudo restaurar y operar sin ayuda del equipo saliente? (Sí / No / Parcial): ______________________
- ¿Pudo explicar el caso 3110044 y las limitaciones? (Sí / No / Parcial): ______________________
- Observaciones o bloqueos: ______________________
