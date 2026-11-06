# T13D — Acta del recorrido de aceptacion humana

**Fecha de ejecucion:** 2026-11-06
**Ejecuto:** Milton
**Entorno:** `df-equipo` (puerto 8446, base `df_equipo_20261023135040`, imagen `df-app:equipo`)
**URL:** `https://localhost:8446`
**Usuarios:** `equipo_lector` / `equipo_admin`

**Nota:** Este recorrido es una pre-aceptacion ejecutada por Milton (equipo de desarrollo).
La aceptacion formal (A14) requiere a Rogelio con la interfaz nueva y queda pendiente.
El entorno `equipo` usa la interfaz v2 (plan operativo de noviembre), cuyo menu difiere
del guion original (escrito para `df-demo`).

---

## Resultados por paso

| N.o | Paso | Resultado |
|---|---|---|
| **A. Acceso e Inicio** | | |
| 1 | Abrir URL sin sesion | Cumple — aparece pantalla de acceso |
| 2 | Contrasena incorrecta | Cumple — mensaje de error |
| 3 | Ingresar como lector | Cumple — Inicio con franja de datos historicos (interfaz v2: plan operativo nov.) |
| 4 | Mirar el menu | Parcial — menu v2 distinto al guion: Inicio, Ventas previstas, Existencias, Compra recomendada, Mis analisis; MAS: Ventas registradas, Evaluacion de resultados, Evaluacion academica, Eval. academica: ventas previstas, Datos cargados, Ayuda. No hay "Reposicion simulada" directa |
| 5 | Leer barra de analisis y cifra | Cumple tras aclaracion — "Plan de compra vigente" con Dato real / Dato empresa / Proyeccion, "19 de 50" |
| 6 | Abrir Datos cargados | Cumple — solo lectura, lista de archivos |
| **B. Mis analisis** | | |
| 7 | Abrir Mis analisis | Cumple — tarjetas de analisis visibles |
| 8 | Elegir evaluacion de agosto | Cumple — aparece "Seleccionado para consultar" |
| 9 | Ver versiones anteriores | Cumple — lista de versiones reemplazadas con aviso |
| 10 | Explicar "En uso" vs "Seleccionado" | Cumple tras aclaracion — entendio la diferencia |
| **C. Ventas previstas** | | |
| 11 | Abrir Ventas previstas | Cumple — tabla con columnas esperadas |
| 12 | Buscar por codigo | Cumple — filtra a ese producto |
| 13 | Comparar metodos/detalles | Cumple — identificador, tipo historial, modelos |
| 14 | Elegir analisis creado en la app | N/A — no existe analisis creado en entorno equipo |
| **D. Interpretar el error (WAPE)** | | |
| 15 | Abrir Evaluacion de resultados | Cumple — vista breve con error y boton "Ver como se evaluo" |
| 16 | Cambiar nivel a Categoria | Cumple — el error baja |
| 17 | Responder: 87% = acierto? | Cumple — entendio que no; es error acumulado equivalente al volumen |
| 18 | Abrir detalle academico | Cumple — tabla completa con metodos, WAPE, MAPE, cobertura |
| **E. Reposicion simulada** | | |
| 19 | Abrir Reposicion simulada | Cumple — accedido via Mas > Evaluacion academica (menu v2 no tiene "Reposicion simulada" directa) |
| 20 | Entender sugerencia | Cumple — "En este ejemplo se sugieren N unidades (hipotetico)" con tres pasos |
| 21 | Verificar formula con calculadora | Parcial — encontro objetivo (7), "en transito" en vez de "por recibir"; observo que "Detalle tecnico" muestra valores en ingles |
| 22 | Explicar pedido a otra persona | Cumple — explico: basado en almacen actual, lo que se recibira de proveedores y demanda de 28 dias |
| 23 | Vista "Sin necesidad de reponer" | Cumple — vio cantidad sugerida 0 en esos productos |
| 24 | Vista "Sin datos de inventario" | Cumple — vio ~300 productos sin datos |
| **F. Evaluacion de agosto** | | |
| 25 | Evaluacion > Reposicion simulada | Cumple — mensaje: "Esta pantalla es una evaluacion historica con inventario simulado, separada del flujo principal" |
| 26 | Ventas previstas (evaluacion) | Cumple — fechas agosto visibles |
| 27 | Evaluacion de resultados (agosto) | Cumple — WAPE 78.1% (promedio_28) vs 79.1% (RF), advertencias visibles, no se declara ganador |
| **G. Ayuda** | | |
| 28 | Abrir Ayuda | Cumple — primeros pasos, limites, WAPE, glosario |
| **H. Administrador** | | |
| 29 | Cargar datos (admin) | Cumple — pasos 1-2-3, "Subir y procesar", archivos listados |
| 30 | Reenviar archivo ya cargado | Cumple — "Sin cambios (archivo ya cargado). Este archivo ya estaba cargado; no se modifico ningun dato." |
| 31 | Abrir Crear analisis | Cumple — fecha "Ventas utilizadas hasta" 10/07/2026, periodo 21 dias (fijo), metodo promedio_28 (fijo), boton "Crear analisis". Milton lo presiono; se genero un analisis historico sin consecuencias |
| 32 | Estado del sistema y salir | Cumple — "Estado general: funcionando", "Base de datos: disponible", "Version: 0.1.0" |

