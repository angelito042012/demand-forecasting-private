# T11 Plan de despliegue (propuesta, NO ejecutada)

Fecha: 17/10/2026. Estado: **propuesta para aprobación**. No se ha creado ningún recurso en la nube, no se ha iniciado sesión en Azure ni en Atlas, no se ha subido ninguna imagen a un registro y no se ha transferido ningún dato fuera de este equipo. Todo lo desplegable fue construido y probado solo en Docker local (ver `docs/T11A_EMPAQUETADO.md`). Los datos son históricos (marzo–agosto 2026); el inventario es simulado.

Convención: **[V]** = verificado en fuente oficial (URL y fecha 17/10/2026); **[NV]** = no verificado, con el método para verificarlo; **[S]** = supuesto de este plan.

## 1. Arquitectura propuesta

```
Navegador (HTTPS, certificado de la plataforma, dominio *.azurecontainerapps.io; sin comprar dominio)
        │
        ▼
Ingress de Azure Container Apps (TLS, X-Forwarded-For)
        │  mismo origen: Angular compilado + /api
        ▼
[Container App  dfpub-api]  imagen única, rol "api", 0,5 vCPU / 1 GiB, usuario 10001, FS de solo lectura salvo /data
        │                                   │
        │ SMB montado en /data              │ mongodb+srv (TLS)  ──►  MongoDB Atlas Free "demand-forecasting-dev"
        ▼                                   │                          (São Paulo; usuario de app mínimo; base demand_forecasting_pub)
[Azure Files share df-data]  ◄──────────────┤
   uploads / privado          SMB           │
        ▲                                   │
[Container App dfpub-worker]  rol "worker" (continuo)  ── o ──  [Container Apps Job dfpub-worker-job] "worker --once" (cron)
        │
        └─ logs ─► Log Analytics (dfpub-logs, tope diario) ;  imagen desde Azure Container Registry Basic (identidad administrada, AcrPull)
```

Sin Key Vault, sin VNet, sin NAT ni IP pública dedicada, sin punto de conexión privado (Atlas Free no los admite **[V]**, y los de Container Apps añaden cargo de gestión, ver §8). Los secretos son secretos de la Container App (valor entregado al desplegar por canal privado).

## 2. Recursos Azure exactos (infra/main.bicep)

Grupo de recursos nuevo `rg-demand-forecasting-pub` (lo crea el usuario o el integrador con permiso). Región propuesta: **Brazil South (`brazilsouth`)**, la más cercana a Atlas São Paulo **[S]**. **[NV]** La suscripción Azure for Students puede restringir regiones por política: verificar en el portal (Suscripción → Políticas → «Ubicaciones permitidas») o con `az policy assignment list`; si Brazil South no está permitida, elegir la región permitida más cercana (la latencia hacia Atlas aumenta pero el diseño no cambia).

| Recurso | Nombre | SKU / configuración |
|---|---|---|
| Log Analytics workspace | `dfpub-logs` | PerGB2018, retención 30 d, tope diario 0,2 GB |
| Storage account | `dfpubst<8 hex>` | StorageV2, Standard_LRS, TLS 1.2, sin acceso público a blobs |
| File share | `df-data` | SMB, TransactionOptimized, cuota 5 GiB, soft delete 7 d |
| Container Registry | `dfpubacr<hash>` | Basic, sin usuario admin, sin pull anónimo |
| Identidad administrada | `dfpub-id` | rol AcrPull sobre el registro |
| Container Apps Environment | `dfpub-env` | perfil Consumption, logs a `dfpub-logs`, sin VNet |
| Container App API | `dfpub-api` | 0,5 vCPU / 1 GiB, min 1 / max 1 réplica, ingress externo 8000, solo HTTPS, sondeos a `/api/v1/health` |
| Container App worker | `dfpub-worker` | 0,5 vCPU / 1 GiB, min 1 / max 1 (modo `continuous`) |
| (alternativa) Job | `dfpub-worker-job` | Schedule `*/5 * * * *`, `worker --once`, timeout 1800 s, 1 reintento (modo `scheduled`) |

Máximo 1 réplica de la API: el recurso compartido SMB tiene un solo escritor lógico y el límite de login/presupuesto vive en Mongo, así que escalar a más réplicas es técnicamente posible, pero no se necesita y encarece. La validación estática: `bicep build infra/main.bicep` (Bicep 0.48.1) compila sin errores ni advertencias (ver §10); no se ejecutó `what-if` porque requiere sesión.

