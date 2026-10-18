# T13 Guion de aceptación humana

**Estado de la aceptación humana: PENDIENTE.** Este documento no está firmado ni acredita participantes, conformidad de asesor o de la MYPE, ni actas. Lo completará Rogelio al ejecutarlo.

- **Versión del sistema:** commit `8412ca0` (rama master); imagen `df-app:t11a-local` (`sha256:59c92de892aa`, construida con la corrección de estilos de producción). Fecha del guion: 17/10/2026 (America/Lima).
- **Entorno a probar:** demostración local `df-demo` sobre una **copia restaurada** (no es la base v1/v2 ni la publicación original). **URL: `https://localhost:8443`** (solo este equipo, 127.0.0.1; certificado autofirmado: el navegador avisará, elija «Avanzado» → «Continuar»). **Base de ensayo activa:** `df_demo_20261017221940` (compruébela con `status`, abajo). Publicación en la nube: [PENDIENTE: no existe publicación]; este guion no acredita pruebas en nube.
- Fecha y hora de ejecución: ____________ Ejecutó: Rogelio ____________ (nombre/firma solo cuando se ejecute).
- **Usuarios (sin compartir contraseñas por chat):** ya existen `demo_admin` y `demo_lector`, con contraseñas generadas guardadas **solo** en `artifacts/private/t13b/demo_credenciales.txt` (ábralo en su equipo; fuera de Git). Para usar su propia contraseña: `.venv\Scripts\python.exe -m scripts.demo_local create-user --username <su_usuario> --role admin` (la pide dos veces por consola y no la muestra). No anote contraseñas aquí.
- **Comprobar antes de empezar:** `.venv\Scripts\python.exe -m scripts.demo_local status` debe decir «misma base en api y worker … True» y listar tres corridas (histórica activa, histórica sustituida y evaluación final).

## Inicio rápido: cinco pasos

1. Abra `https://localhost:8443`, acepte el aviso del certificado e ingrese como `demo_lector`.
2. En «Corridas» identifique la **histórica de desarrollo (activa, corte 10/07/2026)** y la **evaluación final (T12)**; abra «Ver detalle» de la final.
3. En «Comparación» (final) lea el WAPE a 14 días de `promedio_28` (0,78) frente a RF (0,79): **no es 78 % de acierto**; RF no se declara ganador.
4. En «Recomendaciones» de la histórica activa marque «Solo con pedido», abra «Ver cálculo» de un SKU y lea el rótulo **«Inventario simulado con supuestos; no corresponde al inventario real de la empresa»**.
5. Salga e ingrese como `demo_admin`: verá «Importaciones» (carga) y «Generar una corrida»; no suba archivos reales ni genere corridas durante esta prueba inicial.

## Pasos

La última columna queda **vacía** hasta la ejecución real. Marque en ella lo que observó (cumple / no cumple / comentario).

