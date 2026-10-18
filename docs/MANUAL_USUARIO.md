# Manual de usuario (borrador, interfaz UX01)

Estado: borrador. Versión de la interfaz: commit `f95092f` (imagen `df-app:ux01r-f95092f`), tras el rediseño UX01 (17/10/2026). Describe las pantallas tal como existen en `frontend/src`. No hay publicación: **URL pública: [PENDIENTE: no existe publicación]**. Hoy el sistema solo se ejecuta en el equipo local (ver `docs/GUIA_LOCAL.md` y `docs/MANUAL_OPERACION.md`). La comprensión de la interfaz por una persona real sigue siendo una observación abierta (ver `docs/UX01_DECISIONES.md`).

## 1. Qué es y qué no es

Es una aplicación para **consultar cuántas unidades se estimó vender de cada producto** y **entender cómo se calcularía una sugerencia de reposición**, con datos históricos de ventas de marzo a agosto de 2026 de una MYPE. Es un ejemplo de trabajo: no pronostica ventas de hoy ni de octubre.

Todo lo que ve sobre disponible, por recibir, costos y pedidos viene de un **inventario simulado**. Aviso exacto que aparece junto a esos resultados: **«Inventario simulado con supuestos; no corresponde al inventario real de la empresa».** En todas las pantallas se ve además la franja: «Ejemplo con datos históricos de 2026. El inventario es simulado; no representa las existencias actuales».

**Qué NO hace** (también en *Ayuda → Qué no hace esta aplicación*):
- No es su inventario real.
- No ejecuta compras ni envía pedidos a proveedores: las cantidades sugeridas son un escenario para entender el cálculo.
- No pronostica las ventas de hoy ni de los próximos días.
- Consultar nunca crea trabajos ni cambia datos; solo el administrador carga archivos o crea análisis.
- No muestra nombres comerciales de productos (los archivos no los traen autorizados): se ve «Producto 1010004 · Higiene capilar» (código y categoría).

## 2. Acceder

1. Abra la dirección que le indique el administrador (demostración local: `https://localhost:8443`; el certificado es autofirmado y el navegador avisará: «Avanzado» → «Continuar»; en desarrollo `http://localhost:4200`).
2. En **Acceso** escriba *Usuario* y *Contraseña* y pulse **Ingresar**.
3. No existe registro público: la cuenta la crea el administrador por línea de comandos. Si olvidó la contraseña, pídale otra.
4. Mensaje de error: «Usuario o contraseña incorrectos.» Tras 5 fallos seguidos del mismo usuario desde el mismo equipo (o 20 desde un mismo equipo) el acceso se bloquea unos 15 minutos.
5. La sesión dura como máximo 8 horas y se cierra tras 1 hora sin actividad. Para salir pulse **Salir** (arriba a la derecha, junto a su usuario y rol).

Roles: **lector** (solo consulta) y **admin** (además carga archivos y crea análisis). El menú y los botones que no le corresponden no aparecen; el servidor rechaza igualmente cualquier escritura de un lector.

Teclado: el enlace «Saltar al contenido» aparece con Tab al inicio de la página. En pantallas estrechas el menú está en el botón **Menú**.

## 3. El menú

- **Principal:** Inicio · Ventas previstas · Reposición simulada · Mis análisis.
- **Más:** Ventas registradas · Evaluación de resultados · Datos cargados (solo lector) · Ayuda.
- **Administración** (solo admin): Cargar datos · Crear análisis · Estado del sistema.

Al cambiar de pantalla el análisis que eligió se conserva.

## 4. Conceptos que verá en pantalla

| Texto en pantalla | Qué significa |
|---|---|
| **Análisis** | Un conjunto de resultados que puede consultar: el ejemplo histórico, los que se crean en la aplicación y la evaluación de agosto |
| **Ventas utilizadas hasta** | Última fecha de ventas registradas que usó el cálculo; nada posterior influyó. Junto a ella figura «hace N días; datos históricos, no las ventas de hoy» |
| **Período estimado** | Fechas para las que se estimaron ventas (por ejemplo, del 11/07/2026 al 31/07/2026) |
| **Ejemplo de julio** | Análisis histórico con ventas utilizadas hasta el 10/07/2026: compara estimaciones con ventas ya registradas y permite explorar la reposición simulada |
| **Análisis creado con ventas hasta el …** | Creado por el administrador desde la aplicación; no tiene todavía ventas registradas para comparar |
| **Evaluación de agosto** | Compara estimaciones fijadas el 31/07 con las ventas registradas del 01 al 21/08/2026; **no genera pedidos** |
| **Promedio de los últimos 28 días** | Método elegido para estimar las ventas diarias |
| **Modelo experimental** | Un segundo método (bosque aleatorio) solo para comparar; no resultó mejor y no se usa para decidir |
| **Por recibir (simulado)** | Unidades que, en el escenario simulado, ya fueron pedidas y aún no llegan |

