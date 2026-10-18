# T13B — Cierre de R15/R16, demostración local lista y paquete de publicación

Fecha: 17/10/2026 (America/Lima). No se crearon recursos en la nube, no se registraron proveedores, no se transfirieron datos, no se repitieron modelos, la evaluación final ni la suite amplia. Aceptación humana y A13: **pendientes**.

## 1. R15 — medidor de rendimiento (`scripts/t13a_perf.py`)

- Percentil **nearest-rank** (`s[ceil(q·n)-1]`: p95 = 19.ª de 20, 95.ª de 100); lista vacía ⇒ `None` (sin excepción de `statistics`).
- Cada excepción HTTP/timeout y cada estado ≠ 200 se contabiliza por sesión; una tanda con menos muestras que las esperadas, errores o cero sesiones es `completa: false` y el programa **termina con código 1** (nunca «COMPLETA»).
- Recursos cerrados en `finally` (login fallido cierra el cliente; logout y cierre de sesiones); timeout total del arranque en frío (`--cold-timeout`, 120 s); TLS **verificado por defecto**, omisión solo con `--insecure-local`; muestras crudas privadas (`--samples`) y resumen de completitud.
- 9 regresiones sintéticas sin servicios (`tests/ops/test_t13a_perf.py`): percentil n=20/n=100, independencia del orden, cero muestras, tanda sana, un hilo que falla, estado 500, tanda vacía, timeout de arranque, cierre del cliente tras login fallido, TLS por defecto. **9 aprobadas** (`artifacts/private/t13b/pytest_r15.xml`); ruff limpio.
- `perf.json` original **conservado**. Sus cifras «p95» son una **cota conservadora** (la fórmula anterior devolvía el máximo de cada muestra de 20); no hay muestras crudas para recalcularlas y no se inventó un p95 nuevo. Se repitió **solo el ensayo corto local** con el medidor corregido (`perf_r15.json`, `perf_r15_muestras.json`): `completa=true`, 0 errores; p95 más alto **298,6 ms** (5 sesiones). Los **máximos de 2,06–2,50 s** (primera solicitud de 2 de 5 sesiones, bajo tope de 0,5 vCPU) se informan aparte en `docs/T13A_REPORTE.md` §2.1: la meta p95 < 2 s se cumple, la latencia máxima no es ≤ 2 s en todos los casos.

## 2. R16 — demostración sobre una copia restaurada con base común (`scripts/demo_local.py`)

Programa pequeño sobre el compose existente (sin tocar el sistema): `up`, `status [--writers]`, `create-user [--generate]`, `stop`, `down` (conserva volúmenes; nunca `down -v`). Estado privado en `artifacts/private/t13b/demo_state.json` (fuera de Git) que inyecta **la misma URI y base** a `api`, `worker` y `create-user` (se ejecuta dentro de `api`). `status` compara un hash del nombre de base que ve cada contenedor y lo contrasta con el estado, sin imprimir URI/claves.

Verificado en la demo real (proyecto compose `df-demo`):
- Copia restaurada del respaldo verificado T11A en la base nueva `df_demo_20261017221940`: sin problemas, 213,5 MB, puntero `hist-20260710-4ea348836e35`; v1/v2/pub y respaldos no se modificaron.
- `status`: api, worker y mongo `healthy`; **misma base en api y worker y en el estado: True**; corridas visibles: histórica activa `hist-20260710-4ea348836e35`, sustituida `hist-20260710-52b01cd999dd` y evaluación final `final-20260731-d587255d87fb`; 0 jobs, 0 corridas en staging.
- Artefacto concreto servido: `https://localhost:8443` (solo `127.0.0.1:8443`; Mongo/API/worker sin puertos publicados); `/api/v1/health` ok en modo `production`; HTML con `<link rel="stylesheet">` **sin `media=print` ni `onload`**; CSP intacta (`script-src 'self'`); HSTS presente. Imagen `df-app:t11a-local` `sha256:59c92de892aa…`, creada 17/10/2026 21:45 (Lima), con la corrección de estilos.
- Humo por HTTP (`artifacts/private/t13b/demo_verificacion.json`): login lector y admin 200; `/runs` lista las tres corridas con la histórica como única activa; final por categoría 777 filas (37×21); **lector no puede generar corridas (403)**.
- Usuarios: `demo_admin` y `demo_lector` con contraseñas **generadas y guardadas solo** en `artifacts/private/t13b/demo_credenciales.txt` (nunca impresas ni versionadas); para claves propias, `create-user` sin `--generate` pide la clave por consola.
- Mantenimiento: `status --writers` informa escritores activos antes de exportar; `stop-local.ps1` (procesos PowerShell) y `demo_local stop|down` (contenedores) son procedimientos distintos (`docs/MANUAL_OPERACION.md` §2, §2.1, §6).
- No se repitieron los 22 pasos de navegador ni la suite: es una comprobación del artefacto concreto. La demo queda **encendida** para la prueba humana (parada segura: `demo_local stop`).

## 3. Documentos ajustados

`MANUAL_OPERACION` (§2 demostración sobre copia restaurada; §2.1 desarrollo PowerShell con la advertencia de bases distintas; paradas separadas; sin `down -v` rutinario), `T13_GUION_ACEPTACION` (URL, versión, base activa, usuarios, cinco pasos), `MANUAL_USUARIO` (snapshot por corrida), `INFORME_FINAL_BORRADOR` (MAPE acum14 por entidad con total 14 días > 0; coberturas con su denominador), `MATRIZ_CIERRE` (observaciones SKU-fold ≠ SKU únicos; T13A/T13B), `T13A_REPORTE` (corrección R15), fechas a 17/10/2026 (Lima; las marcas en UTC se conservan), y autoridad vigente en `AGENTS.md`, `CLAUDE.md` y `RETOMAR_CLAUDE.md`. ESTADO/TRASPASO/BACKLOG consolidados; antecedentes en HISTORIAL.

## 4. Paquete de publicación

`docs/T11_PLAN_DESPLIEGUE.md`, «Paquete de publicación para una única autorización»: alcance cerrado, acciones 1–7, alternativas y política posterior en el punto 8, techo operativo propuesto US$ 20 (intervención a US$ 12; `spendingLimit=On` protege el saldo total, no es un corte de US$ 20; Cost Management con demora), transferencias limitadas, Atlas con usuario mínimo y credencial rotada, y el mensaje de autorización. **No autorizado ni ejecutado.**

## 5. Límites y pendientes

Demo y medidas son locales (no acreditan Azure/Atlas/HTTPS externo); no se investigó la causa de los máximos > 2 s; certificado autofirmado local; sin lector de pantalla; aceptación humana (A14) y A13 pendientes; informe, manual y video siguen siendo borradores.
