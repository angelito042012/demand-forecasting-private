# Retomar sin repetir trabajo

Lee CLAUDE.md, AGENTS.md, docs/ESTADO.md, docs/TRASPASO.md y docs/T18_REPORTE.md. Etapa 18 entregada (18/10/2026, commit 464eb0c): inventario informado (conteo 18/10/2026 17:00, almacen 1, 50 productos) integrado en un ENTORNO DE ENSAYO aislado.

No repetir: R12-R17 (UX01/UX01R aceptados por Codex), T06/T07/T12, Azure (Microsoft.App Registered; ManagedEnvironmentCount Brazil South 0/1), ni la revision del conteo (docs/REVISION_CONTEO_50_20261018.md; usar artifacts/private/conteo_recibido_20261018_v2/; no regenerar la plantilla ni tocar el Excel recibido).

Entornos: demo anterior https://localhost:8443 (`demo_local up|status|stop`, imagen df-app:ux01r-f95092f) y ensayo https://localhost:8444 (`demo_local --env ens18 up|status|stop`, imagen df-app:t18-464eb0c, con Inventario informado). Credenciales solo en artifacts/private/t13b/*_credenciales.txt. Nunca down -v; no tocar contenedores ajenos ni v1/v2/pub.

Pendiente por personas: prueba humana de Rogelio (tres tareas de comprension + inventario informado; guion docs/T13_GUION_ACEPTACION.md; aceptacion pendiente, no completar por inferencia); revision de Codex de la etapa 18; ventas 01/10-corte del conteo (desconocidas, no cero); autorizacion de publicacion en Azure: NO existe.

Preservar originales, resultados congelados y puntero historico; el inventario simulado de T07/T12 sigue rotulado como simulado y el inventario informado NO se rotula simulado. Entrega final 23/10/2026 (America/Lima).