### «En uso por defecto» frente a «Seleccionado para consultar»

- **En uso por defecto:** el análisis que la aplicación abre cuando usted no elige otro. Lo decide el servidor y **no cambia** por lo que usted haga.
- **Seleccionado para consultar:** el análisis que usted eligió en esta sesión para mirarlo (botón **Elegir este análisis** en *Mis análisis*, o el selector «Análisis» en *Ventas previstas*). Solo cambia lo que usted ve.
- También pueden aparecer **Disponible** (existe, no está elegido) y **Versión reemplazada** (ver 5.6). En una tarjeta, «Estás consultando este análisis» indica cuál está abierto.

## 5. Recorridos

### 5.1 Inicio
Título «Explora las ventas previstas y una simulación de reposición». Debajo, la **barra de análisis** (nombre, estado, «Ventas utilizadas hasta», período estimado, **Cambiar de análisis**, y «Detalles técnicos del análisis» plegado). Tres tarjetas: **Ver previsión**, **Explorar reposición simulada**, **Ver mis análisis**. Una cifra resume cuántos productos tienen sugerencia de reposición en el ejemplo (en la captura de ensayo: 582), con la aclaración «inventario simulado; no son existencias reales». Con la evaluación de agosto elegida no hay pedidos y lo dice. El bloque «Cómo empezar» tiene tres pasos; **Entendido, cerrar** lo oculta y se recupera desde **Ayuda**.

### 5.2 Ventas previstas
1. Entre por **Ventas previstas** (o **Ver previsión** en Inicio o en una tarjeta de *Mis análisis*).
2. Arriba lea las fechas: «Ventas utilizadas hasta … · fechas estimadas: … al …».
3. Busque un producto escribiendo su *Código del producto* (o una *Categoría*, o fechas *Desde/Hasta*) y pulse **Buscar**. «Ver por» cambia entre **Producto** y **Categoría**. «Más filtros» trae tipo de historial y orden. El selector «Análisis» cambia de análisis.
4. La tabla muestra: Producto, Fecha, **Cantidad estimada (unidades base)** y, si el análisis tiene ventas registradas, **Vendido (registrado)**. La cantidad estimada es la venta diaria que calcula el promedio de los últimos 28 días.
5. **Comparar métodos / ver detalles** agrega identificador, tipo de historial, día de la previsión, modelo experimental (si existe), control «siempre cero» y «Evaluable». «Cómo leer esta tabla» (plegado) explica las columnas.
6. «no evaluable» o «no disponible para esta corrida» **no son cero**: son un dato ausente. En un análisis creado en la aplicación aún no hay ventas registradas para comparar.
7. Agosto está reservado: solo la evaluación de agosto muestra fechas hasta el 21/08/2026.

### 5.3 Reposición simulada
1. Entre por **Reposición simulada**. Verá el aviso «Inventario simulado con supuestos; no corresponde al inventario real de la empresa», la barra de análisis y una línea con las fechas («Ventas utilizadas hasta …, período a cubrir …, inventario simulado al cierre del …»).
2. La **Vista** tiene tres botones: **Con sugerencia de reposición** (inicial), **Sin necesidad de reponer en el ejemplo** y **Sin datos de inventario**. Filtre por *Código del producto* o *Categoría* y pulse **Buscar**. El total mostrado viene del servidor.
3. La tabla tiene: Producto, Disponible simulado (unidades), Cantidad sugerida (unidades base) y el botón **Entender sugerencia**.
4. Al pulsar **Entender sugerencia** se abre el detalle: «En este ejemplo se sugieren N unidades (hipotético; inventario simulado al cierre del …)» y **tres pasos**:
   1. *Con qué se cuenta*: disponible simulado + por recibir (simulado) = suma de lo que se tiene o está por llegar.
   2. *Qué se busca cubrir*: ventas previstas para 14 días + reserva de seguridad de 7 días de ventas, redondeado hacia arriba = objetivo.
   3. *De dónde sale la cantidad*: objetivo − lo que se tiene o está por llegar; si el resultado fuera negativo se sugiere 0.
