# Traspaso vigente

Cierre de jornada: 17/10/2026 (America/Lima). Ejecutor: Claude Code. Último commit de código `f95092f` (UX01R); documentación `b3c19f1` (más el commit de este cierre). Árbol de Git limpio al cerrar.

## Estado actual
- **UX01 y UX01R entregados** (`docs/UX01_REPORTE.md`, `docs/UX01R_REPORTE.md`, `docs/UX01_DECISIONES.md`): rediseño por tareas, R17 cerrado, Evaluación simplificada. Frontend 234/234, build de producción, comprobación acotada 18/18 en la imagen real. R12–R16 aceptados localmente por Codex: no repetir.
- **Prueba humana de comprensión: PENDIENTE.** La observación de Rogelio «No comprendió el uso en su primera visita» sigue abierta; se cierra solo con su nueva prueba (`docs/T13_GUION_ACEPTACION.md`, «Prueba de comprensión (UX01)»). No completar su columna por inferencia.
- **Azure/publicación: SIN AUTORIZACIÓN.** Paquete para una única autorización en `docs/T11_PLAN_DESPLIEGUE.md` (no enviado ni ejecutado). `Microsoft.App` registrado, `ManagedEnvironmentCount` Brazil South 0/1. No se creó ningún recurso, no se subió ninguna imagen ni dato. ETAPA_15 diferida. No repetir acceso/registro/consultas de Azure.
- Entrega final: 23/10/2026. Pendientes después de la prueba humana: revisión de Codex de UX01R, T14 final (informe, manual, video con las pantallas finales), T15, decisión de publicación (A13) y política posterior al 23/10.

## Estado de los servicios al cerrar (sin pérdida de datos)
- **Detenidos:** proyecto compose `df-demo` (mongo, api, worker, proxy) con `demo_local stop` y el contenedor `df-mongo-dev`. No había trabajos en cola/ejecución ni corridas en staging al detenerlos.
- **Conservados:** contenedores (detenidos, no eliminados), volúmenes `df-demo_*` (base restaurada `df_demo_20261017221940`, subidas, certificados), base de desarrollo en `df-mongo-dev` (v1/v2/pub intactas), respaldos en `artifacts/private/` (t11a/backup, t11b/respaldo), imágenes (`df-app:ux01r-f95092f`), estado y credenciales privadas (`artifacts/private/t13b/demo_state.json`, `demo_credenciales.txt`; nunca imprimirlas ni versionarlas). Otros contenedores del equipo no se tocaron.

## Cómo volver a encender mañana (en este orden)
1. `docker start df-mongo-dev` (solo si hace falta el Mongo de desarrollo/tests; la demo no lo usa).
2. `.venv\Scripts\python.exe -m scripts.demo_local up` (reutiliza imagen y volúmenes; **no** restaura de nuevo porque el estado privado marca `restored=true`; sin `--build`).
3. `.venv\Scripts\python.exe -m scripts.demo_local status` → debe decir «misma base en api y worker … True», las corridas final, histórica activa, histórica sustituida (y el análisis de ensayo `gen-20260710-…`), puntero `hist-20260710-4ea348836e35`, jobs 0.
4. Abrir `https://localhost:8443` (certificado autofirmado: «Avanzado → Continuar»; Ctrl+F5). Usuarios `demo_lector` y `demo_admin`; contraseñas solo en `artifacts/private/t13b/demo_credenciales.txt`.
Parada segura: `demo_local stop`; para quitar contenedores conservando datos: `demo_local down` (nunca `down -v` ni limpiezas de Docker).

## Qué hacer mañana
1. Leer ESTADO.md, este archivo y `docs/UX01R_REPORTE.md`.
2. Rogelio repite la prueba de comprensión (tres tareas) y anota sus resultados reales; Claude corrige solo lo que él encuentre confuso.
3. Esperar la revisión de Codex de UX01R.
4. Solo con autorización explícita de Rogelio: ejecutar el plan de publicación (acciones 1–7). Sin ella, preparar la entrega local (T14/T15) y no tocar Azure.
- Si se interrumpe: `git status`, `docker ps -a`, `demo_local status`.
