# Manual de usuario — versión entregada (23/10/2026)

**Versión descrita:** aplicación publicada en https://dfpub-api.ashyglacier-9e3e37bc.brazilsouth.azurecontainerapps.io, imagen `t22g-a9119ae` (código `a9119ae`; checkpoint documental: etiqueta Git `entrega-20261023`). Plan de noviembre vigente: **versión 2**, ventas y existencias al corte del **20/10/2026**, escenarios de 7 y 14 días. **Aceptación humana final: pendiente.**

**Cómo leer este manual.** La parte **A** (al final: «Versión de noviembre», «Cómo leer las pantallas principales» y «Qué puedes hacer tú y qué requiere soporte técnico») describe el **plan operativo entregado**. La parte **B** (secciones 1–9) conserva la descripción del **análisis histórico académico** (Mis análisis, Evaluación de resultados, reposición simulada), que sigue disponible en «Más» con su etiqueta «Inventario simulado con supuestos; no corresponde al inventario real de la empresa»; donde la parte B hable de la franja o del menú anterior, **prevalece la parte A**. Material de apoyo: `docs/GUIA_RAPIDA.md`, `docs/EXPLICACION_SIMPLE.md`, `docs/DEMOSTRACION_3110044.md`, `docs/MODELOS_Y_METODO_OPERATIVO.md`, `docs/PREGUNTAS_FRECUENTES_EXPOSICION.md`.

**Límites de esta entrega:** no ejecuta compras; no incorpora datos posteriores al 20/10 desde la interfaz web (desde 07/11/2026 existe un CLI de importación operativa: `scripts/import_operativo.py`; ver `docs/MANUAL_OPERACION.md` §10.1 y `docs/T22_ALCANCE_DATOS_Y_PLAN.md`); no demuestra ahorro; las compras 11452/11455 y 13 diferencias de inventario están pendientes de confirmar por la empresa.

## Parte B — Análisis histórico académico

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
Ventas reales ya cargadas (por defecto 01/01 a 30/09/2026): *Desde*, *Hasta*, *Agrupar por* (Mes, Día, Categoría), *Categoría* y **Consultar**. Las **notas de crédito** se informan aparte (no se restan; no se infiere devolución física) y se listan los **días excluidos del análisis**.

### 5.8 Ayuda (Más)
Primeros pasos (con **Volver a mostrar «Cómo empezar» en Inicio**), «Qué no hace esta aplicación», «Cómo leer el error absoluto (WAPE)» y el glosario con el término técnico entre paréntesis.

### 5.9 Administración (solo administrador)
- **Cargar datos:** 1. Elegir archivo (un `.xlsx` mensual, enero a septiembre de 2026, hasta 25 MiB) y **Subir y procesar**; 2. Revisar el resultado en los trabajos recientes (esperando turno, en curso, terminado, no se pudo completar) y **Ver detalle**; 3. Consultar las ventas registradas o la previsión. Reenviar el mismo archivo no duplica («Este archivo ya había sido enviado»). Cargar no crea análisis. El lector ve en su lugar **Datos cargados**, de solo lectura.
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

## Parte A — Plan operativo

### Antecedente: «Planificar compras» (ensayo 18/10, superado por «Compra recomendada» v2)

**Para qué sirve:** proponer, por producto, una única compra para cubrir todo noviembre de 2026, bajo supuestos visibles. No es un pedido ejecutado ni una mejora comprobada; usa ventas registradas hasta el 30 de septiembre (octubre es desconocido, no cero) y el conteo informado del 18/10/2026 17:00.