5. **Ver cálculo completo y supuestos** despliega los nueve pasos con la misma aritmética (stock, en tránsito, posición, demanda media diaria, pronóstico, seguridad, objetivo, pedido sugerido = máx(0, objetivo − posición), valor supuesto en PEN con el costo unitario supuesto), las verificaciones «coherente», las fechas, el plazo de entrega y «Detalle técnico y valores exactos publicados». Si algo no cuadra aparece «Los valores publicados no cuadran con la fórmula»: no use esa cifra.
6. En la vista **Sin datos de inventario**, la fila dice «Sin datos de inventario al …» y **Ver qué falta** explica qué información falta. La aplicación no supone stock cero ni calcula cantidad.
7. **Cerrar detalle** vuelve a la lista. La sugerencia es hipotética: no es una compra ni una instrucción.
8. Si elige la evaluación de agosto aparece «Este análisis no genera pedidos» y un botón para abrir el ejemplo con reposición simulada. Es el comportamiento correcto.

### 5.4 Mis análisis
Una tarjeta por análisis: nombre, estado («En uso por defecto», «Seleccionado para consultar», «Disponible», «Versión reemplazada»), tipo («Ejemplo histórico», «Creado en la aplicación», «Evaluación»), para qué sirve, «Ventas utilizadas hasta» y «Período estimado». Botones: **Ver previsión**, **Ver reposición** (no existe en la evaluación), **Ver evaluación**, **Elegir este análisis**. «Detalles técnicos» (plegado) trae identificador, fases, cobertura y documento publicado. **Ver versiones anteriores (N)** muestra los análisis reemplazados por una corrección: se conservan para consulta, **no use sus sugerencias**. El administrador ve además **Crear un análisis nuevo**.

### 5.5 Evaluación de resultados (menú «Más»)
Responde «¿Qué tan cerca estuvieron las estimaciones de las ventas registradas?». **Al llegar ves solo lo esencial:** el análisis y sus fechas, el alcance en palabras simples («productos con historia suficiente · acumulado de 14 días · N productos»), **una explicación** del error del promedio de 28 días («equivale a cerca del X % del volumen vendido; no significa X % de acierto; es un error alto por producto»), los dos períodos con etiquetas distintas (**Métrica del 01 al 14 de agosto** y **Bloque de prueba disponible del 01 al 21 de agosto**, derivados de los datos), un aviso breve (con un solo bloque de prueba no se declara método ganador) y el botón **Ver cómo se evaluó**. Ese botón abre **«Ver cómo se evaluó: detalle académico»**, que trae la tabla del hallazgo primario (promedio de 28 días, modelo experimental y control cero, con error y sesgo), la mejora relativa, las advertencias completas publicadas, la cobertura y los métodos de cálculo. Hay dos pestañas: **Estimaciones frente a ventas registradas** y **Comparación de reposición simulada** (esta lleva el aviso «Inventario simulado con supuestos; no corresponde al inventario real de la empresa» y recuerda que más servicio puede venir con más stock y compras, sin atribuir impacto real). Para el ejemplo de julio el resultado es un **resultado agregado de 4 bloques** (se suman estadísticas y se calcula la métrica conjunta; no es una media de métricas). Si el análisis no tiene comparación (por ejemplo, uno creado en la aplicación) la pantalla dice que **ese análisis no incluye una evaluación contra ventas registradas, por diseño**, y ofrece **Ir a «Mis análisis»**.

### 5.6 Versión reemplazada
Una versión corregida reemplaza a la anterior. Aviso rojo: «Esta versión fue reemplazada. No uses sus sugerencias», con enlace «Ver el análisis corregido» y el motivo plegado.

### 5.7 Ventas registradas (Más)
Ventas reales ya cargadas (por defecto 01/06 a 31/07/2026): *Desde*, *Hasta*, *Agrupar por* (Mes, Día, Categoría), *Categoría* y **Consultar**. Las **notas de crédito** se informan aparte (no se restan; no se infiere devolución física) y se listan los **días excluidos del análisis**. No se entrega agosto en esta vista.

