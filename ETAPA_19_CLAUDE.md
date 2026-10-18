# Etapa 19 — prever noviembre y calcular una compra para cubrir el mes

Encargo de Codex, 18/10/2026, America/Lima. Rogelio autoriza como prioridad número uno conectar las fuentes recientes, la previsión futura, el inventario recibido y una cifra de compra por escenario. Eligió expresamente **una propuesta de compra para cubrir todo noviembre**, no un calendario de pedidos semanales. Claude sigue como ejecutor principal; Codex revisa. No se ha implementado esta etapa al crear este documento.

## Resultado que debe poder usar Rogelio

En la aplicación local: abrir «Planificar compras», elegir noviembre de 2026, consultar para los 50 productos las ventas previstas del mes, el stock reportado del 18/10 y su evolución proyectada, y obtener una cantidad de compra en la presentación del producto bajo escenarios de entrega de 7 y 14 días. Poder abrir «Entender la compra» y reconstruir la cifra. Una compra significa una única orden por producto en la fecha de decisión del escenario; no se ejecutan pedidos reales. No hay que esperar datos que la empresa no tiene: los desconocidos se cubren con supuestos identificados, sin convertirlos en hechos.

Leer AGENTS/CLAUDE/PROTOCOLO/ESTADO/TRASPASO/DECISIONES y cierres de REVISION_CODEX_18. El mensaje humano y este encargo posterior autorizan la integración y planificación descritas, superando la espera de integración anterior. No eliminan restricciones de originales, aislamiento, congelación y nube.

## 1. Verificar y conectar el paquete preparado

- Verificar Git/procesos antes de editar; no sobrescribir trabajo ajeno. Reutilizar componentes útiles. El árbol estaba limpio al preparar el encargo.
- Fuente: `artifacts/private/datos_preparados_v1/`: manifest/verification, `00_originales/`, CSV de `01_normalizados/` y catálogo de `02_grupo/productos.csv`. Son siete ventas y siete compras marzo–septiembre, 106.525 registros clasificados. No usar el importador antiguo sin adaptar un contrato separado.
- Implementar importación local del paquete completo, idempotente, versionada y trazable, a colecciones separadas del dataset histórico. Acreditar correspondencia del contenido derivado con las fuentes aprobadas: no basta con que un CSV declare el SHA del Excel. Reutilizar normalizador/verificaciones existentes para contrastar contenido y sellar un manifiesto verificable antes de cargar. Detectar manipulación de cantidades coherente con un total manipulado.
- Conservar ventas, compras, créditos y cuarentenas separados. 101.080 ventas, 3.555 compras positivas, 1.224 compras sin cargo registrado, 664 créditos, 2 cuarentenas. Mantener las seis copias de compra marcadas y las monedas separadas; no deducir devoluciones físicas de créditos. No inventar cambio PEN/USD ni precio en compras de importe cero.
- Importar las 14 fuentes para trazabilidad/consulta del nuevo módulo; las ventas son la entrada del pronóstico. Las compras permiten consultar entradas documentadas y cobertura histórica; no se presentan como predictor ML incorporado si no lo son ni reconstruyen automáticamente un stock real. No sumar compras históricas al conteo de octubre (doble conteo).
- Primera planificación limitada a los 50 productos del grupo con conteo. Otros productos quedan consultables en el dataset, sin compra calculada por ausencia de stock comparable. Productos/categorías por código y corte; no unir por nombres ni multiplicar caja/pack por el texto de presentación. Verificar compatibilidad de UND entre ventas y conteo; rechazar productos incompatibles en vez de inferir equivalencias.

## 2. Modo de planificación separado del modo histórico

