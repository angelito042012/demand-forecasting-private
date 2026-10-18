# Traspaso vigente

- Ejecutor: Claude Code, 18/10/2026. **Etapa 13 entregada para revisión de Codex** (ETAPA_13_CLAUDE.md). Reportes: `docs/T13A_REPORTE.md` (rendimiento/uso/accesibilidad local), `docs/T11_PLAN_DESPLIEGUE.md` (plan de publicación con acciones que requieren aprobación), `docs/T11B_REPORTE.md` (R12–R14, aceptados localmente por Codex).
- Hecho: T13A local (p95 ≤ 373 ms con 5 sesiones, Chrome 22/22 sobre la imagen de producción, defecto de CSS de producción corregido); borradores T14A: `docs/MATRIZ_CIERRE.md`, `docs/INFORME_FINAL_BORRADOR.md`, `docs/MANUAL_USUARIO.md`, `docs/MANUAL_OPERACION.md`, `docs/GUION_VIDEO.md`, `docs/T13_GUION_ACEPTACION.md` (aceptación humana: PENDIENTE; sin firmas ni cifras nuevas).
- Azure: `Microsoft.App` Registered; `ManagedEnvironmentCount` Brazil South 0/1; sesión cerrada y caché borrada. No repetir acceso/registro/consultas.
- NO hecho (a propósito, sin autorización): registrar otros proveedores, crear grupos/recursos/roles, subir imágenes, transferir datos, consumir crédito, conectar Atlas, desplegar. Sin HTTPS externo; A13 y A14 pendientes.
- Decisión que necesita el usuario: aprobar (o no) cada acción numerada del plan (crédito máximo propuesto US$ 20 hasta el 23/10; parada > US$ 12; la imagen a subir debe construirse desde el commit con la corrección de estilos); entregar por canal privado el usuario Atlas mínimo y la credencial rotada; ejecutar el guion de aceptación.
- Estado de datos: v1/v2 y `demand_forecasting_pub` intactas; paquete T12 sellado intacto; histórica auditada activa. Stack de ensayo `df-t13a` eliminado (volúmenes, credenciales de ensayo). Sin procesos propios en ejecución.
- Si se interrumpe: `git status`, leer `docs/ESTADO.md` y `docs/T13A_REPORTE.md`.
