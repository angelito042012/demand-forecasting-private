# Traspaso entre ejecutores

## Registro actual

- Ejecutor: Claude Code (Sonnet 5.5). Fecha: 17/10/2026, America/Lima. Tarea: ETAPA_02_CLAUDE.md (R04, base v2, T04).
- Punto de retoma encontrado: sin trabajador anterior activo; Mongo (df-mongo-dev) arriba; solo existía `demand_forecasting_dev` (v1: 86 877 ventas, 560 créditos); v2, R04 y T04 no existían en código ni datos; Git sin commits.
- Último paso terminado: R04 + v2 + T04 implementados, probados y comprometidos. Suite completa con `RUN_REALDATA=1`: 65 aprobadas, 0 omitidas, 1 aviso, 69 s. `ruff` limpio (backend, pipeline, tests, scripts/build_t04.py, scripts/compare_v1_v2.py).
- Paso en curso: ninguno de escritura. Revisión de solo lectura por quality-reviewer hecha; M1 (persistencia declarada vs real), M2 (una fuente por mes), M3 (día sin filas = SIN_REGISTROS_DIA, no cero) y M5 (texto del perfil) corregidos con pruebas. Quedan sin tratar, menores: catálogo ignora start, catálogo no excluye la máscara, unidad_base fuera del fingerprint, céntimos por truncado (importes con ≤2 decimales no verificado), bloqueo permanente sin ruta de remediación tras carga fallida de archivo reemplazado.
- Checkpoints Git locales: 8a34814 (estado recuperado, parcial), 425d663 (R04 + comparador + config v2), 05510d1 (T04). Un commit final de documentación sigue a este registro.
- Base activa: `demand_forecasting_v2` (config por defecto en `backend/app/config.py` y `.env.example`; el `.env` local no se leyó ni se imprimió: la configuración efectiva resuelta es v2). v1 conservada intacta.
- Revertir a v1: en `backend/app/config.py` (y `.env.example`) volver `mongodb_database` a `demand_forecasting_dev`, o fijar `MONGODB_DATABASE=demand_forecasting_dev` en el entorno. Nota: v1 tiene claves de esquema 1 y no pasa `check_schema` del importador ni la aprobación de fuentes (no tiene `sources`); sirve solo para consulta/comparación.
- Procesos: sin servidores propios en segundo plano. df-mongo-dev se dejó activo. No se tocaron otros contenedores.
- Evidencia (no versionada con datos comerciales): `artifacts/private/compare_v1_v2.json` (comparación y recarga), `artifacts/private/load_v2.log`, `artifacts/private/t04/` (series). Versionada: `docs/T04_*`.
- Bloqueos: ninguno de datos. Angular: `npm ping` al registro hoy responde (661 ms); no se intentó instalar; TLS sin tocar.
- Pendiente de revisión de Codex: R04 (`pipeline/data/sources.py`, `training_access.py`, `catalog.py`), v2 (comparación y configuración), T04 (`pipeline/data/daily_series.py`, `scripts/build_t04.py`, perfil/diccionario/firma).
- Siguiente acción exacta: tras la revisión de Codex, emitir el encargo T05 (baselines, folds sin fuga). No entrenar ni usar agosto antes.

## Reproducir

```
.venv\Scripts\python.exe -m scripts.compare_v1_v2 --reload C:\Users\rogel\Documents\Datos --out artifacts\private\compare_v1_v2.json
.venv\Scripts\python.exe -m scripts.build_t04
$env:RUN_REALDATA="1"; .venv\Scripts\python.exe -m pytest -q
```

## Actualización obligatoria durante el trabajo

Reemplazar el registro actual con hechos comprobados al cambiar de etapa o ejecutor. Conservar detalles anteriores relevantes en HISTORIAL_ENTREGAS.md.

Campos mínimos: ejecutor; fecha; tarea; último paso terminado; paso en curso; archivos; commit/checkpoint; comandos y resultado; evidencia; base activa; procesos útiles; bloqueos; siguiente acción exacta; pendiente de revisión.

No escribir claves, tokens o URI con credenciales. Si una prueba no se ejecutó o un proceso dejó de ser observable, indicarlo.