- No quitar globalmente el límite T10 ni modificar `config/seleccion_congelada.*`, barreras de T06/T07/T12, resultados o punteros históricos. Añadir contrato y acceso a datos propios para planificación posterior, con filtros por fecha y fuente aprobada. Agosto/septiembre pueden alimentar esta nueva previsión posterior a su disponibilidad; eso no reescribe la evaluación final anterior.
- Mantener `promedio_28` como método inicial: por producto/almacén, media exacta de ventas brutas en los últimos 28 días naturales de historia cubierta hasta el corte de ventas (actualmente 30/09). Respetar máscara y calendario; cero solo donde hay cobertura completa y ausencia de ventas del producto, nunca para octubre desconocido. Catálogo al corte. RF no se reentrena ni se vuelve a seleccionar.
- Pronóstico diario y agregado mensual para **01–30/11/2026**, más proyección de los días intermedios que precise el inventario y de la reserva posterior al mes. El salto desde 30/09 hasta noviembre debe representarse explícitamente: no desplazar fechas, comprimir el calendario ni tratar octubre como ventas observadas. Sin ventas reales futuras en los cálculos.
- Añadir un horizonte acotado apropiado (por ejemplo hasta 120 días desde la última venta conocida) y validar las fechas en servidor; no dejar cálculos de duración ilimitada. Mostrar fecha de ventas, fecha de conteo, fecha de decisión, período objetivo y distancia de extrapolación. Noviembre completo requiere 30 días; desde septiembre hay además un intervalo sin observaciones. No afirmar validación de noviembre antes de que existan sus ventas.
- Futuras ventas de octubre: permitir una nueva versión del dataset con el mismo contrato cuando se reciban, sin inventarlas ni hacer su recepción requisito para el escenario inicial. No construir en esta etapa un importador genérico de cualquier ERP.

## 3. Inventario fechado, consumo previo y supuestos

- Inventario inicial: snapshot T18 revisado del **18/10/2026 17:00 Lima**, almacén 1, 50 productos. Persistir referencias y huellas; nunca modificarlo al simular. No usar `saldos_calculados.csv`, `balance_diario.csv` ni el mínimo inicial retrospectivo como inventario predictivo.
- Fecha de decisión inicial: 18/10/2026, vinculada al conteo, visible y editable dentro de límites coherentes. Si es posterior, proyectar desde el conteo hasta esa fecha. No usar este conteo para una compra al 01/10 o al 30/09; sería información futura.
- Proyectar el consumo **después del conteo y antes de noviembre**, además del de noviembre. El stock del 18/10 no equivale al stock del 01/11. Proyección diaria, saldo no negativo, faltantes separados; no cambiar una venta perdida en pedido atrasado sin declarar otra política.
- Convención intradiaria: como el conteo es a las 17:00, el escenario inicial puede empezar el 19/10 suponiendo que no hay movimientos adicionales tras el conteo el 18/10. Registrar y mostrar ese supuesto; no atribuirlo a una confirmación empresarial. Recepciones al inicio del día y consumo después, con plazos en días naturales y convención explícita.
- Pedidos por recibir: fuente desconocida. Proponer de forma visible el supuesto «en este escenario, no llegan otros pedidos», valor 0 **asumido**, jamás «cero informado por empresa». Hacer visible y editable la hipótesis antes de generar. Si se admiten pedidos manuales, exigir producto, unidades, fecha de llegada y naturaleza reportada/asumida; no usar cantidad sin fecha para cubrir demanda anterior a la recepción. No pedir información empresarial como bloqueo.
- Parámetros iniciales: plazos de entrega **7 y 14 días naturales**; reserva **7 días de ventas previstas**; sin movimientos extraordinarios no informados; faltantes como ventas no atendidas, sin arrastrarlas como demanda futura; mínimo y múltiplo de compra **1 unidad de reporte**. Todos supuestos editables/identificados salvo evidencia. No inferir plazos de facturas sin fecha de pedido. No presentar reserva como garantía estadística de servicio.

## 4. Cifra de compra para cubrir noviembre y efecto del plazo