## Observaciones del menu v2

El guion (T13_GUION_ACEPTACION.md) fue escrito para el entorno `df-demo` con la interfaz
anterior. El entorno `df-equipo` usa la interfaz v2 (plan operativo de noviembre) con
diferencias en el menu:

| Guion (df-demo) | Entorno equipo (v2) |
|---|---|
| Reposicion simulada (menu principal) | Mas > Evaluacion academica |
| Menu: Inicio, Ventas previstas, Reposicion simulada, Mis analisis | Menu: Inicio, Ventas previstas, Existencias, Compra recomendada, Mis analisis |
| Mas: Ventas registradas, Evaluacion de resultados, Datos cargados, Ayuda | Mas: Ventas registradas, Evaluacion de resultados, Evaluacion academica, Eval. academica: ventas previstas, Datos cargados, Ayuda |

Estas diferencias no son defectos del software; reflejan la evolucion de la interfaz
(v1 → v2). El guion deberia actualizarse para cubrir ambos entornos o indicar las
equivalencias.

## Cierre de la sesion

### Defectos encontrados

Ningun defecto critico. Observaciones menores:

1. **Paso 4 (menu):** El menu del entorno v2 difiere del guion. No es defecto del
   software; el guion fue escrito para otra version de la interfaz.
2. **Paso 5 ("barra de analisis y cifra"):** La expresion no fue clara para el
   ejecutor. Se sugiere reformular en el guion como "seccion Plan de compra vigente".
3. **Paso 14:** No hay analisis creado en la aplicacion en el entorno equipo — N/A.
4. **Paso 21:** La seccion "Detalle tecnico y valores exactos publicados" muestra
   nombres de campos en ingles. Observacion de usabilidad menor.

### Se pudo explicar WAPE, inventario simulado, tipos de analisis y un pedido?

- **WAPE:** Si — Milton entendio que no es porcentaje de acierto; es error acumulado
  equivalente al volumen vendido (paso 17).
- **Inventario simulado:** Si — explico correctamente los componentes: almacen actual,
  lo que viene de proveedores, demanda de 28 dias (paso 22).
- **Tipos de analisis:** Si — distinguio "En uso por defecto" vs "Seleccionado para
  consultar" (paso 10); entendio que la evaluacion no genera pedidos (paso 25).
- **Pedido/sugerencia:** Si — explico la formula y aclaro que es hipotetico (paso 22).

### Quedo resuelta la observacion "No comprendio el uso en su primera visita"?

**Parcial.** Milton completo el recorrido guiado (32 pasos) sin bloqueantes criticos.
Pudo explicar WAPE, inventario simulado y sugerencias de reposicion. Sin embargo,
este recorrido fue guiado por el asistente, no independiente. La observacion original
de Rogelio sigue abierta hasta que la pruebe con la interfaz nueva sin ayuda.

### Aceptacion humana

**COMPLETADA COMO PRE-ACEPTACION** por Milton (equipo de desarrollo), 2026-11-06.
La aceptacion formal (A14) por Rogelio/MYPE queda pendiente.

### Pendientes ajenos a este guion

- Validacion en nube (A13)
- Cinco usuarios concurrentes en nube (A13)
- Aceptacion formal de Rogelio con la interfaz nueva (A14)
- Rotacion de credencial Atlas (pospuesta por decision del titular)
