# Remediación no destructiva de fuentes fallidas o de reemplazo

Situación: `SourceApprovalError` por `CARGA_NO_COMPLETADA`, `MES_CON_VARIAS_FUENTES`, `PERSISTENCIA_INCOMPLETA` o `CONFLICTO_ABIERTO`, típicamente tras cargar un archivo de reemplazo que falla o difiere del canónico. No existe un mecanismo fiable de resolución automática ni se desarrolla una interfaz de conflictos en esta etapa.

1. **Identificar**: ejecutar `evaluate_sources(db, corte)`; cada incidencia trae mes, archivo, sha256 y detalle. Contrastar con `db.imports` y `db.import_conflicts` (solo lectura). No editar ni borrar estados `failed`, conflictos u otras importaciones para hacer pasar el control.
2. **Contener**: dejar de usar esa base para entrenamiento; las rutas `load_*` ya se detienen.
3. **Reconstruir en una base nueva** (por ejemplo `demand_forecasting_v3`) con `python -m pipeline.data.importer --source <carpeta con los archivos canónicos> --db <nueva>`, usando solo los archivos aprobados (un archivo por mes) cuyos sha256 coinciden con `docs/T04_FIRMA.json`.
4. **Verificar** con `scripts/compare_v1_v2.py --v1 demand_forecasting_v2 --v2 <nueva>`: conteos, importes y líneas normalizadas iguales; 0 conflictos y 0 rechazos; después `scripts/build_t04.py --db <nueva>` y comparar hashes de contenido con la firma vigente.
5. **Cambiar** `mongodb_database` localmente solo si todo coincide; conservar la base anterior para auditoría. El borrado de bases antiguas queda fuera de cualquier encargo salvo petición explícita.
6. Si el archivo nuevo es un reemplazo legítimo, registrar la decisión (qué fuente queda activa y por qué) antes de reconstruir; el sistema admite una sola fuente aprobada por mes.

## Reserva de mes parcial (T10R)

Si una importación web falló después de escribir filas, `month_reservations` conserva el mes en estado `partial` para esa fuente y rechaza cualquier otra: no se libera como si estuviera vacío. La misma fuente puede reintentar (idempotente). Si se decide abandonar esa fuente, no se borran ventas: se reconstruye en una base nueva (pasos anteriores). La liberación privilegiada de la reserva (`pipeline.data.month_lock.release_month`) solo desbloquea el mes y debe registrarse con su motivo; no está expuesta en la API.
