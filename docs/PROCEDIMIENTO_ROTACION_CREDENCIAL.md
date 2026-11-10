# Procedimiento de rotación de credencial de Atlas — listo para ejecutar

**Estado: PROCEDIMIENTO DOCUMENTADO, NO EJECUTADO.** La rotación requiere autorización del titular (Rogelio) y acceso a la consola de MongoDB Atlas. El equipo de desarrollo no tiene acceso a Atlas.

**Fecha de redacción:** 2026-11-10
**Pospuesto desde:** 23/10/2026 (decisión del titular)
**Riesgo identificado:** una credencial de Atlas se expuso en una captura de pantalla anterior. El usuario afectado no es `dfpub_app` (el usuario de la aplicación), pero su contraseña podría permitir acceso a la base si no se ha rotado.

---

## 1. Antecedentes

- **Usuario de la aplicación:** `dfpub_app` (rol `readWrite` solo en `demand_forecasting_pub`). Verificado: escritura en otra base denegada.
- **Usuario expuesto:** su nombre solo puede verse en Atlas → Security → Database Access. No hay copia de la credencial en esta máquina ni en Azure.
- **URI en producción:** almacenada como secreto en Azure Container Apps (variable `MONGODB_URI`). No está en el repositorio ni en archivos versionados.
- **Respaldo local:** `artifacts/private/atlas_uri.txt` (no versionado, solo contiene la URI de `dfpub_app`).

## 2. Prerrequisitos

- [ ] Autorización de Rogelio (titular de la cuenta de Atlas)
- [ ] Acceso de Rogelio a la consola de MongoDB Atlas (https://cloud.mongodb.com)
- [ ] Conocer qué usuarios de base de datos existen (Rogelio los lista en Atlas → Security → Database Access)

## 3. Procedimiento paso a paso

### Paso 1: Identificar el usuario expuesto

**Quién:** Rogelio (en la consola de Atlas)

1. Ir a Atlas → Security → Database Access
2. Listar los usuarios de base de datos
3. Comunicar al equipo **solo los nombres y roles** (sin contraseñas)
4. Identificar por descarte cuál es el expuesto (no es `dfpub_app`)

### Paso 2: Rotar o eliminar el usuario expuesto

**Quién:** Rogelio (en la consola de Atlas)

**Opción A — Rotar la contraseña (si alguien usa ese usuario):**
1. En Database Access, seleccionar el usuario expuesto
2. Pulsar "Edit" → "Edit Password"
3. Generar una nueva contraseña aleatoria (Atlas ofrece generar una)
4. Guardarla en un lugar seguro (no compartir por chat)
5. Pulsar "Update User"

**Opción B — Eliminar el usuario (si nadie lo usa):**
1. En Database Access, seleccionar el usuario expuesto
2. Pulsar "Delete" → Confirmar
3. Verificar que `dfpub_app` sigue existiendo y no fue el eliminado

### Paso 3: Verificar que la aplicación sigue funcionando

**Quién:** Equipo de desarrollo

1. Verificar que la API responde:
   ```
   curl -s https://dfpub-api.ashyglacier-9e3e37bc.brazilsouth.azurecontainerapps.io/api/v1/health
   ```
   Respuesta esperada: `{"status": "ok", "database": "available", ...}`

2. Verificar que el worker conecta:
   ```
   az containerapp logs show -n dfpub-worker -g rg-demand-forecasting-pub --tail 5
   ```
   Buscar: línea de inicio sin errores de conexión.

3. Si la API reporta `"database": "unavailable"`:
   - **No se tocó `dfpub_app`:** revisar el paso 2 (¿se eliminó el usuario equivocado?)
   - **Se tocó `dfpub_app` por error:** restaurar su contraseña en Atlas y actualizar `MONGODB_URI` en Azure:
     ```
     az containerapp update -n dfpub-api -g rg-demand-forecasting-pub --set-env-vars "MONGODB_URI=<nueva_uri>"
     az containerapp update -n dfpub-worker -g rg-demand-forecasting-pub --set-env-vars "MONGODB_URI=<nueva_uri>"
     ```
     Luego escalar a 0 y volver a 1 para que tome la nueva variable.

### Paso 4: Registrar el resultado

- Anotar la fecha y hora de la rotación
- Confirmar qué usuario se rotó/eliminó (sin escribir la contraseña)
- Confirmar que la aplicación sigue funcionando (captura del health check)
- Actualizar este documento con el resultado

## 4. Verificación de que la contraseña antigua ya no funciona

Esta verificación depende de Rogelio: como el equipo no tiene la credencial antigua ni acceso a Atlas, no puede probar si la contraseña anterior sigue siendo válida. Rogelio puede verificarlo intentando conectar con la credencial antigua desde `mongosh`:

```
mongosh "mongodb+srv://<usuario_expuesto>:<contraseña_antigua>@demand-forecasting-dev.xxxxx.mongodb.net/demand_forecasting_pub"
```

Si la conexión falla con error de autenticación, la rotación fue exitosa.

## 5. Medidas complementarias (opcionales, post-rotación)

| Medida | Descripción | Prioridad |
|---|---|---|
| Revisar lista de usuarios en Atlas | Eliminar cualquier usuario de prueba que ya no se use | Media |
| Verificar roles de `dfpub_app` | Confirmar que solo tiene `readWrite` en `demand_forecasting_pub` | Ya verificado |
| Revisar Network Access | Confirmar que solo están las IPs necesarias (sin `0.0.0.0/0`) | Ya verificado |
| Habilitar alertas de Atlas | Configurar alertas por conexiones fallidas o desde IPs desconocidas | Baja |

## 6. Riesgo residual

Hasta que se ejecute la rotación:
- La credencial expuesta podría permitir acceso a la base si el usuario tiene permisos suficientes.
- El riesgo se mitiga porque: (a) Atlas tiene lista de IPs permitidas (no `0.0.0.0/0`), (b) el usuario expuesto probablemente no es `dfpub_app` (único con `readWrite`), (c) no se conoce el alcance de sus permisos sin acceso a Atlas.
- **La mitigación no es equivalente a la corrección.** La rotación debe ejecutarse.
