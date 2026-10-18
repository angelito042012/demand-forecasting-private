# T13 Guion de aceptación humana

**Estado de la aceptación humana: PENDIENTE.** Este documento no está firmado ni acredita participantes, conformidad de asesor o de la MYPE, ni actas. Lo completará Rogelio al ejecutarlo.

**Observación abierta de Rogelio (primera visita, interfaz anterior):** «No comprendió el uso en su primera visita». Se registra como observación de usabilidad que motivó el rediseño UX01; **no es una aceptación ni un defecto de cálculo demostrado**. Sigue abierta hasta que Rogelio vuelva a probar con la interfaz nueva (bloque «Prueba de comprensión (UX01)»).

- **Versión del sistema:** commit `269a9cd` (rama master); imagen `df-app:ux01-269a9cd`. Interfaz rediseñada (UX01). Fecha del guion: 17/10/2026 (America/Lima).
- **Entorno a probar:** demostración local `df-demo` sobre una **copia restaurada** (no es la base v1/v2 ni la publicación original). **URL: `https://localhost:8443`** (solo este equipo; certificado autofirmado: el navegador avisará, elija «Avanzado» → «Continuar»). **Base de ensayo activa:** `df_demo_20261017221940` (compruébela con `status`, abajo). Publicación en la nube: [PENDIENTE: no existe publicación]; este guion no acredita pruebas en nube.
- Fecha y hora de ejecución: ____________ Ejecutó: Rogelio ____________ (nombre/firma solo cuando se ejecute).
- **Usuarios (sin compartir contraseñas por chat):** existen `demo_admin` y `demo_lector`, con contraseñas generadas guardadas **solo** en `artifacts/private/t13b/demo_credenciales.txt` (ábralo en su equipo; fuera de Git). Para usar su propia contraseña: `.venv\Scripts\python.exe -m scripts.demo_local create-user --username <su_usuario> --role admin` (la pide por consola y no la muestra). No anote contraseñas aquí.
- **Comprobar antes de empezar:** `.venv\Scripts\python.exe -m scripts.demo_local status` debe decir «misma base en api y worker … True» y listar tres corridas (histórica activa, histórica sustituida y evaluación final). Si la imagen en ejecución no es `df-app:ux01-269a9cd`, avise antes de seguir.

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
| 1 | Abrir `https://localhost:8443` sin sesión | Aparece «Acceso»; no se ve ningún dato | |
| 2 | Ingresar con una contraseña incorrecta | Mensaje «Usuario o contraseña incorrectos.» | |
| 3 | Ingresar con el usuario lector | Entra a **Inicio** (título «Explora las ventas previstas y una simulación de reposición»); arriba se ve `demo_lector (lector)`; la franja dice «Ejemplo con datos históricos de 2026. El inventario es simulado…» | |
| 4 | Mirar el menú | Inicio, Ventas previstas, Reposición simulada, Mis análisis; en «Más»: Ventas registradas, Evaluación de resultados, Datos cargados, Ayuda; no aparece «Administración» | |
| 5 | En Inicio leer la barra de análisis y la cifra | «Ejemplo de julio · En uso por defecto», «Ventas utilizadas hasta el 10/07/2026 (hace N días; datos históricos, no las ventas de hoy)», período estimado 11/07/2026 al 31/07/2026; «N productos con sugerencia de reposición en el ejemplo … inventario simulado; no son existencias reales» | |
| 6 | Abrir «Datos cargados» | Mensaje de solo lectura; lista de archivos; no hay botón de carga | |
| **B. Mis análisis y estados** | | | |
| 7 | Abrir «Mis análisis» | Tarjetas: «Ejemplo de julio» (En uso por defecto, Ejemplo histórico), «Análisis creado con ventas hasta el 10/07/2026» (Creado en la aplicación) si existe, y «Evaluación de agosto» (Evaluación) | |
| 8 | En la tarjeta de la evaluación pulsar **Elegir este análisis** | Aparece «Estás consultando este análisis» y «Seleccionado para consultar»; «Ejemplo de julio» sigue «En uso por defecto» | |
| 9 | Pulsar «Ver versiones anteriores» | Lista de versiones reemplazadas con aviso «Esta versión fue reemplazada. No uses sus sugerencias» y enlace a la corregida | |
| 10 | Explicar con sus palabras la diferencia entre «En uso por defecto» y «Seleccionado para consultar» | El primero lo fija el servidor y no cambia; el segundo es solo lo que usted mira | |
| **C. Ventas previstas** | | | |
| 11 | Abrir «Ventas previstas» con el ejemplo de julio | Tabla Producto / Fecha / Cantidad estimada (unidades base) / Vendido (registrado) | |
| 12 | Buscar por «Código del producto» y pulsar **Buscar** | La tabla muestra solo ese producto | |
| 13 | Pulsar **Comparar métodos / ver detalles** | Aparecen identificador, tipo de historial, día de la previsión, modelo experimental y control «siempre cero» | |
| 14 | Elegir el análisis creado en la aplicación (si existe) | Aviso: aún no hay ventas registradas para comparar; «no disponible…» no es cero | |
| **D. Interpretar el error (WAPE)** | | | |
| 15 | Abrir «Evaluación de resultados» (ejemplo de julio) | «Cifras clave del alcance elegido» con error absoluto del promedio de 28 días y del modelo experimental | |
| 16 | Cambiar «Nivel» a «Categoría» | El error baja mucho respecto de producto | |
| 17 | Responder: ¿un error de 87 % significa 87 % de acierto? | No. Es error acumulado equivalente al 87 % del volumen vendido; menor es mejor (también en «Ayuda») | |
| 18 | Abrir «Ver detalle completo: todos los métodos y métricas» | MAPE con cobertura y ceros excluidos; R² puede decir «no evaluable» | |
| **E. Reposición simulada y su explicación** | | | |
| 19 | Abrir «Reposición simulada» | Aviso «Inventario simulado con supuestos; no corresponde al inventario real de la empresa»; línea con «inventario simulado al cierre del 10/07/2026»; vista «Con sugerencia de reposición» activa | |
| 20 | En un producto pulsar **Entender sugerencia** | «En este ejemplo se sugieren N unidades (hipotético…)» y tres pasos: con qué se cuenta, qué se busca cubrir, de dónde sale la cantidad | |
| 21 | Abrir **Ver cálculo completo y supuestos** y verificar con calculadora: pedido = máx(0, objetivo − (disponible + por recibir)) | Coincide; «posición/objetivo/cantidad coherente»; no aparece «no cuadran con la fórmula» | |
| 22 | Explicar el pedido a otra persona (producto, disponible, por recibir, objetivo, cantidad) y aclarar que es hipotético | Debe poder decir de dónde sale cada número | |
| 23 | Pulsar la vista «Sin necesidad de reponer en el ejemplo» | Lista de productos con inventario simulado y cantidad sugerida 0 | |
| 24 | Pulsar la vista «Sin datos de inventario» y **Ver qué falta** | «Sin datos de inventario al …» y qué información falta; no se supone stock cero ni se calcula cantidad | |
| **F. Evaluación de agosto sin pedidos** | | | |
| 25 | Elegir la evaluación de agosto y abrir «Reposición simulada» | «Este análisis no genera pedidos»; sin existencias ni pedidos; botón para abrir el ejemplo con reposición simulada | |
| 26 | Abrir «Ventas previstas» con la evaluación | Fechas 01/08 a 21/08/2026; nota de evaluación; «no evaluable» no es cero | |
| 27 | Abrir «Evaluación de resultados» con la evaluación | Un solo bloque de 21 días; advertencias visibles; no se declara ganador | |
| **G. Ayuda y límites** | | | |
| 28 | Abrir «Ayuda» | Primeros pasos, «Qué no hace esta aplicación», «Cómo leer el error absoluto (WAPE)» y glosario | |
| **H. Administrador (opcional, caso mínimo ya probado)** | | | |
| 29 | Salir e ingresar como admin; abrir «Cargar datos» | Pasos 1-2-3; «Subir y procesar»; trabajos recientes | |
| 30 | Reenviar un archivo ya aprobado (si hay uno de prueba) | «Este archivo ya había sido enviado» o «Sin cambios»; sin duplicados | |
| 31 | Abrir «Crear análisis» (sin crear si no es necesario) | Fecha «Ventas utilizadas hasta» con rango permitido; período estimado de 21 días y método fijos; botón «Crear análisis» | |
| 32 | Abrir «Estado del sistema» y salir | «funcionando», base de datos «disponible»; al salir vuelve a «Acceso» | |

## Cierre de la sesión (completar al ejecutar)

- Defectos encontrados (número de paso y descripción): ______________________
- ¿Se pudo explicar WAPE, inventario simulado/antigüedad, los tipos de análisis y un pedido? (Sí / No / Parcial por tema): ______________________
- ¿Quedó resuelta la observación «No comprendió el uso en su primera visita»? (Sí / No / Parcial; con evidencia de la Prueba de comprensión): ______________________
- Aceptación humana: **PENDIENTE** (cambiar solo tras la ejecución real y con la anotación de quien corresponda).
- Pendientes ajenos a este guion: validación en nube, cinco usuarios en nube y participación humana adicional (A13/A14 según la matriz de cierre).