**Cómo se lee:** (1) el recuadro «De dónde sale este plan» dice qué es dato real, qué es proyección y qué es supuesto, y a cuántos días del último dato está el mes; (2) la tabla muestra por producto las ventas previstas del mes (sin limitar por stock), el stock del conteo y, para cada plazo de entrega (7 y 14 días), la fecha de llegada, el stock al inicio del mes, la **compra propuesta** y su estado («Cubre noviembre», «Llega tarde», «No llega a tiempo», «No se puede calcular»); un **0** significa «calculado: no hace falta comprar», y «No se puede calcular» no es cero; (3) **Entender la compra** reconstruye la cantidad: stock del conteo → consumo hasta la llegada (y lo que faltó) → stock al llegar → demanda del puente de octubre, de noviembre y reserva → necesidad menos stock → compra redondeada. Un plazo mayor no implica comprar más: puede comprarse menos pero con más ventas no atendidas antes de la llegada.

**Qué no hace:** no suma unidades de productos distintos, no usa valores monetarios, no usa el inventario simulado, no arrastra las ventas perdidas como pedidos atrasados y no actualiza el pronóstico con octubre. Los decimales usan punto (18.214 = 18,2 unidades).

**Administrador:** el formulario permite cambiar mes, fecha de decisión, plazos, reserva, mínimo y múltiplo, y declarar pedidos por recibir (producto, unidades, fecha de llegada y si es reportado o asumido); por defecto «no llegan otros pedidos» (supuesto). Un envío idéntico reutiliza el plan.

## Versión de noviembre (actualización v2, 22/10/2026)
**Menú principal:** *Inicio*, *Ventas previstas*, *Existencias*, *Compra recomendada* y *Mis análisis*. En *Más → Evaluación académica* están los análisis históricos con inventario simulado (no corresponden al inventario real de la empresa).
- **Inicio:** resume el plan de noviembre vigente: versión, fecha de decisión, corte de ventas (último día completo: 20/10/2026), existencia inicial y cuántos productos tienen compra recomendada.
- **Ventas previstas:** ventas previstas del mes y por día de cada producto, calculadas con el promedio de los últimos 28 días de ventas (23/09–20/10). Es una proyección bajo supuestos, no ventas observadas.
- **Existencias:** existencia reconstruida al cierre del 20/10 (conteo reportado del 18/10 17:00 + movimientos del sistema). Los productos cuya existencia reconstruida difiere del stock del sistema (misma fecha de comparación) se marcan «Diferencia con el sistema»; no se ajustó ninguna cantidad.
- **Compra recomendada:** por producto y para entregas de 7 y 14 días, con «Entender la compra» (pasos y día a día desde el 21/10). Los plazos y la reserva son parámetros configurados (*Configuración de reposición*), no condiciones confirmadas del proveedor. No se registran pedidos adicionales por recibir; se supone que no llegan otros (supuesto, sin confirmar con la empresa).
- **Pendientes de confirmar con la empresa:** las compras 11452 y 11455 (fecha de recepción futura registrada) y las diferencias de inventario. Se muestran como pendientes.
- **Comparar con otra versión:** en Compra recomendada, compara el plan del 18/10 con el del 21/10 por producto (las existencias son de fechas distintas).

### Cómo leer las pantallas principales (versión publicada el 22/10/2026)
- **Dónde:** https://dfpub-api.ashyglacier-9e3e37bc.brazilsouth.azurecontainerapps.io — inicia sesión con el usuario que te dio el administrador (lector: consulta; administrador: además genera planes y carga Excel).
- **Todas las pantallas del plan** abren con un aviso de una línea («Plan de compra bajo supuestos…», «Existencia reconstruida (no es simulada)…», «La previsión es una proyección bajo supuestos…») y un resumen corto de fechas y procedencia: *Dato real* (ventas hasta el 20/10), *Dato de la empresa* (existencias al cierre del 20/10, reconstruidas del conteo del 18/10 + movimientos del sistema), *Proyección* (promedio de 28 días) y *Supuesto* (lo posterior al corte es desconocido, no cero; sin pedidos adicionales registrados, pendiente de confirmar).
- **Tablas anchas** (Ventas previstas, Existencias, Compra recomendada): usan todo el ancho; la primera columna queda fija; si tu pantalla es estrecha, desplaza la tabla hacia los lados. Los encabezados son cortos; el significado completo de cada columna está en **«Cómo leer la tabla»** (enlace junto a los filtros, cerrado por defecto; se abre con Enter).
- **Existencias:** «Conteo 18/10», «Entradas», «Salidas», «Existencia al 20/10» y «Diferencia» (solo en los productos donde el sistema y la reconstrucción no coinciden; pendiente de confirmar, sin ajustes). «2 pendientes de confirmar con la empresa · Ver detalle» muestra las compras 11452/11455 y las diferencias de inventario.
- **Compra recomendada:** «Plazo de 7 días / 14 días» con *Llegada*, *Stock al 1/11* (según el mes), *Comprar* («Cubre el mes», «Llega tarde», «No llega a tiempo») y *Faltantes* («Antes» del mes y «Mes»). «Entender la compra» muestra primero cantidad, llegada, ventas que podrían atenderse y faltantes; una frase resume el cálculo y **«Ver cálculo detallado»** (cerrado) guarda los 14 pasos. Si un plazo largo compra menos **porque la llegada tardía deja ventas sin atender**, una nota lo explica con las cifras del producto: no es una opción equivalente con ahorro.
- **Formato de números:** el punto separa decimales (18.214 son 18 unidades y 214 milésimas) y la coma separa miles (1,250).

