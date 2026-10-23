# Demand Forecasting - Prevision de ventas y compras

Sistema de prevision de demanda y recomendacion de compras para una MYPE. Construido con Angular, FastAPI, Python (scikit-learn / XGBoost) y MongoDB.

## Estado actual

La aplicacion tiene un plan de noviembre v2 funcional con 50 productos, escenarios de entrega a 7 y 14 dias, y recomendaciones de compra explicables. La version entregada (`t22g-a9119ae`) fue aceptada funcionalmente para exposicion el 23/10/2026.

**Pendiente:** actualizacion operativa autonoma (nuevos cortes de datos), evaluacion academica formal y automatizacion. Ver `docs/ESTADO.md` y `docs/BACKLOG.md`.

## Requisitos

- Python 3.12
- Node.js >= 18 (para el frontend Angular)
- Docker y Docker Compose
- MongoDB Database Tools (`mongorestore`) para restaurar respaldos

## Instalacion local

### 1. Clonar y preparar el entorno Python

```
git clone <url-del-repo> demand-forecasting
cd demand-forecasting
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate
pip install -r requirements.lock.txt
```

### 2. Crear un entorno Docker aislado

El script `scripts/demo_local.py` crea entornos Docker aislados con credenciales auto-generadas:

```
python -m scripts.demo_local --env mi_entorno up
```

Esto construye la imagen, levanta MongoDB + API + Worker + Proxy (Caddy con TLS autofirmado) y restaura el respaldo academico incluido.

### 3. Crear usuarios locales

```
python -m scripts.demo_local --env mi_entorno create-user mi_admin admin
python -m scripts.demo_local --env mi_entorno create-user mi_lector lector
```

Las credenciales se guardan en `artifacts/private/t13b/<env>_credenciales.txt`.

### 4. Acceder a la aplicacion

Abrir `https://localhost:<puerto>` (el puerto se muestra al crear el entorno). Aceptar el certificado autofirmado.

### 5. Detener / reiniciar

```
python -m scripts.demo_local --env mi_entorno stop     # detiene, conserva datos
python -m scripts.demo_local --env mi_entorno up        # reinicia
python -m scripts.demo_local --env mi_entorno down      # elimina contenedores y volumenes
```

## Estructura del proyecto

```
backend/          API FastAPI y logica de negocio
frontend/         Aplicacion Angular
pipeline/         Pipeline de datos y modelos ML
scripts/          Utilidades (demo_local, bootstrap, etc.)
tests/            Pruebas (backend, jobs, plan, publish, inventory)
deploy/           Dockerfile, Caddyfile, entrypoint, mongo-init
infra/            Bicep templates para Azure (referencia)
config/           Configuracion de experimentos y seleccion de modelos
docs/             Documentacion tecnica y reportes
data/synthetic/   Datos sinteticos para desarrollo y pruebas
```

## Datos privados

Este repositorio **no contiene** datos empresariales, respaldos de produccion ni credenciales. Los datos necesarios para operar con el escenario real se entregan por un canal separado y se almacenan en `artifacts/private/` (excluido de Git).

Para restaurar el escenario operativo completo se necesita:
1. El respaldo operativo (`cloud_bundle_20261021/`) con sus dos archivos `.gz`
2. Restaurar con `mongorestore` y remapeo de namespace a la base local
3. Consultar la guia tecnica entregada por separado

## Pruebas

```
# Backend (777 tests)
python -m pytest tests/backend tests/jobs tests/plan tests/publish tests/inventory -q

# Frontend (312 tests)
cd frontend && ng test
```

## Arquitectura

- **API:** FastAPI (uvicorn), autenticacion por sesion + CSRF, roles admin/lector
- **Worker:** procesa jobs de generacion de planes en background
- **MongoDB:** almacen de datos, planes, corridas y sesiones
- **Proxy:** Caddy con TLS autofirmado para desarrollo local
- **Frontend:** Angular con pantallas de ventas, existencias, compra recomendada y evaluacion

## Infraestructura en nube

El proyecto incluye templates de Azure (`infra/main.bicep`) como referencia. El despliegue en nube requiere permisos y presupuesto propios; la configuracion del titular anterior **no** se hereda automaticamente. Los accesos a Azure y Atlas se gestionan por separado.

## Reglas del proyecto

- No fabricar resultados ni datos reales
- Datos sinteticos siempre etiquetados como tales
- No repetir T12 ni reentrenar contra agosto
- No desplegar sin autorizacion ni presupuesto
- Credenciales solo en `.env` (no versionado) o variables de entorno
