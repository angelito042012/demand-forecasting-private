# Guía rápida — lector y administrador (versión entregada, 23/10/2026)

**Dirección:** https://dfpub-api.ashyglacier-9e3e37bc.brazilsouth.azurecontainerapps.io · Navegador de escritorio al 100 % de zoom. Usuarios: `pub_lector` (lector) y `pub_admin` (administrador); las contraseñas se entregan por canal privado (nunca en documentos ni por chat). Si la sesión caduca, vuelve a ingresar.

## Lector (consulta)
| Pantalla (menú) | Para qué sirve | Pasos | Resultado esperado |
|---|---|---|---|
| **Inicio** | Resumen del plan de noviembre vigente | Abre Inicio | «Plan de compra vigente»: **Versión 2**, decisión 21/10/2026, plazos 7 y 14 días; ventas hasta el 20 de octubre; existencia reconstruida al cierre del 20/10; **19 de 50** productos con compra recomendada en cada plazo |
| **Ventas previstas** | Cuántas unidades se estima vender por producto en noviembre | Busca por código o nombre; abre «Cómo leer la tabla» | Venta prevista del mes y por día, ventana de 28 días (23/09–20/10), existencias; 3110044 → 18.214 en el mes, 0.607 por día |
| **Existencias** | Existencia al cierre del 20/10 y su procedencia | Marca «Solo productos con diferencia»; abre «2 pendientes… Ver detalle» | 50 productos; 13 con «Diferencia» (sistema vs reconstrucción, pendiente de confirmar); pendientes: compras 11452/11455 y diferencias |
| **Compra recomendada** | Cuántas unidades comprar, cuándo llega y qué falta | Mira «Plazo de 7 días» y «14 días»: Llegada, Stock al 1/11, Comprar, Faltantes; filtra por estado (Cubre / Llega tarde) | 10 productos «Llega tarde» a 14 días; cada fila trae «Entender la compra» |
| **Entender la compra** | Explicar una compra | Pulsa el botón de un producto; despliega «Ver cálculo detallado» | Compra, llegada, ventas atendibles y faltantes por plazo; una frase de cálculo; 14 pasos en el detalle; nota si el plazo largo compra menos porque vende menos |
| **Compra recomendada → Comparar con otra versión** | Ver v1 (18/10) frente a v2 (21/10) | Abre el desplegable y pulsa «Comparar con otra versión» | Tabla A → B por producto con la nota de que las existencias son de fechas distintas |
| **Mis análisis / Más → Evaluación académica** | Análisis histórico (marzo–julio, agosto prueba final) con **inventario simulado con supuestos** | Entra desde Más | Datos históricos, siempre rotulados; no es el plan operativo |
| **Ayuda** | Primeros pasos, límites, glosario, «Cómo se actualiza el plan de noviembre» | Abre Ayuda | Explica lo que no hace la aplicación |
**El lector no** ve «Cargar datos», «Crear análisis» ni el formulario «Generar plan».

## Administrador (además de lo anterior)
| Pantalla | Qué hace | Pasos | Resultado esperado |
|---|---|---|---|
| **Compra recomendada → Generar plan** | Crea una versión del plan con parámetros (decisión, plazos, reserva, mínimo, múltiplo, pedidos por recibir) | Baja al formulario; **sin cambiar nada** pulsa «Generar plan» | Aviso verde «Ya existía un plan con exactamente estos datos: se reutilizó y no se calculó de nuevo»; la versión 2 sigue vigente, no aparece una versión 3 |
| **Cargar datos** | Sube ventas mensuales del **análisis histórico** (solo marzo–julio 2026; agosto reservado) | Elige un `.xlsx` y «Subir y procesar» | Para un archivo ya cargado (p. ej. `marzo.xlsx`): «Sin cambios (archivo ya cargado)». **No actualiza el plan de noviembre** |
| **Crear análisis** | Crea un análisis **histórico** (cortes 01/06–10/07, 21 días, promedio de 28 días) | Elige fecha y «Crear análisis» | Un análisis en «Mis análisis»; no es el plan operativo |
| **Estado del sistema** | Comprueba servicio y base de datos | Abre la pantalla | «funcionando» y «Base de datos: disponible» |

## Lo que la aplicación NO hace
No compra ni envía pedidos; no incorpora ventas o existencias posteriores al 20/10 (eso requiere un procedimiento técnico: ver `docs/T22_ALCANCE_DATOS_Y_PLAN.md`); no demuestra ahorro; no hace pronósticos de ventas de «hoy» (lo posterior al corte es desconocido, no cero).

## Si algo falla
- Pantalla en blanco o «Base de datos: no disponible»: espera 1–2 minutos y recarga (la API se reinicia al actualizarse); si sigue, avisa al soporte técnico (ver `docs/MANUAL_OPERACION.md` §9).
- «Demasiados intentos»: espera 15 minutos antes de reintentar el inicio de sesión.
