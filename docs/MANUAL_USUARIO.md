# Manual de usuario (borrador)

Estado: borrador T14A, versión de código de referencia `28a5f49` (18/10/2026). Describe las pantallas tal como existen en `frontend/src`. No hay publicación: **URL pública: [PENDIENTE: no existe publicación]**. Hoy el sistema solo se ejecuta en el equipo local (ver `docs/GUIA_LOCAL.md` y `docs/MANUAL_OPERACION.md`).

## 1. Qué es y qué no es

Sistema de pronóstico de demanda y recomendaciones de reposición para una MYPE, construido con **datos históricos de marzo a agosto de 2026**. No pronostica octubre ni ejecuta compras. Todo lo que ve sobre stock, tránsito, costos y pedidos viene de un **inventario simulado**.

Aviso que aparece en pantalla: **«Inventario simulado con supuestos; no corresponde al inventario real de la empresa».**

## 2. Acceder

1. Abra la dirección que le indique el administrador (local: `http://localhost:4200`).
2. En la pantalla **Acceso** escriba *Usuario* y *Contraseña* y pulse **Ingresar**.
3. No existe registro público: la cuenta la crea el administrador por línea de comandos. Si olvidó la contraseña, pídale otra al administrador.
4. Mensajes: «Usuario o contraseña incorrectos.» Tras 5 fallos seguidos del mismo usuario desde el mismo equipo (o 20 desde un mismo equipo) el acceso se bloquea unos 15 minutos.
5. La sesión dura como máximo 8 horas y se cierra tras 1 hora sin actividad. Para salir pulse **Salir** (arriba a la derecha, junto a su usuario y rol).

Roles: **lector** (solo consulta) y **admin** (además carga archivos y genera corridas). El menú y los botones de escritura que no le corresponden no aparecen; el servidor rechaza igualmente cualquier escritura de un lector.

Teclado: el enlace «Saltar al contenido» aparece con la tecla Tab al inicio de cada página.

## 3. Menú principal

Resumen · Importaciones · Corridas · Pronósticos · Recomendaciones · Comparación · Sistema.

### 3.1 Resumen (ventas y calidad de datos)
Ventas observadas del Excel (desde 01/06 hasta 31/07/2026 por defecto). Filtros *Desde*, *Hasta*, *Agrupar por* (Mes, Día, Categoría) y *Categoría*; pulse **Consultar**. Debajo: **Notas de crédito** (informadas aparte, no restadas; no se infiere devolución física) y **Días excluidos del análisis**. Agosto no se entrega aquí.

### 3.2 Corridas: histórica, generada y final
Una *corrida* es un conjunto publicado de pronósticos. Hay tres tipos y nunca se sustituyen entre sí (columna **Tipo**):

| Tipo en pantalla | Qué es | Qué hacer con ella |
|---|---|---|
| **Histórica de desarrollo (T07)** | Backtest de desarrollo con origen 10/07/2026; es la corrida **activa** por defecto y la única con recomendaciones validadas | Úsela para ver pronósticos, recomendaciones simuladas y la comparación de métodos |
| **Generada por la aplicación** | `promedio_28` calculado por la aplicación para un origen elegido por el administrador (horizonte 21 días); no tiene ventas observadas posteriores ni backtest propio | Es una demostración de generación; no activa la corrida por defecto |
| **Evaluación final (T12)** | Pronóstico fijado el 31/07/2026 comparado con las ventas ya observadas del 01 al 21/08/2026 (un solo bloque) | Sirve para evaluar, **no genera recomendaciones ni pedidos** |

Pulse **Ver detalle** para ver estado (Completada / Sustituida), fechas (origen, fechas objetivo, período de evaluación), método, cobertura y enlaces «Ver pronósticos / recomendaciones / comparación de esta corrida». Cada corrida muestra su **antigüedad** al consultar; si supera 7 días aparece «Corrida antigua». Una corrida **Sustituida** (corrección de precisión) muestra un aviso rojo: no use sus pedidos y abra la corrida corregida con el enlace.

### 3.3 Pronósticos
Elija la **Corrida** en el selector (la elección se conserva al ir a Recomendaciones y Comparación mediante el parámetro `run` de la dirección). Filtre por *Nivel* (SKU o Categoría), SKU, Categoría, Cohorte, fechas y *Orden*; pulse **Filtrar**. Columnas: `promedio_28 (elegido)` es el método operativo (promedio móvil de 28 días); `RF distribuido (comparador)` es un modelo experimental que no mejora el hallazgo principal; `cero (control)` es solo una referencia. «Observado» existe solo en la histórica y en la final; en la generada figura «no disponible para esta corrida» (no es cero). En la final, un día sin ningún registro se rotula «no evaluable».

### 3.4 Recomendaciones y su explicación paso a paso
1. Abra **Recomendaciones**. Siempre se ve el aviso de inventario simulado. Arriba figura el origen del pronóstico, las fechas objetivo y la fecha del inventario simulado.
2. Filtre por SKU, Categoría, Estado (*Con inventario simulado* / *Sin inventario simulado*), *Solo con pedido* y *Orden*; pulse **Filtrar**.
3. En una fila con inventario pulse **Ver cálculo**. Se muestran, numerados: (1) stock simulado, (2) en tránsito, (3) posición = stock + tránsito, (4) demanda media diaria (promedio de 28 días), (5) pronóstico de 14 días, (6) stock de seguridad (7 días de demanda media), (7) objetivo = pronóstico + seguridad redondeado hacia arriba, (8) **pedido sugerido = máx(0, objetivo − posición)**, y (9) valor supuesto del pedido en PEN. «Detalle técnico» muestra los valores exactos publicados.
4. Si una fila dice «Sin inventario simulado al…», **Ver motivo** explica por qué; el sistema no supone stock cero ni calcula pedido.
5. Si el cálculo mostrado no cuadra con la fórmula aparece el aviso «Los valores publicados no cuadran con la fórmula»; no use ese pedido.
6. Si elige una corrida de **evaluación final**, la pantalla indica «Esta corrida no tiene recomendaciones de compra» y ofrece un enlace a la demostración histórica. Es el comportamiento correcto.

