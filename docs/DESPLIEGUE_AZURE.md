# Despliegue en Azure Container Apps

**Fecha:** 2026-11-10
**Ejecutado por:** Milton (líder del proyecto)
**Cuenta Azure:** Estudiante (Azure for Students, $100 crédito)

---

## Arquitectura desplegada

```
Usuario → HTTPS → Azure Container Apps (capstone-api, puerto 8000)
                        ↓
                   MongoDB Atlas (clustersv.pn9x8.mongodb.net)
                        ↑
              Azure Container Apps (capstone-worker, sin ingress)
```

- **capstone-api**: Sirve el frontend Angular + API FastAPI (uvicorn, puerto 8000)
- **capstone-worker**: Procesa jobs en segundo plano (sin acceso público)
- **MongoDB Atlas**: Base de datos en cluster M0 free tier (São Paulo)
- **Azure Container Registry**: Almacena la imagen Docker

---

## Recursos creados en Azure

| Recurso | Nombre | Detalles |
|---|---|---|
| Resource Group | `rg-capstone` | Región: Brazil South |
| Container Registry | `capstonecr2026` | SKU Basic, admin habilitado |
| Container Apps Environment | `capstone-env` | Con Log Analytics automático |
| Container App (API) | `capstone-api` | 0.5 vCPU, 1 GB RAM, min-replicas=0 |
| Container App (Worker) | `capstone-worker` | 0.5 vCPU, 1 GB RAM, min-replicas=0 |

**URL pública:** `https://capstone-api.icypebble-fc2fe1de.brazilsouth.azurecontainerapps.io/`
**IP estática del entorno:** `20.201.103.203`

---

## Pasos realizados (reproducibles)

### Prerequisitos

1. Cuenta Azure con créditos de estudiante ($100)
2. Azure CLI instalado (`winget install Microsoft.AzureCLI`)
3. Docker Desktop corriendo
4. Imagen Docker del proyecto construida localmente

### Paso 1: Iniciar sesión en Azure

```bash
az login
```

Se abre el navegador, inicias sesión con tu cuenta de Azure.

### Paso 2: Registrar proveedores necesarios

Azure requiere que ciertos proveedores estén habilitados en la suscripción. Solo se hace una vez:

```bash
az provider register --namespace Microsoft.ContainerRegistry --wait
az provider register --namespace Microsoft.App --wait
az provider register --namespace Microsoft.OperationalInsights --wait
```

Estos proveedores habilitan: Container Registry, Container Apps y Log Analytics respectivamente. El `--wait` espera a que termine el registro (~1-2 minutos cada uno).

### Paso 3: Crear grupo de recursos

```bash
az group create -n rg-capstone -l brazilsouth -o table
```

Un grupo de recursos es un contenedor lógico que agrupa todos los recursos de Azure del proyecto. Se eligió `brazilsouth` por ser la región más cercana a Perú.

### Paso 4: Crear Azure Container Registry (ACR)

```bash
az acr create -n capstonecr2026 -g rg-capstone --sku Basic --admin-enabled true -o table
```

ACR es el registro privado donde se almacena la imagen Docker. `--admin-enabled true` permite que Container Apps extraiga la imagen con credenciales de admin (alternativa: managed identity, más compleja).

### Paso 5: Construir la imagen Docker

```bash
cd D:\PROYECTOS2\Entrega_equipo_20261023\github_clean\repo
docker build -t capstone-app:latest -f Dockerfile .
```

La imagen usa un Dockerfile multi-stage:
1. **Etapa 1 (node:24-slim):** Compila el frontend Angular con `npx ng build`
2. **Etapa 2 (python:3.12-slim):** Instala dependencias Python desde `requirements.lock.txt`
3. **Etapa 3 (python:3.12-slim):** Imagen final con el código, usuario no-root, healthcheck

### Paso 6: Subir la imagen al ACR

```bash
az acr login -n capstonecr2026
docker tag capstone-app:latest capstonecr2026.azurecr.io/capstone-app:v3
docker push capstonecr2026.azurecr.io/capstone-app:v3
```

1. `az acr login` autentica Docker contra el registro de Azure
2. Se etiqueta la imagen con la URL del registro + versión `v3`
3. `docker push` sube la imagen (~500 MB comprimida)

### Paso 7: Crear el entorno de Container Apps

```bash
az containerapp env create -n capstone-env -g rg-capstone -l brazilsouth
```

El entorno es la infraestructura compartida donde corren los contenedores. Crea automáticamente un workspace de Log Analytics para los logs.

### Paso 8: Desplegar el contenedor API

```bash
az containerapp create \
  -n capstone-api \
  -g rg-capstone \
  --environment capstone-env \
  --image capstonecr2026.azurecr.io/capstone-app:v3 \
  --registry-server capstonecr2026.azurecr.io \
  --target-port 8000 \
  --ingress external \
  --min-replicas 0 --max-replicas 1 \
  --cpu 0.5 --memory 1.0Gi \
  --secrets mongo-uri="<MONGODB_URI>" auth-secret="<AUTH_SECRET_ALEATORIO>" \
  --env-vars \
    APP_ENV=production \
    MONGODB_URI=secretref:mongo-uri \
    MONGODB_DATABASE=demand_forecasting_pub \
    AUTH_SECRET=secretref:auth-secret \
    ALLOWED_ORIGINS=https://<URL_ASIGNADA> \
    DF_UPLOADS_DIR=/data/uploads \
    APP_TIMEZONE=America/Lima \
  --command "df-entrypoint" "api"
```