| N.º | Paso (qué hacer) | Resultado esperado | Resultado real / observación |
|---|---|---|---|
| **A. Acceso** | | | |
| 1 | Abrir `https://localhost:8443` sin sesión | Aparece «Acceso»; no se ve ningún dato | |
| 2 | Ingresar con una contraseña incorrecta | Mensaje «Usuario o contraseña incorrectos.» | |
| 3 | Ingresar con el usuario lector | Entra a «Resumen»; arriba se ve usuario y rol «lector» | |
| 4 | Abrir «Importaciones» | Mensaje de solo lectura; no hay botón de carga | |
| **B. Histórica, generada y final** | | | |
| 5 | Abrir «Corridas» | Tabla con corridas y columna «Tipo»; la activa está marcada «Sí»; hay antigüedad en días | |
| 6 | Localizar una corrida «Histórica de desarrollo (T07)», una «Generada por la aplicación» (si existe) y la «Evaluación final (T12)»; abrir **Ver detalle** de cada una | Cada detalle muestra su tipo; la final muestra advertencias y paquete; la generada dice que no tiene backtest propio | |
| 7 | En el detalle de la final, leer «Período de evaluación» | 01/08/2026 al 21/08/2026 (origen 31/07/2026) | |
| 8 | Explicar con sus palabras en qué se diferencian las tres | Histórica: backtest de desarrollo (origen 10/07); generada: promedio_28 sin observados; final: pronóstico fijo vs agosto observado | |
| **C. Interpretar WAPE** | | | |
| 9 | Abrir «Comparación» (corrida histórica) → «Precisión de los pronósticos (backtest)», nivel SKU, cohorte primaria | Fila `promedio_28` con WAPE en %; leyenda «WAPE = error absoluto total / unidades observadas» | |
| 10 | Cambiar nivel a «Categoría» | El WAPE baja mucho respecto de SKU | |
| 11 | Responder: ¿un WAPE de 87 % significa 87 % de acierto? | No. Significa que el error absoluto acumulado equivale al 87 % del volumen observado (no es precisión) | |
| 12 | Ubicar MAPE y R² | MAPE muestra cobertura y ceros excluidos; R² puede decir «no evaluable» | |
| **D. Inventario simulado y antigüedad** | | | |
| 13 | Abrir «Recomendaciones» | Aviso «Inventario simulado con supuestos; no corresponde al inventario real de la empresa» | |
| 14 | Leer el encabezado de la página | Se ve el origen del pronóstico, fechas objetivo y «inventario simulado al cierre del» (10/07/2026) | |
| 15 | Leer la barra de corrida | Etiqueta, tipo, corte, «antigüedad N día(s) al consultar» y, si N > 7, «Corrida antigua» | |
| 16 | Responder: ¿este stock es el real de la empresa? ¿qué tan reciente es? | No es real; corresponde al cierre del 10/07/2026 | |
| **E. Explicar un pedido** | | | |
| 17 | Filtrar «Solo con pedido» y pulsar **Filtrar** | La lista muestra solo SKU con pedido > 0 | |
| 18 | En un SKU pulsar **Ver cálculo** | Pasos numerados: stock, tránsito, posición, demanda media, pronóstico de 14 días, seguridad, objetivo, pedido | |
| 19 | Con la calculadora verificar: pedido = máx(0, objetivo − (stock + tránsito)) | Coincide con «Pedido sugerido»; no aparece el aviso «no cuadran con la fórmula» | |
| 20 | Explicar el pedido a otra persona usando sus propios datos (SKU, stock, tránsito, objetivo, pedido) y aclarar que es hipotético | Debe poder decir de dónde sale cada número | |
| 21 | Filtrar Estado «Sin inventario simulado» y pulsar **Ver motivo** | Mensaje «Sin inventario simulado al…»; no se calcula pedido ni se supone stock cero | |
| **F. Evaluación final sin recomendaciones** | | | |
| 22 | En «Corridas», abrir la final y pulsar «Ver recomendaciones de esta corrida» | «Esta corrida no tiene recomendaciones de compra»; sin existencias ni pedidos | |
| 23 | Abrir «Pronósticos» con la final | Fechas objetivo 01/08 a 21/08; nota de evaluación final; «no evaluable» no es cero | |
| **G. Administrador (opcional, caso mínimo ya probado)** | | | |
| 24 | Salir e ingresar como admin; abrir «Importaciones» | Aparece «Cargar un archivo Excel» y trabajos recientes | |
| 25 | Reenviar un archivo ya aprobado (si hay uno de prueba) | «Sin cambios» o «Este archivo ya había sido enviado»; sin duplicados | |
| 26 | Salir | Vuelve a «Acceso» | |

## Cierre de la sesión (completar al ejecutar)

- Defectos encontrados (número de paso y descripción): ______________________
- ¿Se pudo explicar WAPE, inventario simulado/antigüedad, tipos de corrida y un pedido? (Sí / No / Parcial por tema): ______________________
- Aceptación humana: **PENDIENTE** (cambiar solo tras la ejecución real y con la anotación de quien corresponda).
- Pendientes ajenos a este guion: validación en nube, cinco usuarios en nube y participación humana adicional (A13/A14 según la matriz de cierre).
