# Traspaso vigente

- Ejecutor: Claude Code, 17/10/2026. Tarea en curso: T08 + integración de lectura T09 (ETAPA_06_CLAUDE.md). T07 aceptado (5790103).
- Hecho y comprometido: ajustes del motor (d59703b), contrato `docs/T08_CONTRATO.md`, selección congelada `docs/SELECCION_CONGELADA.md` + `config/seleccion_congelada.json` (c49160c; sin ejecutar, sin agosto).
- En curso: tres agentes con archivos separados (auth/backend, persistencia+rutas de datos, frontend). Un único integrador (yo) controla main.py, config, lockfiles. Después: integrar, publicar la corrida real en demand_forecasting_v2 por CLI, E2E en navegador (Playwright-core con Chrome del sistema en `artifacts/private/t08/e2e`, fuera de Git), pruebas y reporte T08.
- Base activa: demand_forecasting_v2. Agosto no consultado. Procesos propios: ninguno persistente todavía.
- Si la sesión se interrumpe: revisar `git status` (archivos de los agentes sin commitear), ejecutar las pruebas de cada ámbito y continuar la integración.
