# Plan de migración a credenciales propias

**Fecha:** 2026-11-10
**Autorizado por:** Rogelio (titular anterior)
**Ejecuta:** Milton (nuevo líder del proyecto)

---

## Objetivo

Migrar la infraestructura del proyecto (MongoDB Atlas y opcionalmente Azure) de las
credenciales de Rogelio a las de Milton, para que el equipo tenga autonomía completa
y la credencial expuesta quede rotada.

---

## Opción A: Solo Atlas (recomendada para el 13/11)

Tiempo estimado: **1–2 horas**

### Paso 1: Crear cuenta y cluster en Atlas

1. Ir a [cloud.mongodb.com](https://cloud.mongodb.com) y crear cuenta con tu email
2. Crear un proyecto (ej. `demand-forecasting-capstone`)
3. Crear un cluster **M0 (free tier)** en la región más cercana (São Paulo o Virginia)
4. En **Database Access**: crear usuario `app_user` con rol `readWrite` en la base `demand_forecasting_pub`
5. En **Network Access**: añadir `0.0.0.0/0` temporalmente para la migración (luego restringir)

### Paso 2: Exportar datos del cluster de Rogelio

```bash
# Pedir a Rogelio el URI de Atlas o usar el backup existente
# Si hay backup local:
ls artifacts/private/cloud_bundle_20261021/

# Si no, exportar con mongodump (requiere URI de Rogelio):
mongodump --uri="mongodb+srv://<user>:<pass>@<cluster>.mongodb.net/demand_forecasting_pub" --out=dump_migracion/
```

**ALTERNATIVA sin acceso a Atlas de Rogelio:** usar los datos locales de `df_test_local` que ya tienen los 9 meses (130,747 docs de ventas + 50 productos de stock).

### Paso 3: Importar datos al nuevo cluster

```bash
# Con mongorestore desde el dump:
mongorestore --uri="mongodb+srv://app_user:<tu_pass>@<tu_cluster>.mongodb.net/" --db demand_forecasting_pub dump_migracion/demand_forecasting_pub/

# O subir desde la base local:
mongodump --uri="mongodb://127.0.0.1:27017" --db df_test_local --out=dump_local/
mongorestore --uri="mongodb+srv://app_user:<tu_pass>@<tu_cluster>.mongodb.net/" --db demand_forecasting_pub dump_local/df_test_local/
```

### Paso 4: Verificar

```bash
python -c "
from pymongo import MongoClient
# Reemplaza con tu URI
client = MongoClient('mongodb+srv://app_user:<pass>@<cluster>.mongodb.net/')
db = client['demand_forecasting_pub']
print('plan_sales:', db.plan_sales.estimated_document_count())
print('snapshots:', db.inventory_reconstructed_snapshots.estimated_document_count())
print('items:', db.inventory_reconstructed_items.estimated_document_count())
"
```

### Paso 5: Restringir acceso

En Atlas **Network Access**, reemplazar `0.0.0.0/0` por las IPs específicas:
- Tu IP de casa/universidad
- IPs de Azure (si despliegas)

---

## Opción B: Atlas + Azure (si tienes créditos de estudiante)

Tiempo estimado: **3–4 horas adicionales**

### Prerequisitos

- Cuenta Azure con créditos de estudiante (Azure for Students: $100 gratis)
- Azure CLI instalado (`az login`)

### Paso 1: Crear el entorno

```bash
# Grupo de recursos
az group create -n rg-capstone -l brazilsouth

# Container Apps Environment
az containerapp env create -n capstone-env -g rg-capstone -l brazilsouth
```

### Paso 2: Construir y subir la imagen

```bash
# Desde la raíz del repo
docker build -t capstone-app:latest -f deploy/Dockerfile .

# Crear Azure Container Registry (o usar Docker Hub)
az acr create -n capstonecr -g rg-capstone --sku Basic
az acr login -n capstonecr
docker tag capstone-app:latest capstonecr.azurecr.io/capstone-app:latest
docker push capstonecr.azurecr.io/capstone-app:latest
```

### Paso 3: Desplegar la app

```bash
# API
az containerapp create \
  -n capstone-api -g rg-capstone \
  --environment capstone-env \
  --image capstonecr.azurecr.io/capstone-app:latest \
  --target-port 8000 \
  --ingress external \
  --env-vars MONGODB_URI=secretref:mongo-uri MONGODB_DATABASE=demand_forecasting_pub \
  --secrets mongo-uri="mongodb+srv://app_user:<pass>@<cluster>.mongodb.net/"
```

### Paso 4: Obtener IP de salida y añadir a Atlas

```bash
# Dentro de la réplica
az containerapp exec -n capstone-api -g rg-capstone --command "curl -s ifconfig.me"
# Añadir esa IP/32 a Atlas Network Access
```

### Paso 5: Verificar

Abrir la URL que te da Azure Container Apps y probar login + consultas.

---

## Qué NO hacer

- No borrar el cluster/datos de Rogelio — es su infraestructura
- No usar las credenciales de Rogelio en tu nuevo entorno
- No exponer tu URI de Atlas en el código o git — usar variables de entorno
- No poner `0.0.0.0/0` en Atlas en producción (solo durante migración)

---

## Después de migrar

1. Actualizar `.env` local con la nueva URI de Atlas
2. Si desplegaste en Azure: actualizar el secret `mongo-uri` en Container Apps
3. Rogelio puede desactivar su cluster cuando lo considere
4. Documentar la nueva URI (sin credenciales) en el informe como evidencia de despliegue
