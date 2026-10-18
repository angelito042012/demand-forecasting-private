# Guía local de la demostración (T08, T10)

Demostración local con **resultados existentes de desarrollo** (corrida histórica de desarrollo al 10/07/2026). No es un despliegue, no ejecuta compras y todo inventario es **simulado con supuestos; no corresponde al inventario real de la empresa**. Agosto no se consulta.

## Requisitos

- Windows, Python 3.12 con el entorno `.venv` del proyecto, Node 24 / npm 11, y MongoDB en `127.0.0.1:27017` (contenedor `df-mongo-dev`; los scripts no lo crean ni lo detienen).
- Base `demand_forecasting_v2` con las ventas importadas (ver `docs/ESTADO.md`).
- Variables en `.env` local (no versionado; use `.env.example` como plantilla). Para HTTP local: `COOKIE_SECURE=false` (excepción explícita solo con `APP_ENV=development`).

## Pasos

1. **Crear un usuario administrador** (una vez; la contraseña se pide por consola y no se imprime ni se guarda en texto):
   `.venv\Scripts\python.exe -m backend.cli create-user --username <usuario> --role admin`
   Un lector: igual con `--role lector`. No existe registro público ni contraseñas por defecto. Sin usuario no hay acceso (no hay *bypass*).
2. **Publicar la corrida histórica** (una vez; CLI privilegiada, idempotente; verifica checksums, fuentes y la referencia aprobada T07; calcula las señales exactas de la recomendación desde las ventas aprobadas):
   `.venv\Scripts\python.exe -m scripts.publish_run --manifest t07` (para sustituir una corrida con un defecto: `--supersede <run_id>`; la anterior se conserva marcada como sustituida).
3. **Iniciar** API y frontend (la API arranca con `--no-proxy-headers`: no confía en `X-Forwarded-For` del cliente; ver contrato de proxy en `docs/T08_CONTRATO.md` §8): `powershell -File scripts/start-local.ps1` → API `http://127.0.0.1:8000/api/v1/health`, web `http://localhost:4200` (el servidor de Angular hace proxy de `/api`, mismo origen).
   `start-local.ps1` también lanza el **worker** (`python -m pipeline.jobs.worker`), que ejecuta importaciones y generaciones encoladas desde la web; todos quedan en `artifacts/private/t08/procesos.json` (pid, hora de inicio, ejecutable).
4. **Detener** solo los procesos propios: `powershell -File scripts/stop-local.ps1`.

## Flujo de la demostración

Acceso → Corridas (corrida histórica de desarrollo al 10/07/2026, con su antigüedad) → Pronósticos (filtrar por categoría/SKU; comparar `promedio_28` —método elegido—, RF —comparador experimental que no ganó— y el control cero) → Recomendaciones (ver el cálculo paso a paso: stock simulado al 10/07, tránsito al origen, pronóstico de 14 días, seguridad de 7 días, objetivo, posición y pedido; productos sin inventario simulado se muestran sin recomendación) → Comparación (backtests T07 y escenarios) → Salir.

## Carga web, generación y temporizador (T10)

- Admin → Importaciones: subir un `.xlsx` mensual (marzo–julio 2026; agosto se rechaza). El mismo archivo ya aprobado devuelve «Sin cambios»; otra fuente para un mes aprobado se rechaza (ver `docs/REMEDIACION_FUENTES.md`). Admin → Corridas: generar `promedio_28` con origen entre 01/06 y 10/07/2026 (horizonte 21). El lector no ve ni puede usar estas acciones.
- Worker manual: `.venv\Scripts\python.exe -m pipeline.jobs.worker --once` (una vuelta) o sin `--once` (continuo).
- Temporizador (deshabilitado por defecto): `.venv\Scripts\python.exe -m pipeline.jobs.scheduler --once` o `--loop --enable` (06:00 Lima, intervalo 1440 min); misma ranura no duplica trabajos.
- La corrida generada no activa el puntero de corrida por defecto; se elige en el selector de corrida.

## Qué no hace todavía

Despliegue/HTTPS en la nube (publicación pendiente de aprobación; ver `docs/T11_PLAN_DESPLIEGUE.md`) y aceptación humana. Ya existen, y están documentados aparte: evaluación final T12 (`docs/T12_RESULTADOS.md`), contenedores y copia/restauración (`docs/T11A_EMPAQUETADO.md`, `docs/T11B_ACTA_RECUPERACION_INTEGRAL.md`) y pruebas locales de rendimiento/uso (`docs/T13A_REPORTE.md`). La carga masiva por CLI sigue disponible: `python -m pipeline.data.importer --source <carpeta> --db <base>`.

Tras T10R: la importación CLI es administrativa **serial, nunca simultánea con cargas web/worker**, porque no usa la reserva mensual del handler. El timer continúa deshabilitado por defecto y requiere fuentes/config estables durante recuperación; no afirmar exclusión global de cualquier escritor ni cancelación instantánea de un lote ya enviado. T12 es un runner dedicado de evaluación final, no una ampliación de la carga web o de la generación de desarrollo.

## Accesos necesarios para el despliegue posterior (sin contratar nada ahora)

- Suscripción Azure con permiso para crear: App Service o Container Apps (API), Static Web Apps o almacenamiento (frontend), Key Vault, Application Insights; presupuesto autorizado y región.
- MongoDB Atlas (cuenta/organización, proyecto, clúster con IP/red permitida) o alternativa autorizada; usuario de base con privilegios mínimos.
- Dominio/certificado HTTPS (o dominio de la plataforma) y política de copias/restauración.
- Los secretos se entregan por el gestor de secretos de la plataforma, nunca por chat ni en el repositorio.
