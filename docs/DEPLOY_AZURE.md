# Deploy a Azure Container Apps

Pasos para reconstruir y desplegar la imagen Docker en Azure.

## Prerrequisitos

- Docker Desktop corriendo
- Azure CLI instalado y sesion activa (`az login`)
- Acceso al resource group `rg-capstone`

## Paso 1 — Build de la imagen

Desde la raiz del repositorio:

```bash
docker build -t capstone-app:v4 .
```

Si falla `npm ci` por lock file desincronizado:

```bash
cd frontend
npm install
cd ..
docker build -t capstone-app:v4 .
```

## Paso 2 — Login al registry de Azure

```bash
az acr login --name capstonecr2026
```

## Paso 3 — Tag y push

```bash
docker tag capstone-app:v4 capstonecr2026.azurecr.io/capstone-app:v4
docker push capstonecr2026.azurecr.io/capstone-app:v4
```

## Paso 4 — Actualizar los container apps

Worker:

```bash
az containerapp update --name capstone-worker --resource-group rg-capstone --image capstonecr2026.azurecr.io/capstone-app:v4
```

API:

```bash
az containerapp update --name capstone-api --resource-group rg-capstone --image capstonecr2026.azurecr.io/capstone-app:v4
```

## Paso 5 — Verificar

```bash
az containerapp revision list --name capstone-worker --resource-group rg-capstone -o table
az containerapp revision list --name capstone-api --resource-group rg-capstone -o table
```

Confirmar que la revision mas reciente este en estado `Running`.

## Variables de entorno del worker

El Dockerfile ya define `DF_UPLOADS_DIR=/data/uploads` con permisos correctos. Si en Azure Portal la variable `DF_UPLOADS_DIR` tiene otro valor (como `/tmp/uploads`), se puede eliminar para usar el de la imagen o dejarlo en `/tmp/uploads` (ambos funcionan).

Variables requeridas en Azure (ya configuradas):

| Variable | Valor | Origen |
|---|---|---|
| `APP_ENV` | `production` | Manual |
| `MONGODB_URI` | (secreto) | Referencia a secreto `mongo-uri` |
| `MONGODB_DATABASE` | `demand_forecasting_pub` | Manual |
| `AUTH_SECRET` | (secreto) | Referencia a secreto `auth-secret` |
| `DF_UPLOADS_STORE` | `mongo` | Manual |
| `DF_UPLOADS_DIR` | `/tmp/uploads` o eliminar | Manual |
| `APP_TIMEZONE` | `America/Lima` | Manual |

## Versionado de imagenes

Para futuros deploys, incrementar la etiqueta (`v5`, `v6`, etc.) o usar el sha corto del commit:

```bash
docker build -t capstone-app:v5 .
docker tag capstone-app:v5 capstonecr2026.azurecr.io/capstone-app:v5
docker push capstonecr2026.azurecr.io/capstone-app:v5
az containerapp update --name capstone-worker --resource-group rg-capstone --image capstonecr2026.azurecr.io/capstone-app:v5
az containerapp update --name capstone-api --resource-group rg-capstone --image capstonecr2026.azurecr.io/capstone-app:v5
```