El pedido es **hipotético**: no es una compra ejecutada ni una instrucción. Cantidades en «unidad base»; costos supuestos en PEN.

### 3.5 Comparación
Backtests y simulación. Para la histórica: selector **Backtest**, y dos bloques.
- *Simulación de reposición: tres políticas* (referencia fija, `promedio_28`, RF) para el escenario elegido (plazo L, seguridad S, cohorte). Más servicio suele venir con más stock y más compras: no es ganancia neta.
- *Precisión de los pronósticos (backtest)*: WAPE, MAE, RMSE, sesgo, sub/sobrepronóstico, MAPE y R² con selectores de nivel, cohorte, horizonte y pliegue (fold).
Para la evaluación final se muestra la comparación del único bloque con sus advertencias.

### 3.6 Sistema
Estado general (operativo/degradado), base de datos y versión de la API.

## 4. Cargar y generar (solo administrador)

**Importaciones → Cargar un archivo Excel**
1. Elija un `.xlsx` mensual (marzo a julio de 2026, hasta 25 MiB). El navegador solo avisa de forma temprana (extensión, tamaño); el servidor decide.
2. Pulse **Subir y procesar**. El procesamiento ocurre en segundo plano (worker); puede recargar la página sin perder el trabajo. Siga el estado en **Trabajos de importación recientes** (En cola, En ejecución, Completado, Fallido) y use **Ver detalle de la importación**.
3. Reenviar el mismo archivo no duplica: aparece «Este archivo ya había sido enviado» o «Sin cambios». Otro archivo para un mes ya aprobado se rechaza con un motivo; agosto se rechaza. La sustitución de una fuente aprobada no se hace desde la pantalla (ver `docs/REMEDIACION_FUENTES.md`).

**Corridas → Generar una corrida de desarrollo**
1. Elija el *Origen (fecha de corte)* entre los límites que indica la pantalla (01/06 a 10/07/2026). Horizonte (21 días) y método (`promedio_28`) son fijos.
2. Pulse **Generar** y siga el trabajo en «Trabajos de generación recientes»; al terminar use «Ver la corrida generada».
3. La corrida generada no cambia la corrida por defecto. Si el origen es distinto del 10/07 puede no haber comparador RF ni recomendaciones.

El lector verá «Esta pantalla es de solo lectura para su rol».

## 5. Cómo interpretar los límites

- **WAPE no es precisión porcentual.** WAPE = error absoluto total / unidades observadas. Un WAPE de 0,78 significa que el error absoluto acumulado equivale al 78 % del volumen observado; no «78 % de acierto». Menor es mejor. Un valor sobre 100 % es posible. Los WAPE por SKU son altos (la demanda es intermitente); por categoría son mucho menores porque los errores se compensan.
- **MAPE** solo se calcula con ventas reales positivas; se muestra su cobertura y los ceros excluidos. **R²** puede ser «no evaluable» (indefinido) y no debe leerse como porcentaje de acierto.
- **Inventario simulado:** stock, tránsito, costos y plazos son supuestos del simulador (procedencia `SYNTHETIC_NOT_REAL_INVENTORY`). No corresponde al inventario real de la empresa ni demuestra una mejora real.
- **Antigüedad:** el inventario simulado corresponde al cierre del 10/07/2026 (fecha mostrada) y la corrida tiene su corte; mire siempre «antigüedad N día(s) al consultar» antes de interpretar.
- **Ventas posiblemente censuradas:** la demanda es la venta observada, que puede estar limitada por falta de stock; los faltantes reales se desconocen.
- **Evaluación final sin recomendaciones:** compara pronósticos con agosto observado; no crea pedidos. Es un solo bloque de 21 días: no permite declarar ganador.
- Los folds de desarrollo se solapan: el agregado no es una evaluación independiente. Se muestran también los resultados desfavorables y el control «cero».
- Notas de crédito se informan aparte; no se infiere devolución física.

## 6. Resolución de problemas

| Síntoma | Qué hacer |
|---|---|
| No puedo ingresar | Revise usuario y contraseña; tras 5 fallos espere unos 15 minutos; pida al administrador una cuenta nueva o restablecida |
| «Sesión expirada» | Vuelva a ingresar (límite 8 h o 1 h sin actividad) |
| Pantalla con error de API / «Reintentar» | Pulse el botón; si persiste, revise **Sistema** y avise al administrador (API o base caída) |
| No veo Importaciones/Generar | Su rol es lector; solo el administrador carga y genera |
| La carga se rechaza | Lea el motivo: extensión, tamaño (>25 MiB), fechas fuera de marzo–julio, mes con fuente ya aprobada |
| El trabajo queda «En cola» | El worker puede no estar activo; avise al administrador |
| Recomendaciones vacías en una corrida | Si es evaluación final o generada con otro origen, es esperado (ver 3.4) |
| Aviso rojo de corrida sustituida | No use sus pedidos; abra la corrida corregida |
| Fechas de agosto no disponibles | Agosto está reservado; solo la evaluación final lo muestra, hasta el 21/08 |

## 7. Alcance de este manual

No hay URL ni usuarios públicos de demostración. Los pasos de despliegue, HTTPS externo y aceptación por usuarios reales están pendientes; este manual no los afirma.