Una única orden emitida en la fecha de decisión, recibida tras el plazo supuesto; cubrir hasta el cierre del 30/11 y la reserva elegida. Si llega en octubre, parte puede consumirse antes de noviembre: distinguir unidades para el puente de octubre, noviembre y reserva. Si llega después del comienzo de noviembre, mostrar demanda anterior a llegada y faltantes proyectados; no prometer cobertura total del mes.

Antes de recibir la orden nueva, simular el stock/otras llegadas con la demanda prevista: guardar stock remanente y ventas no atendidas. La compra nueva no repone automáticamente las ventas ya perdidas antes de su llegada. Después de llegar, calcular la menor cantidad entera compatible con cobertura y reserva bajo los supuestos, respetando mínimos/múltiplos. Usar aritmética exacta para cantidades y redondear el pedido al final, no cada previsión diaria.

Sin otros pedidos, una vez fijada la fecha de recepción A y el stock inmediatamente anterior S, la explicación básica es:

`compra = redondear_a_multiplo(max(0, ventas_previstas_desde_A_hasta_30_11 + reserva_final - S))`.

Si hay otras recepciones, considerar sus fechas: una recepción posterior no cubre faltantes anteriores. La cantidad debe satisfacer cada prefijo del período desde A hasta 30/11 y la reserva al cierre, o declarar explícitamente la cobertura que no puede alcanzar. Probar esta condición con un ejemplo de recepción tardía. No descontar de nuevo el stock inicial después de haberlo consumido en el puente.

Fijar una convención única para las recepciones el mismo día A: S incluye las otras entradas de ese día si ya fueron aplicadas; en ese caso no volver a descontarlas como recepciones futuras. La demanda del día A se atiende después de todas sus recepciones. Persistir el orden de eventos para reproducirlo.

**No forzar que 7 y 14 días den compras distintas ni que la compra con 14 días sea siempre mayor.** El plazo cambia la llegada, el consumo antes/después de ella y los faltantes. Mostrar cantidad, recepción, cobertura y demanda no atendida para cada escenario. Una compra menor con peor servicio no se describe como ahorro o mejora.

Si la llegada es posterior al 30/11, no presentar una orden que llega en diciembre como solución de noviembre; devolver estado explicable «no llega para cubrir noviembre» con la fecha requerida. Si no hace falta comprar, mostrar 0 calculado con explicación. Sin señal o unidad compatible, «no calculable», no 0.

## 5. Pantalla y ejecución

- «Planificar compras», con mes, fecha de decisión, fuente de ventas, conteo y supuestos. Lector consulta resultados; administrador genera/cambia escenarios con controles de sesión/CSRF existentes. Cálculo fuera de la petición HTTP si corresponde, aprovechando la cola; no reentrenar al navegar.
- Mostrar 50 productos (ceros incluidos), nombre/presentación, ventas previstas de noviembre, stock del conteo con fecha, stock proyectado al inicio del mes, compra única propuesta, fecha de llegada, saldo final y faltantes del escenario; comparar 7/14 días sin abrumar la vista inicial. Desglose «Entender la compra» con números que reproducen la cantidad.
- Separar «ventas previstas sin limitar por stock» y «ventas que podrían atenderse en el escenario». Compras e inventario no sustituyen las ventas como objetivo predictivo. Indicar que la previsión estima ventas observadas históricas, que pueden haber estado limitadas por disponibilidad.
- Procedencia por campo: ventas reales hasta 30/09, conteo reportado 18/10, proyección posterior, parámetros supuestos. Etiqueta global: «Plan de compra bajo supuestos», sin llamar simulado al conteo real. No convertir los escenarios en una mejora comprobada ni en un pedido ejecutado.
- No sumar cantidades de cajas, packs y frascos en un total general de artículos sueltos. No mostrar valor monetario de compra si no se ha definido un costo compatible, fechado y con moneda. El objetivo inicial es una cifra de unidades por producto.
- Identidad del cálculo: versión/huella dataset, corte de ventas, snapshot, mes, fecha decisión, escenarios/supuestos, método y código. Reintento idempotente, versión nueva si cambian entradas, resultados incompletos invisibles, fallo conserva último resultado válido. Persistir separado de T12 y recomendaciones históricas.
- Preferir nuevo entorno de ensayo **ens19, puerto 8445**, base/imagen/estado propios, aprovechando parametrización de demo_local. Conservar demo 8443 y ensayo T18 8444, volúmenes, usuarios y punteros. No cambiar servicios ajenos. Si el equipo no permite tres entornos simultáneos, documentar limitación y conservar los anteriores sin borrarlos.