Notas importantes:
- `--ingress external`: Expone la API a internet con HTTPS automático
- `--min-replicas 0`: Escala a cero cuando no hay tráfico (ahorra créditos)
- `--secrets`: Los valores sensibles (URI de MongoDB, clave de sesión) se almacenan como secretos de Azure, nunca en texto plano
- `secretref:mongo-uri`: Las variables de entorno referencian los secretos por nombre
- `--command "df-entrypoint" "api"`: Ejecuta el entrypoint con el rol "api" (uvicorn en puerto 8000)
- `--registry-server`: Azure detecta automáticamente las credenciales del ACR

### Paso 9: Actualizar ALLOWED_ORIGINS

Después de crear la app, Azure asigna una URL. Se actualiza la variable:

```bash
az containerapp update \
  -n capstone-api -g rg-capstone \
  --set-env-vars ALLOWED_ORIGINS=https://capstone-api.icypebble-fc2fe1de.brazilsouth.azurecontainerapps.io
```

### Paso 10: Desplegar el contenedor Worker

```bash
az containerapp create \
  -n capstone-worker \
  -g rg-capstone \
  --environment capstone-env \
  --image capstonecr2026.azurecr.io/capstone-app:v3 \
  --registry-server capstonecr2026.azurecr.io \
  --min-replicas 0 --max-replicas 1 \
  --cpu 0.5 --memory 1.0Gi \
  --secrets mongo-uri="<MONGODB_URI>" auth-secret="<AUTH_SECRET>" \
  --env-vars \
    APP_ENV=production \
    MONGODB_URI=secretref:mongo-uri \
    MONGODB_DATABASE=demand_forecasting_pub \
    AUTH_SECRET=secretref:auth-secret \
    DF_UPLOADS_DIR=/data/uploads \
    APP_TIMEZONE=America/Lima \
  --command "df-entrypoint" "worker"
```

El worker NO tiene `--ingress` (sin acceso público), solo procesa jobs internos conectándose a la misma base de datos.

### Paso 11: Verificar el despliegue

```bash
# Health check de la API
curl https://capstone-api.icypebble-fc2fe1de.brazilsouth.azurecontainerapps.io/api/v1/health
# Respuesta: {"status":"ok","database":"ok","version":"0.1.0","environment":"production","timezone":"America/Lima"}

# Obtener IP estática del entorno
az containerapp env show -n capstone-env -g rg-capstone --query "properties.staticIp" -o tsv
# Resultado: 20.201.103.203
```

### Paso 12: Configurar Atlas Network Access

En MongoDB Atlas → Network Access, reemplazar `0.0.0.0/0` por:
- `20.201.103.203/32` (IP del entorno Azure)
- Tu IP personal de casa/universidad

---

## Variables de entorno configuradas

| Variable | Valor | Tipo |
|---|---|---|
| `APP_ENV` | `production` | Texto plano |
| `MONGODB_URI` | `mongodb+srv://...` | Secreto de Azure |
| `MONGODB_DATABASE` | `demand_forecasting_pub` | Texto plano |
| `AUTH_SECRET` | (aleatorio 64 chars) | Secreto de Azure |
| `ALLOWED_ORIGINS` | URL de la app | Texto plano |
| `DF_UPLOADS_DIR` | `/data/uploads` | Texto plano |
| `APP_TIMEZONE` | `America/Lima` | Texto plano |

---

## Costos estimados

| Componente | Costo mensual |
|---|---|
| Atlas M0 | Gratis (hasta 512 MB) |
| Container Apps (min-replicas=0) | ~$3-5/mes con uso mínimo |
| Container Registry (Basic) | ~$5/mes |
| **Total estimado** | **~$8-10/mes** |

Con $100 de créditos de estudiante: **~10-12 meses de operación**.

---

## Mantenimiento

### Actualizar la imagen

```bash
docker build -t capstone-app:latest -f Dockerfile .
docker tag capstone-app:latest capstonecr2026.azurecr.io/capstone-app:v4
docker push capstonecr2026.azurecr.io/capstone-app:v4
az containerapp update -n capstone-api -g rg-capstone --image capstonecr2026.azurecr.io/capstone-app:v4
az containerapp update -n capstone-worker -g rg-capstone --image capstonecr2026.azurecr.io/capstone-app:v4
```

### Ver logs

```bash
az containerapp logs show -n capstone-api -g rg-capstone --follow
```

### Eliminar todo (si es necesario)

```bash
az group delete -n rg-capstone --yes --no-wait
```

Esto elimina todos los recursos del grupo de una vez.

---

## Decisiones técnicas y justificación

1. **¿Por qué Azure Container Apps y no App Service?**
   Container Apps soporta escalar a cero (sin costo cuando no hay tráfico), multi-contenedor con el mismo entorno, y es más económico para workloads intermitentes.

2. **¿Por qué min-replicas=0?**
   Para ahorrar créditos de estudiante. La primera solicitud tarda ~20s en "despertar" (cold start), pero el costo en reposo es $0.

3. **¿Por qué Brazil South?**
   Región más cercana a Perú con disponibilidad de Container Apps. Latencia menor que US East.

4. **¿Por qué secretos y no variables planas?**
   Las credenciales de MongoDB y la clave de sesión nunca deben estar en texto plano. Azure Container Apps encripta los secretos en reposo y los inyecta como variables de entorno al iniciar el contenedor.

5. **¿Por qué dos contenedores (API + Worker)?**
   Separar responsabilidades: la API atiende solicitudes HTTP, el worker procesa jobs largos (pronósticos, recálculos). Si el worker falla, la API sigue funcionando.
