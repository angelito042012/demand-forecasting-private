# Guía local de la demostración (T08)

Demostración local con **resultados existentes de desarrollo** (corrida histórica de desarrollo al 10/07/2026). No es un despliegue, no ejecuta compras y todo inventario es **simulado con supuestos; no corresponde al inventario real de la empresa**. Agosto no se consulta.

## Requisitos

- Windows, Python 3.12 con el entorno `.venv` del proyecto, Node 24 / npm 11, y MongoDB en `127.0.0.1:27017` (contenedor `df-mongo-dev`; los scripts no lo crean ni lo detienen).
- Base `demand_forecasting_v2` con las ventas importadas (ver `docs/ESTADO.md`).
- Variables en `.env` local (no versionado; use `.env.example` como plantilla). Para HTTP local: `COOKIE_SECURE=false` (excepción explícita solo con `APP_ENV=development`).

## Pasos

1. **Crear un usuario administrador** (una vez; la contraseña se pide por consola y no se imprime ni se guarda en texto):
   `.venv\Scripts\python.exe -m backend.cli create-user --username <usuario> --role admin`
   Un lector: igual con `--role lector`. No existe registro público ni contraseñas por defecto. Sin usuario no hay acceso (no hay *bypass*).
2. **Publicar la corrida histórica** (una vez; CLI privilegiada, idempotente; verifica checksums contra el manifiesto):
   `.venv\Scripts\python.exe -m scripts.publish_run --manifest t07`
3. **Iniciar** API y frontend: `powershell -File scripts/start-local.ps1` → API `http://127.0.0.1:8000/api/v1/health`, web `http://localhost:4200` (el servidor de Angular hace proxy de `/api`, mismo origen).
4. **Detener** solo los procesos propios: `powershell -File scripts/stop-local.ps1`.

## Flujo de la demostración

Acceso → Corridas (corrida histórica de desarrollo al 10/07/2026, con su antigüedad) → Pronósticos (filtrar por categoría/SKU; comparar `promedio_28` —método elegido—, RF —comparador experimental que no ganó— y el control cero) → Recomendaciones (ver el cálculo paso a paso: stock simulado al 10/07, tránsito al origen, pronóstico de 14 días, seguridad de 7 días, objetivo, posición y pedido; productos sin inventario simulado se muestran sin recomendación) → Comparación (backtests T07 y escenarios) → Salir.

## Qué no hace todavía

Carga de Excel desde la web, ejecución de corridas desde la aplicación, tareas programadas, HTTPS, copia/restauración y despliegue en la nube (T10–T13). La carga nueva sigue por CLI: `python -m pipeline.data.importer --source <carpeta> --db <base>`.

## Accesos necesarios para el despliegue posterior (sin contratar nada ahora)

- Suscripción Azure con permiso para crear: App Service o Container Apps (API), Static Web Apps o almacenamiento (frontend), Key Vault, Application Insights; presupuesto autorizado y región.
- MongoDB Atlas (cuenta/organización, proyecto, clúster con IP/red permitida) o alternativa autorizada; usuario de base con privilegios mínimos.
- Dominio/certificado HTTPS (o dominio de la plataforma) y política de copias/restauración.
- Los secretos se entregan por el gestor de secretos de la plataforma, nunca por chat ni en el repositorio.
