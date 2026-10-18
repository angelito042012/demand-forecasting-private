# Retomar sin repetir trabajo

Cierre del 17/10/2026. Lee CLAUDE.md, docs/ESTADO.md, docs/TRASPASO.md (instrucciones exactas para encender la demo), docs/PROTOCOLO_TRABAJO.md y docs/UX01R_REPORTE.md.

Estado: UX01 y UX01R entregados (rediseño comprensible; R17 cerrado; Evaluación simplificada); ultimo codigo f95092f. R12-R16 aceptados localmente: no repetir. No repetir T06/T07/T12 real, el registro de Microsoft.App ni el preflight de Azure (Microsoft.App Registered; ManagedEnvironmentCount Brazil South 0/1).

Pendiente y bloqueado por personas: (1) la prueba humana de comprension de Rogelio (observacion abierta: «No comprendio el uso en su primera visita»; guion en docs/T13_GUION_ACEPTACION.md; no completar por inferencia); (2) revision de Codex de UX01R; (3) autorizacion de publicacion en Azure: NO existe; no crear recursos, subir imagenes, transferir datos ni pedir accesos hasta recibir el mensaje explicito de autorizacion descrito en docs/T11_PLAN_DESPLIEGUE.md.

Servicios: la demo (compose df-demo) y df-mongo-dev estan DETENIDOS con todos sus volumenes, bases y credenciales conservados. Encender: docker start df-mongo-dev (si se necesita) y `.venv\Scripts\python.exe -m scripts.demo_local up` (sin --build), luego `... demo_local status`; URL https://localhost:8443; usuarios demo_lector / demo_admin con claves solo en artifacts/private/t13b/demo_credenciales.txt. Parar: `demo_local stop`. Nunca down -v ni limpiezas de Docker; no tocar contenedores ajenos ni v1/v2/pub.

Preservar originales, resultados congelados y puntero historico; inventario siempre simulado y rotulado. Agentes por ambitos y un integrador. Entrega final 23/10/2026 (America/Lima).