### Qué puedes hacer tú y qué requiere soporte técnico (22/10/2026)
| Tarea | Lector | Administrador (interfaz) | Soporte técnico |
|---|---|---|---|
| Consultar Inicio, Ventas previstas, Existencias, Compra recomendada, «Entender la compra» | Sí | Sí | — |
| Generar una versión nueva del plan con otros parámetros (decisión, plazos, reserva, mínimo, múltiplo, pedidos por recibir) | No | **Sí**: «Compra recomendada» → «Generar plan». Si todo es idéntico se reutiliza la versión existente | — |
| Cargar un Excel mensual en «Cargar datos» | No | Sí, **solo ventas de enero a septiembre de 2026**: alimenta los análisis históricos, **no el plan de noviembre** | — |
| «Crear análisis» | No | Sí, **solo históricos**: cortes del 01/06 al 10/07/2026, 21 días, promedio de 28 días | — |
| Incorporar ventas o existencias posteriores al 20/10/2026 y actualizar el plan de noviembre con ellas | No | **No** (la interfaz no lo permite) | **Sí**: desde 07/11 disponible el CLI `scripts/import_operativo.py` (ver `docs/MANUAL_OPERACION.md` §10.1) para importar a MongoDB local sin mongorestore. La publicación a la nube sigue requiriendo el paso 5 de §10 (ver `docs/T22_ALCANCE_DATOS_Y_PLAN.md`) |
| Cambiar las reglas del servidor (meses permitidos, cortes, horizonte) | No | No | Sí, con encargo aparte posterior a la evaluación final |
| Confirmar las compras 11452/11455 y las 13 diferencias de inventario | — | — | Lo confirma la empresa; luego soporte actualiza los datos |
- **Estado del sistema** (administrador): indica si el servicio y la base de datos responden; no depende del plan ni del inventario.
- **Por qué «Cargar datos» y «Crear análisis» tienen límites:** son reglas del servidor para definir el alcance del proyecto académico; no son textos viejos.

### Documentación técnica complementaria

Para profundizar en el método de pronóstico, las métricas de evaluación y las variables del pipeline:

| Documento | Contenido |
|---|---|
| `docs/DICCIONARIO_VARIABLES.md` | Variables, constantes, features y parámetros del pipeline con sus valores, archivos y procedencia |
| `docs/EVALUACION_T06_T07_METRICAS.md` | Diseño experimental, fórmulas de métricas (WAPE, MAE, RMSE, MAPE, R²) y resultados T06/T07/T12 |
| `docs/T12_RESULTADOS.md` | Resultados completos de la evaluación final de agosto (evidencia histórica cerrada) |
| `docs/MODELOS_Y_METODO_OPERATIVO.md` | Explicación del método operativo (promedio 28 días) y por qué se eligió sobre el modelo ML |
