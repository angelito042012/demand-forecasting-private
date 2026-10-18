# Revisión Codex13: T11B local aceptada, publicación pendiente

Fecha: 17/10/2026, America/Lima. Código revisado hasta e64bc03 (R12 acc9251; R13/R14 a7b7447). Durante la revisión Claude mantiene su operación independiente de autenticación/registro de Microsoft.App; `scripts/azure_register_app.py` estaba sin versionar. No se incorporó ese archivo ni se modificaron archivos productivos o de estado compartidos.

## Resultado

R12, R13 y R14 cerrados para el alcance local revisado. Esto no acredita conexión a Atlas, disponibilidad de cuota, publicación HTTPS, rendimiento de nube ni aceptación humana. La autorización humana vigente permite registrar únicamente Microsoft.App y consultar después; no autoriza otros registros, recursos facturables, despliegue ni transferencia de datos.

## Evidencia propia

- 67 pruebas aprobadas, 1 omitida, 0 fallos, 44,16 s: `tests/final/test_t12_estado.py`, `tests/ops/test_private_bundle.py`, `tests/publish/test_runtime_reference.py`, `tests/ops/test_t11b_generation.py`. Omisión: symlink real sin privilegios Windows; detección simulada sí ejecutada.
- Evidencia privada: `artifacts/private/codex_review13_tests.xml` y `.log`. Las pruebas Mongo usaron exclusivamente bases temporales de sus fixtures y su limpieza; no se cambió v1/v2/pub ni se leyeron secretos.
- R12: revisión del cierre bajo try/except, escritura atómica y manifiesto invalidado tras fallo; regresiones tardías y recuperación sin recalcular aprobadas.
- R13: revisión independiente del bundle real contra el hash externo de `recuperacion.json`: 43 archivos, 154159790 bytes, verificación sin problemas; hash del manifiesto Mongo coincide y árbol ya restaurado sin problemas. No se repitió el volcado/restauración grande; las restauraciones sintéticas sí forman parte de las pruebas propias. El respaldo ahora contiene físicamente los artefactos y distingue `mongo_ok`, `artefactos_ok` y `recuperacion_integral_ok`.
- R14: cadena de aprobación anclada en hashes versionados, no en un índice autoautorizado; pruebas sin Git y de alteración aprobadas. Referencia explícita inválida bloquea el trabajo. Configuración de montaje privado solo lectura y recursos coherentes con el contenedor.
- Evidencia de Claude revisada, sin repetir Docker: generación real 10/07 H21, 22,2 s, pico worker 406 MiB; RF coincide con T07, 582 pedidos/2655 unidades, 300 SKU sin snapshot; idempotencia, recuperación tras interrupción y puntero conservado. Sigue siendo una prueba local, no Azure/Atlas.

No se entrenaron modelos ni se repitió la evaluación real T12. Los resultados 440/5 y Docker/E2E de la entrega permanecen atribuidos a Claude, separados de las pruebas propias.

## Límites y mantenimiento no bloqueante

- Detener escritores sigue siendo requisito del respaldo; hashes y `currentOp` no sustituyen una ventana real de mantenimiento. Atlas puede restringir `currentOp` y debe registrarse esa limitación.
- El bundle excluye modelos T07 (47 MB), que continúan conservados en el equipo. Sí contiene el modelo T12 y las referencias necesarias para consultar/reproducir la demostración sin entrenar. No presentarlo como archivo íntegro de todos los experimentos.
- `verify_tree` comprueba el enlace de la hoja, pero no todos los ancestros de un árbol recibido. El bundle propio actual se verificó normal. Antes de aceptar respaldos externos/no confiables, rechazar también symlinks/junctions de directorios intermedios; no hay evidencia de escape de escritura de destino. No bloquea el respaldo propio probado ni exige repetirlo.
- Costos propuestos no son presupuesto aprobado. Cuota 0/0 antes del registro no es prueba de indisponibilidad permanente: verificar después del registro; si persiste, preparar solicitud de cuota o alternativa antes de comprometer gasto.
- Los archivos de estado contienen antecedentes contradictorios (R11 pendiente, Azure sin autenticar, encargo antiguo). Claude debe consolidarlos con la entrega vigente; conservar los antecedentes en HISTORIAL, sin repetir tareas cerradas.

## Siguiente entrega

`ETAPA_13_CLAUDE.md`: terminar el registro/consulta ya autorizado; avanzar T13A local y borradores T14 sin depender de recursos externos; entregar un paquete pequeño de evidencia y la decisión de nube. Publicación real requiere recursos/costo/alcance aprobados, acceso seguro a Atlas y pruebas posteriores en nube. Mantener 23/10/2026 como fecha límite hasta cambio explícito del usuario.

### Actualización posterior a b64c3ff

Codex leyó `artifacts/private/t11b/azure_microsoft_app.json`: proveedor ya Registered al comenzar, registro omitido, ManagedEnvironmentCount Brazil South uso 0/límite 1 y sesión cerrada/caché borrada. Se resuelve el riesgo concreto de cantidad de entornos para el plan de un entorno; no prueba todas las cuotas ni la ejecución real de la plataforma. No repetir autenticación/registro ni consultar otras regiones por rutina. La causa del 0/0 previo no queda demostrada por este JSON. Sigue sin autorización la creación de recursos/otros registros/gasto/transferencia de datos. ETAPA_13 actualizada para pasar directamente a T13A, documentación y preparación del plan facturable.
