# Instrucciones para Claude Code

Sistema de prevision de demanda y compras. Angular + FastAPI + Python + MongoDB.

## Stack y convenciones

- Python 3.12, PyMongo, FastAPI, scikit-learn, XGBoost
- Angular (frontend), Caddy (proxy), Docker Compose
- Zona horaria: America/Lima
- Fijar versiones en `requirements.lock.txt` y `package-lock.json`

## Estructura

- `backend/` — API y logica de negocio
- `frontend/` — Aplicacion Angular
- `pipeline/` — Pipeline de datos y ML
- `scripts/` — Utilidades (demo_local, build, etc.)
- `tests/` — Pruebas (backend, jobs, plan, publish, inventory)
- `deploy/` — Docker, Caddy, entrypoint
- `infra/` — Templates Azure (referencia)
- `config/` — Configuracion de modelos y experimentos
- `docs/` — Documentacion tecnica

## Reglas de desarrollo

Leer `docs/ESTADO.md` y `docs/BACKLOG.md` al retomar. Existe una implementacion funcional aceptada; la actualizacion operativa y la evaluacion academica estan pendientes.

### Seguridad
- No exponer credenciales en repositorio, logs ni prompts
- No imprimir `.env` ni tokens
- No desplegar a Azure/Atlas sin autorizacion y presupuesto
- No ejecutar compras reales ni modificar sistemas de la empresa

### Datos
- Datos sinteticos autorizados para desarrollo, siempre etiquetados
- Nunca presentar datos sinteticos como evidencia real
- No repetir T12 ni reentrenar contra agosto
- TIPO_DOC=7 son notas de credito; separar de ventas brutas
- Excluir del entrenamiento: 03/04, 12/04 y 07/06 de 2026
- Catalogo por fecha de corte segun `docs/DECISIONES_DATOS.md`

### Ciencia
- Particion temporal; ultimo mes reservado para evaluacion
- Transformaciones ajustadas en train
- Rezagos anteriores al corte; no usar ventas futuras
- Reportar MAPE con cobertura; R² indefinido
- La venta observada puede estar censurada por stock

### Proceso
- Cada entrega actualiza `docs/ESTADO.md`
- Cambios pequenos, revisar diff, resolver defectos antes de ampliar
- No inventar resultados, mejoras ni aceptaciones
- Separar hechos, propuestas, supuestos y bloqueos

## Subagentes

Definidos en `.claude/agents/`: data-engineer, forecasting, backend-inventory, frontend, quality-reviewer. Maximo tres simultaneos para tareas independientes. Un unico integrador cambia contratos, dependencias y configuracion comun.

## Skills

Definidos en `.claude/skills/`: data-quality, inventory-backtest, release-evidence, temporal-forecasting.