## 6. Validación dirigida y evidencia exigida

Antes de implementar, escribir un contrato breve de dataset, fechas/eventos, fórmula, persistencia/API y ejemplos calculados a mano. Es parte del encargo, no otra ronda de aprobación rutinaria. Implementar y entregar el incremento completo; no detenerse solo en el plan.

Pruebas necesarias:

1. Integridad de las 14 fuentes/derivados, partición exhaustiva y repetición sin duplicar; compras sin cargo, créditos, monedas, copias y cuarentenas conservados.
2. Corte de datos y fechas: datos posteriores no cambian un plan anterior; octubre ausente no se transforma en cero; noviembre tiene sus 30 fechas; conteo de octubre nunca entra en una decisión anterior; última ventana válida y distancia al objetivo explícitas.
3. Escenarios calculados a mano: stock suficiente/insuficiente, consumo previo al mes, recepción 7/14, llegada tardía, pendiente con fecha, reserva, cero y no calculable, múltiplo, caja/pack, no arrastrar pérdidas anteriores como pedidos atrasados. Un balance diario con conservación y faltantes separados, sin redondeos diarios que inflen demanda/pedido.
4. Idempotencia, recuperación, permisos, aislamiento y comparación de huellas de colecciones/punteros protegidos antes/después. Pruebas de componentes comunes que efectivamente cambien.
5. Comprobación **descriptiva nueva** de previsión mensual y del salto al mes objetivo, sin selección de modelos ni reejecución T12: media al 31/08 → septiembre (30 días), y media al 31/07 → septiembre (separación de 61 días; no usar agosto como entrada de ese cálculo). Reales de septiembre solo para evaluar, nunca features del origen. Cohorte/catálogo conocidos al corte. Septiembre ya fue inspeccionado: no llamarlo prueba final independiente ni validación de noviembre. No usar el conteo de octubre en estas comprobaciones ni atribuirles mejora de inventarios. Reportar error, sesgo, ceros/cobertura y limitaciones; no imponer metas inventadas.
6. Recorrido corto en imagen de producción de ens19: administrador genera, lector consulta los escenarios, detalles coherentes, errores comprensibles. No repetir suite completa, modelos, benchmarks ni recorridos antiguos por rutina.

Evidencia comercial y logs extensos solo en `artifacts/private/t19/`, ignorados por Git; documentos y código sin secretos. Entregar contrato, reporte, commits, pruebas efectivamente ejecutadas, URL/imagen/base/usuarios (claves solo en archivo privado), cómo reproducir y detener sin perder datos. Actualizar ESTADO/TRASPASO/BACKLOG/HISTORIAL y manual/ayuda afectados. Aceptación humana solo con respuestas reales posteriores de Rogelio.

## Límites finales

No Azure/Atlas, recursos facturables, transferencias, compras reales ni cambios en sistemas de la empresa. No pedir datos ausentes como condición para empezar: emitir escenarios con hipótesis visibles. Si noviembre usa ventas hasta septiembre, llamarlo planificación con información desactualizada y supuestos, no pronóstico actualizado al 18/10. No fingir que hoy es septiembre ni usar inventario futuro para planificar octubre. El objetivo prioritario es noviembre completo. No afirmar que esta etapa esté terminada por estar redactado el encargo.