## 3. Almacenamiento durable (Azure Files frente a efímero)

Container Apps ofrece almacenamiento efímero (se pierde al reiniciar la réplica) y Azure Files (permanente, compartible entre apps y réplicas) **[V]** (https://learn.microsoft.com/en-us/azure/container-apps/storage-mounts, consultado 17/10/2026). Las subidas (`DF_UPLOADS_DIR=/data/uploads`) deben sobrevivir a reemplazos y ser vistas por API y worker, por lo que se usa **Azure Files SMB**. NFS exige VNet personalizada y no admite cifrado en tránsito **[V]**: descartado. Solo se admiten recursos compartidos «clásicos» (en una cuenta de almacenamiento) **[V]**: el Bicep usa ese tipo. La montura SMB usa la clave de la cuenta (secreto del entorno): rotarla tras el despliegue y no registrarla. `mountOptions` fija `uid=10001,gid=10001` para el usuario no root **[NV]** (probar al primer despliegue: si la escritura falla, ajustar las opciones o `file_mode`).

Copias: (1) snapshot del recurso compartido antes de cada cambio (diferencial; costo marginal, **[NV]** precio exacto de snapshots Standard no apareció en la API de precios consultada; verificar en la calculadora); (2) copia de los Excel/archivos privados queda en el equipo del usuario (no se suben a la nube las fuentes originales); (3) Atlas: snapshots diarios, hasta 4 **[V]**, si se activan; (4) exportación `mongodump` de `demand_forecasting_pub` al equipo local antes de cualquier desmontaje.

## 4. Registro de imágenes

Azure Container Registry **Basic**, pull por identidad administrada. La imagen se construye localmente (`docker build`), se etiqueta con un tag inmutable (`t11a-<sha7>`) y se sube **solo tras aprobación del usuario** (`az acr login` + `docker push`; nunca hecho). La imagen no contiene datos, `.env`, `.git` ni artefactos; su tamaño local es 991 MB (el almacenamiento Basic incluye 10 GB **[NV]**; verificar en la página de ACR).

## 5. Logs y retención

Log Analytics con retención 30 d y tope diario 0,2 GB para acotar costo; la API registra con nivel `warning`, sin cuerpos de petición ni secretos (comprobado en el ensayo local: los logs no contienen secretos). Primeros 5 GB/mes de ingesta sin cargo según el escalón de la API de precios **[V]** (inferido de los escalones de tarifa; confirmar en el portal).

## 6. Worker/timer y escala a cero: cómo se procesan los jobs

El worker es un consumidor por sondeo de la colección `jobs` de Mongo: reclama con una operación atómica (CAS), renueva un lease con latidos (config T10: `lease_segundos`, `latido_segundos`) y reintenta si el lease vence. Una API que escala a cero **no** procesa nada; los trabajos esperan en Mongo (persisten). Opciones comparadas:

| Opción | Demora máxima hasta iniciar un trabajo | Costo (ver §9) | Riesgos |
|---|---|---|---|
| A. Worker continuo (réplica mínima 1), API min 1 | ~ el sondeo (segundos) | ~US$22–23/mes de cómputo si está ocioso | simple; costo fijo |
| B. API min 0 + **Job programado** `worker --once` cada 5 min | ≤ 5 min + arranque (~15–30 s) | ~US$7/mes de cómputo (supuestos §9) | la demora es visible para el usuario tras subir; una ejecución larga puede solaparse con la siguiente: es seguro porque el reclamo es atómico y el lease impide doble procesamiento |
| C. Job con escalador KEDA (Mongo) por evento | segundos | similar a B | configuración más compleja y credenciales extra en el escalador; no se elige |
| D. VM / App Service | n.a. | VM B1s ~ costo fijo mayor y administración del SO | más superficie operativa; innecesario |

**Elección propuesta:** A hasta el 23/10/2026 (defensa: sin demora ni arranque en frío; costo ~US$3–5 para 6 días) y cambio a B (`workerMode=scheduled`, `apiMinReplicas=0`) si el sistema queda encendido después. El scheduler (generación periódica) sigue **deshabilitado**; cualquier uso exige `DF_SCHEDULER_ENABLE=true`. Una importación o generación larga no se pierde si el contenedor se reemplaza: el lease vence y otro worker retoma (semántica T10).

## 7. Atlas Free

- Clúster existente `demand-forecasting-dev` (São Paulo). Cuota de datos **512 MB** (incluye índices, sin autoexpansión), 500 conexiones, 100 operaciones/s, 10 GB entrada y 10 GB salida por 7 días, sin peering ni endpoints privados, pausa tras 30 días sin conexiones, un clúster Free por proyecto, nombre de base ≤ 38 bytes **[V]** (https://www.mongodb.com/docs/atlas/reference/free-shared-limitations/, 17/10/2026).
- Base de publicación `demand_forecasting_pub`, usuario de aplicación **nuevo, readWrite solo sobre esa base** (no `atlasAdmin`), credencial generada y entregada por canal privado, rotable. Nunca reutilizar el usuario de desarrollo. Los datos no se restauran en `_v2/_dev`.
- **Tamaño de la base de publicación:** **213,90 MB de datos+índices (41,8 % de 512 MB)** medidos tras restaurar en una base distinta (dbstats/collstats; ver `docs/T11A_INVENTARIO_BD.md` y `docs/T11A_ACTA_RESTAURACION.md`). Margen hasta el 60 %: ≈93 MB (≈2 corridas generadas más; cada corrida generada ≈44,8 MB, histórica ≈42 MB, final ≈37,9 MB). Fórmula de ocupación: `ocupación = (datos_MB + índices_MB) / 512`; objetivo ≤ 60 % ⇒ `datos+índices ≤ 307 MB`; proyección: `ocupación_proyectada = ocupación + n_corridas_nuevas × MB_por_corrida / 512` (MB por corrida generada se mide en local; antes de aprobar el despliegue debe quedar `ocupación_proyectada ≤ 0,6`).
- Lista de acceso IP: sin apertura global (`0.0.0.0/0`) por defecto. Se agrega solo el/los rangos de egreso de Azure del entorno. **[NV]** Los IP de salida de un entorno Consumption sin VNet no son una IP dedicada y pueden cambiar; método: portal → Container Apps Environment → Overview/Properties (IP de salida) y repetir tras cualquier recreación del entorno; cada cambio de IP exige actualizar la lista en Atlas. Si el rango compartido resultara demasiado amplio o inestable, la decisión del usuario es (a) aceptar una apertura temporal `0.0.0.0/0` con fecha de caducidad automática (días) y usuario mínimo con contraseña fuerte, o (b) pagar VNet + NAT con IP fija (ver costo en §9, no incluido). Mientras tanto la apertura global no se activa.
- Atlas Free admite autenticación SCRAM; la conexión usa TLS (`mongodb+srv`). El driver es PyMongo (sin cambios).

## 8. HTTPS, dominio y proxy

HTTPS con el dominio y certificado administrados de la plataforma (`https://dfpub-api.<dominio-del-entorno>`); sin dominio comprado. `allowInsecure=false`. La aplicación fija `ALLOWED_ORIGINS` al origen exacto, cookies `Secure; HttpOnly; SameSite=Strict`, HSTS, CSP y demás cabeceras (probado en local). **X-Forwarded-For:** el ingress de Azure es el único salto; la aplicación confía en la cabecera **solo** si el par TCP directo está en `TRUSTED_PROXIES` y toma la primera IP no confiable desde la derecha. **[NV]** El rango de la IP desde la cual el ingress llega al contenedor no está documentado en las fuentes consultadas. Procedimiento: desplegar con `TRUSTED_PROXIES=""` (seguro: todos los clientes comparten el mismo cupo de login por IP del salto — protege contra fuerza bruta pero un atacante puede agotar el cupo de los demás: riesgo de denegación a aceptar de forma explícita), observar la IP de par con `az containerapp exec` + `ss -tn`, y fijar `TRUSTED_PROXIES` a ese CIDR más estrecho; verificar que cambiar `X-Forwarded-For` no evita el límite (misma prueba del ensayo local).

Cargo «Dedicated Plan Management»: la documentación indica que los endpoints privados y el mantenimiento planificado generan un cargo de gestión incluso en Consumption **[V]** (https://learn.microsoft.com/en-us/azure/container-apps/billing). La API de precios muestra medidores «Environment Management Hour / Private Endpoint / Planned Maintenance» a US$0,2/h con vigencia desde 2026-09-01 (US$0,2 × 720 h ≈ US$144/mes, que consumiría el crédito). Este plan **no** usa endpoints privados ni mantenimiento planificado y no debe habilitarlos; **[NV]** confirmar en la calculadora de precios y en Cost Management tras el primer recurso que el entorno Consumption no genera ese medidor.

## 9. Costo (precios minoristas USD, región `brazilsouth`)

Fuente de tarifas: Azure Retail Prices API, `https://prices.azure.com/api/retail/prices?currencyCode=USD&$filter=serviceName eq '<servicio>' and armRegionName eq 'brazilsouth'`, consultada el 17/10/2026 (la herramienta de lectura resumió el JSON; reverificar en la calculadora oficial antes de aprobar). Cuotas gratuitas mensuales por suscripción de Container Apps Consumption: 180 000 vCPU-s, 360 000 GiB-s, 2 M peticiones **[V]** (https://azure.microsoft.com/en-us/pricing/details/container-apps/ y la página de facturación, 17/10/2026; la página de precios muestra marcadores sin cifras, por eso se usó la API).

| Concepto | Tarifa | Fuente/fecha |
|---|---|---|
| vCPU activa | 0,000024 US$/s | Retail API 17/10/2026 |
| vCPU en reposo (idle) | 0,000003 US$/s | ídem |
| Memoria activa e idle | 0,000003 US$/GiB-s | ídem |
| Peticiones | 0,40 US$/millón (2 M gratis) | ídem |
| Registro Basic | 0,1666 US$/día (≈5,00/mes) | Retail API Container Registry |
| Azure Files Standard LRS (datos) | 0,08175 US$/GB-mes; escritura/lista 0,015 por 10 K; lectura 0,0015 por 10 K | Retail API Storage |
| Log Analytics | primeros 5 GB sin cargo; luego 4,6 US$/GB; retención adicional 0,2 US$/GB-mes | Retail API Log Analytics |
| Atlas Free | US$0 | docs de MongoDB 17/10/2026 |
| Salida de datos Azure, NAT, IP pública | no incluidos; **[NV]** primeros GB de salida mensual gratuitos según la lista de precios de ancho de banda (verificar) | — |

Cómputo (0,5 vCPU / 1 GiB por contenedor; se muestran el valor sin cuotas gratuitas y con ellas valoradas al mínimo, «ocioso» = todo el tiempo en reposo; «activo» = límite superior):

| Escenario | 6 días hasta el 23/10 | Mes de 30 días |
|---|---|---|
| A: API min 1 + worker continuo, ocioso | US$3,05–4,67 | US$21,71–23,33 |
| A: límite superior, todo activo | US$13,93–15,55 | US$76,14–77,76 |
| B: API min 1 + job cada 5 min (30 s/ejecución) | US$1,49–3,11 | US$13,93–15,55 |
| C: API min 0 (2 h activas/día) + job cada 5 min | US$1,00–1,43 | US$5,51–7,13 |

Costo total propuesto hasta el 23/10/2026 (escenario A, ocioso con tráfico de defensa leve): cómputo US$3–5 + registro ≈US$1,0 (6 d) + archivos < US$0,5 + logs US$0 (bajo el tope gratuito, **[NV]**) + Atlas US$0 ⇒ **≈ US$5–7**, con techo prudente de **US$20** si el tráfico fuera todo activo (límite superior A + registro + archivos). Mensual si queda encendido: **A ≈ US$28–30** (cómputo 21,7–23,3 + registro 5,0 + archivos ≈0,5 + logs ≤ 4,6 si superara el gratuito); **C ≈ US$11–13**. Todo se descuenta del crédito (US$100 hasta el 17/10/2027, sin pago por uso). **Presupuestos y alertas no cortan el gasto**: la mitigación real es el tope de réplicas (max 1), el tope de logs, y revisar Cost Management a diario; el desmontaje (§11) es la única forma de detener el cargo.

Mantenimiento fijo no verificado: el costo de egress, de snapshots del share y de operaciones SMB; con las cargas de este proyecto (decenas de MB) se estima despreciable **[S]**.

## 10. Validación estática de la infraestructura

`infra/main.bicep` + `infra/main.parameters.example.json` (sin secretos; `mongodbUri` y `authSecret` son `@secure()` y se pasan en el comando de despliegue desde el canal privado). Ejecutado localmente: Bicep CLI 0.48.1 (descargado a `artifacts/private/t11a/tools/bicep/bicep.exe`, directorio aislado, SHA-256 `398af294cf16ac4becdbd008a77d148d0e8e91492309a6b60ec911b7e1cab082`) — `bicep build infra/main.bicep` y `bicep lint`: **sin errores ni advertencias** (tras eliminar una propiedad inexistente detectada). No se ejecutó `what-if` ni despliegue.

Despliegue en dos fases (propuesto, no ejecutado): (1) `deployApps=false` → registro, almacenamiento, logs, entorno; (2) subir imagen; (3) `deployApps=true` con los secretos.

## 11. Rollback y desmontaje

- Rollback de la aplicación: cada despliegue usa un tag inmutable; revertir = redesplegar el tag anterior (`activeRevisionsMode: Single`; la revisión previa se conserva y se puede reactivar).
- Datos: restaurar el `mongodump` previo en la base de publicación y/o el snapshot del share.
- Desmontaje completo: exportar `mongodump` y el contenido de `df-data` al equipo; `az group delete -n rg-demand-forecasting-pub` (elimina todos los recursos y detiene el cargo); en Atlas, eliminar el usuario de aplicación y las entradas de la lista de acceso. Esta secuencia no se ha ejecutado.

## 12. Cuotas y permisos por verificar (suscripción Azure for Students)

1. Proveedores registrados: `Microsoft.App`, `Microsoft.OperationalInsights`, `Microsoft.ContainerRegistry`, `Microsoft.Storage`, `Microsoft.ManagedIdentity` (`az provider show -n <proveedor> --query registrationState`).
2. Regiones permitidas por política (ver §2) y disponibilidad de Container Apps en la región elegida.
3. Cuota de Container Apps (núcleos por entorno/suscripción en Consumption): verificar en el portal (Suscripción → Uso + cuotas → Microsoft.App). **[NV]** el comando CLI exacto; confirmar con `az containerapp --help`.
4. Permisos del usuario: `Owner` o `Contributor` + `User Access Administrator` sobre el grupo de recursos (para la asignación AcrPull).
5. Saldo de crédito y vigencia (US$100, hasta 17/10/2027): Portal → Cost Management + Billing → Credits (no hay comando de CLI confiable para el saldo de Azure for Students **[NV]**).
6. ¿Azure for Students permite Container Registry Basic y Log Analytics sin tarjeta? Verificar con la creación guiada de `what-if` o la calculadora.

### Herramienta aislada de Azure CLI y autenticación de solo lectura

Sin tocar el entorno Python del proyecto, dos opciones: (a) contenedor oficial `mcr.microsoft.com/azure-cli` con un volumen Docker nombrado para la configuración (`docker run -it --rm -v df-az-config:/root/.azure mcr.microsoft.com/azure-cli`), o (b) ZIP oficial de Azure CLI para Windows extraído a un directorio nuevo y vacío. Ninguna se instaló. Autenticación mínima de solo lectura (cuando el usuario lo apruebe): `az login --use-device-code` (el usuario completa el código en su navegador; sin pegar tokens en el chat), luego únicamente comandos `show`/`list` (`az account show`, `az provider show`, `az policy assignment list`, `az consumption usage list`). Rol requerido: `Reader` (+ `Cost Management Reader` para costos). Cerrar con `az logout` y eliminar el volumen `df-az-config`.

## 13. Accesos mínimos que faltan y decisiones que el usuario debe aprobar

**Accesos faltantes:** (1) inicio de sesión de solo lectura en Azure (device code) para §12; (2) permiso Contributor + UAA sobre un grupo de recursos nuevo; (3) creación en Atlas de un usuario de aplicación mínimo sobre `demand_forecasting_pub` y entrega de su URI por canal privado; (4) lista de acceso IP en Atlas con el/los rangos de egreso (acción del usuario en Atlas); (5) medida del tamaño de la base de publicación (agente de datos) para completar §7.

**Decisiones a aprobar:** (a) crear los recursos de §2 en la región propuesta (o la permitida más cercana); (b) costo máximo autorizado (propuesta: US$20 hasta el 23/10 y US$35/mes si queda encendido); (c) escenario A hasta el 23/10 y paso a C después, o apagar/desmontar el 24/10; (d) política de acceso en Atlas: solo egreso de Azure vs apertura temporal con caducidad vs pagar NAT/VNet; (e) subir la imagen a ACR (primer `docker push`); (f) aceptar el riesgo de límite de login compartido hasta fijar `TRUSTED_PROXIES`; (g) restaurar datos en Atlas solo desde la política de `docs/T11_CONTRATO.md` §4 (sin usuarios, sesiones ni jobs).

Nada de lo anterior se ha ejecutado; cualquier resultado de despliegue en la nube es **pendiente**.
