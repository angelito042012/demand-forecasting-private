# Traspaso vigente

- Ejecutor: Claude Code, 17/10/2026. **Etapa 14 (T13B) entregada para revisión de Codex** (ETAPA_14_CLAUDE.md). Reportes: `docs/T13B_REPORTE.md` (R15/R16, demostración, paquete de publicación), `docs/T13A_REPORTE.md` (ensayo local, corregido por R15), `docs/T11_PLAN_DESPLIEGUE.md` («Paquete de publicación para una única autorización»). R12–R14 aceptados localmente por Codex.
- **Demostración local ACTIVA:** `https://localhost:8443` (solo 127.0.0.1), proyecto compose `df-demo` (mongo, api, worker, proxy), base `df_demo_20261017221940` restaurada del respaldo T11A; usuarios `demo_admin`/`demo_lector` con contraseñas generadas en `artifacts/private/t13b/demo_credenciales.txt` (privado). Comprobar: `.venv\Scripts\python.exe -m scripts.demo_local status`. Parada segura: `... demo_local stop` (conserva volúmenes); no usar `down -v`; no detener `df-mongo-dev` ni otros contenedores.
- Azure: `Microsoft.App` Registered, `ManagedEnvironmentCount` Brazil South 0/1; sesiones cerradas. No repetir acceso/registro/consultas.
- NO hecho (sin autorización): registrar otros proveedores, crear grupos/recursos/roles, subir imágenes, transferir datos, consumir crédito, conectar Atlas, desplegar. A13 y A14 pendientes; informe, manual y video son borradores.
- Decisión del usuario: ejecutar el guion de aceptación (`docs/T13_GUION_ACEPTACION.md`); decidir si emite el mensaje único de autorización de nube (alcance, US$ 20, intervención a US$ 12) y la política posterior al 23/10.
- Estado de datos: v1/v2 y `demand_forecasting_pub` intactas; paquete T12 sellado intacto; histórica auditada activa. El stack de ensayo `df-t13a` fue eliminado; `df-demo` permanece.
- Si se interrumpe: `git status`, leer `docs/ESTADO.md` y `docs/T13B_REPORTE.md`; `demo_local status`.