### 5.8 Ayuda (Más)
Primeros pasos (con **Volver a mostrar «Cómo empezar» en Inicio**), «Qué no hace esta aplicación», «Cómo leer el error absoluto (WAPE)» y el glosario con el término técnico entre paréntesis.

### 5.9 Administración (solo administrador)
- **Cargar datos:** 1. Elegir archivo (un `.xlsx` mensual, marzo a julio de 2026, hasta 25 MiB; agosto se rechaza) y **Subir y procesar**; 2. Revisar el resultado en los trabajos recientes (esperando turno, en curso, terminado, no se pudo completar) y **Ver detalle**; 3. Consultar las ventas registradas o la previsión. Reenviar el mismo archivo no duplica («Este archivo ya había sido enviado»). Cargar no crea análisis. El lector ve en su lugar **Datos cargados**, de solo lectura.
- **Crear análisis:** elija «Ventas utilizadas hasta (fecha)» dentro del rango que indica la pantalla; período estimado (21 días siguientes) y método (promedio de los últimos 28 días) son fijos; pulse **Crear análisis**. Al terminar: «Listo: el análisis se creó», con **Ver previsión** y **Ver en Mis análisis**. No reentrena modelos. Un lector ve «Solo el administrador puede crear análisis».
- **Estado del sistema:** funcionando / con fallas, base de datos y versión; **Volver a comprobar**.

## 6. Cómo leer el error (WAPE)

- El error absoluto (WAPE) es la suma de los errores dividida entre las unidades vendidas. **Menor es mejor.**
- **No es porcentaje de acierto.** Un WAPE de 0,78 equivale a un error acumulado de alrededor del 78 % del volumen vendido; no significa 78 % de acierto. Puede superar 100 %.
- Por producto el error es alto (la demanda es intermitente); por categoría es mucho menor porque los errores se compensan, pero una categoría suma unidades de productos distintos.
- «no evaluable» (por ejemplo MAPE o R² indefinidos) no es cero. MAPE solo se calcula con ventas positivas y muestra su cobertura.

## 7. Límites que conviene recordar

- **Inventario simulado:** disponible, por recibir, costos y plazos son supuestos del simulador. No corresponde al inventario real ni demuestra una mejora real.
- **Ventas posiblemente limitadas por stock:** la demanda es la venta registrada, que puede estar limitada por falta de existencias; los faltantes reales se desconocen.
- **Evaluación sin pedidos:** la evaluación de agosto compara estimaciones con ventas registradas; no crea pedidos. Es un solo bloque de 21 días: no permite declarar ganador.
- Los bloques de evaluación de desarrollo se solapan: el agregado no es una evaluación independiente. Se muestran también los resultados desfavorables y el control «cero».
- Más servicio viene con más stock y más compras: no es ganancia neta.
- Notas de crédito aparte; no se infiere devolución física.
- Los datos son históricos: «Ventas utilizadas hasta … (hace N días)» no son las ventas de hoy.

## 8. Resolución de problemas

| Síntoma | Qué hacer |
|---|---|
| No puedo ingresar | Revise usuario y contraseña; tras 5 fallos espere unos 15 minutos; pida una cuenta nueva al administrador |
| «Sesión expirada» | Vuelva a ingresar (límite 8 h o 1 h sin actividad) |
| Pantalla con error / «Reintentar» | Pulse el botón; si persiste, avise al administrador (**Estado del sistema**) |
| No veo Cargar datos ni Crear análisis | Su rol es lector; solo el administrador los usa |
| La carga se rechaza | Lea el motivo: extensión, tamaño (>25 MiB), fechas fuera de marzo–julio, mes ya aprobado |
| El trabajo queda «Esperando turno» | El procesador puede no estar activo; avise al administrador |
| La lista de reposición está vacía | Pruebe otra **Vista** o quite filtros; en la evaluación de agosto es esperado; en un análisis creado puede faltar inventario simulado para su fecha |
| Aviso rojo de versión reemplazada | No use esas sugerencias; abra el análisis corregido |
| Fechas de agosto no disponibles | Agosto está reservado; solo la evaluación de agosto lo muestra, hasta el 21/08 |

## 9. Alcance de este manual

No hay URL ni usuarios públicos de demostración. Los pasos de despliegue, HTTPS externo y la aceptación humana están pendientes; este manual no los afirma. Las contraseñas de las cuentas de ensayo no se escriben aquí.
