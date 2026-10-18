# T11 Plan de despliegue (propuesta, NO ejecutada)

Fecha: 17/10/2026; corregido en T11B el 17–18/10/2026. Estado: **propuesta para aprobación**. No se ha creado ningún recurso en la nube, no se ha iniciado sesión en Azure ni en Atlas, no se ha subido ninguna imagen a un registro y no se ha transferido ningún dato fuera de este equipo. Todo lo desplegable fue construido y probado solo en Docker local (ver `docs/T11A_EMPAQUETADO.md`). Los datos son históricos (marzo–agosto 2026); el inventario es simulado.

Convención: **[V]** = verificado en fuente oficial (URL y fecha 17/10/2026); **[NV]** = no verificado, con el método para verificarlo; **[S]** = supuesto de este plan.

## Propuesta principal (T11B)

| Elemento | Propuesta |
|---|---|
| Recursos | Un grupo de recursos nuevo `rg-demand-forecasting-pub`; Container Apps Environment **de solo perfil Consumption** (sin endpoints privados, mantenimiento planificado, VNet, NAT ni perfiles Dedicated); 1 Container App `api` (ingress HTTPS, min 1 / max 1) y 1 Container App `worker` continuo (min 1 / max 1), ambas con la **misma imagen**, 0,5 vCPU / 1 GiB; ACR Basic; Storage Standard LRS con shares `df-data` (subidas, lectura/escritura) y `df-ref` (paquete de referencia, solo lectura, solo worker); Log Analytics con tope diario; identidad administrada con AcrPull. Atlas Free (existente) con usuario de aplicación mínimo. `infra/main.bicep` (compila sin errores). |
| Región | Brazil South (cercana a Atlas São Paulo): **confirmada como permitida** por la política de la suscripción (preflight 18/10/2026). Condicionada a la cuota de Container Apps (ver estado del preflight). |
| Modo | A (worker continuo) hasta el 23/10 para evitar demoras en la defensa; después modo C (API a cero + job cada 5 min, demora máxima ≈ 5 min + arranque) o desmontaje. |
| Recursos probados | Generación real 10/07 H21 por API→job→worker en la imagen con 0,5 vCPU / 1 GiB: 22,2 s, pico 406 MiB, sin OOM (`docs/T11B_GENERACION_CONTENEDOR.md`). Smoke de contenedores 29/29 (T11A). |
| Costo estimado hasta el 23/10 | US$ 4 – 17 (modo A, según idle real; §9.4) más, solo si se cobrara un medidor de gestión de entorno no esperado, hasta US$ 28,8 (§9.3). |
| **Crédito máximo solicitado** | **US$ 20 hasta el 23/10/2026.** |
| Condición de parada | Más de US$ 12 acumulados en Cost Management o cualquier medidor no previsto ⇒ pasar a modo C o eliminar el grupo de recursos el mismo día. El primer recurso es el entorno vacío para detectar temprano el medidor de gestión (pérdida acotada ≈ US$ 0,2/h). |
| Después del curso | 24/10: modo C (≈ US$ 7 – 12/mes) o desmontaje tras exportar el bundle y Mongo; Atlas Free se conserva (US$ 0). |
| Controles reales de gasto | Presupuesto y alertas **no cortan** el gasto; los controles son: 1 réplica máxima por app, tope diario de logs, un solo grupo de recursos eliminable de una vez, revisión de Cost Management a las 24 h y luego a diario, y sin pago por uso (la suscripción de estudiantes se detiene al agotar el crédito). |

**Estado del preflight de Azure (T11B): COMPLETADO (solo lectura) el 18/10/2026.** El usuario completó el inicio de sesión por *device code* en su navegador; se ejecutaron únicamente consultas `show`/`list`/GET (`scripts/azure_preflight.py`; resultado sin identificadores en `artifacts/private/t11b/azure_preflight.json` y `azure_preflight_extra.json`); después se ejecutó `az logout` y se eliminó la caché de sesión. No se creó ni modificó nada, no se registró ningún proveedor, no se asignaron permisos y no se transfirieron datos del proyecto. Resultados:

| Comprobación | Resultado |
|---|---|
| Suscripción / oferta | Habilitada; oferta `AzureForStudents_2018-01-01`; **`spendingLimit = On`** (la suscripción se detiene al agotar el crédito: es el corte real de gasto) |
| Saldo del crédito | No visible por CLI; solo en el portal (verificación puntual del usuario: Cost Management + Billing → Credits) |
| Regiones permitidas (política «Allowed resource deployment regions») | `canadacentral`, `brazilsouth`, `northcentralus`, `westus`, `westus2`; **Brazil South está permitida** (eastus, eastus2, southcentralus y westus3 no lo están) |
| Otras políticas | Exigencia de MFA para escrituras (`Deny`) y auditoría de borrados; bloqueo de West Europe. Las operaciones de escritura del despliegue requerirán una sesión con MFA |
| Permisos propios | Roles `Owner` y `User Access Administrator`; acciones efectivas `*` en la suscripción (basta para el grupo de recursos y la asignación AcrPull) |
| Grupos de recursos existentes | 0 (el despliegue crea el suyo; no hay `what-if` posible sin grupo) |
| Proveedores | `Microsoft.Authorization` Registered; **`Microsoft.App`, `OperationalInsights`, `Storage`, `ContainerRegistry`, `ManagedIdentity` e `Insights` NotRegistered** (el registro es un paso del despliegue; no se hizo) |
| **Cuota de Container Apps** | **`ManagedEnvironmentCount` uso 0 / límite 0 en las 8 regiones consultadas, incluida Brazil South.** Puede deberse al proveedor sin registrar o ser el valor por defecto de Azure for Students; **no se puede distinguir sin registrar el proveedor o abrir una solicitud de cuota**. Es el principal riesgo del plan |
| Cuota de Storage | La consulta falló (`SubscriptionNotFound`) porque `Microsoft.Storage` no está registrado |

**Consecuencia para el plan.** El primer paso real del despliegue pasa a ser (1) registrar `Microsoft.App`, `Microsoft.Storage`, `Microsoft.ContainerRegistry`, `Microsoft.OperationalInsights` y `Microsoft.ManagedIdentity` (sin costo; requiere aprobación explícita) y (2) volver a consultar `ManagedEnvironmentCount`. Si el límite sigue en 0, Container Apps **no está disponible** para esta oferta en esas regiones: contingencia a evaluar con el mismo método de costo (sin aprovisionar) —Azure Container Instances, App Service Linux en Brazil South o una máquina virtual pequeña—; el plan se reabriría con cifras nuevas antes de pedir crédito.

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
| File share de referencia | `df-ref` | SMB, 1 GiB; contiene el paquete de referencia de runtime (CSV/NPZ T07 + manifiesto con anclajes, 7,6 MiB); montado **solo lectura** en `/reference` únicamente en worker/job (`DF_RUNTIME_REFERENCE_DIR=/reference`); la API no lo monta ni lo sirve |
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
| A. Worker continuo (réplica mínima 1), API min 1 | ~ el sondeo (segundos) | US$ 27–30/mes si el worker queda ocioso; hasta ≈ US$ 83/mes si está siempre activo (§9.4) | simple; costo fijo |
| B. API min 0 + **Job programado** `worker --once` cada 5 min | ≤ 5 min + arranque (~15–30 s) | US$ 17–48/mes con API min 1; US$ 7–12/mes con API min 0 (§9.4) | la demora es visible para el usuario tras subir; una ejecución larga puede solaparse con la siguiente: es seguro porque el reclamo es atómico y el lease impide doble procesamiento |
| C. Job con escalador KEDA (Mongo) por evento | segundos | similar a B | configuración más compleja y credenciales extra en el escalador; no se elige |
| D. VM / App Service | n.a. | VM B1s ~ costo fijo mayor y administración del SO | más superficie operativa; innecesario |

**Elección propuesta:** A hasta el 23/10/2026 (defensa: sin demora ni arranque en frío; costo US$ 4–17 para 6 días según el estado real de idle, §9.4) y cambio a B (`workerMode=scheduled`, `apiMinReplicas=0`) si el sistema queda encendido después. El scheduler (generación periódica) sigue **deshabilitado**; cualquier uso exige `DF_SCHEDULER_ENABLE=true`. Una importación o generación larga no se pierde si el contenedor se reemplaza: el lease vence y otro worker retoma (semántica T10).

## 7. Atlas Free

- Clúster existente `demand-forecasting-dev` (São Paulo). Cuota de datos **512 MB** (incluye índices, sin autoexpansión), 500 conexiones, 100 operaciones/s, 10 GB entrada y 10 GB salida por 7 días, sin peering ni endpoints privados, pausa tras 30 días sin conexiones, un clúster Free por proyecto, nombre de base ≤ 38 bytes **[V]** (https://www.mongodb.com/docs/atlas/reference/free-shared-limitations/, 17/10/2026).
- Base de publicación `demand_forecasting_pub`, usuario de aplicación **nuevo, readWrite solo sobre esa base** (no `atlasAdmin`), credencial generada y entregada por canal privado, rotable. Nunca reutilizar el usuario de desarrollo. Los datos no se restauran en `_v2/_dev`.
- **Tamaño de la base de publicación:** **213,90 MB de datos+índices (41,8 % de 512 MB)** medidos tras restaurar en una base distinta (dbstats/collstats; ver `docs/T11A_INVENTARIO_BD.md` y `docs/T11A_ACTA_RESTAURACION.md`). Margen hasta el 60 %: ≈93 MB (≈2 corridas generadas más; cada corrida generada ≈44,8 MB, histórica ≈42 MB, final ≈37,9 MB). Fórmula de ocupación: `ocupación = (datos_MB + índices_MB) / 512`; objetivo ≤ 60 % ⇒ `datos+índices ≤ 307 MB`; proyección: `ocupación_proyectada = ocupación + n_corridas_nuevas × MB_por_corrida / 512` (MB por corrida generada se mide en local; antes de aprobar el despliegue debe quedar `ocupación_proyectada ≤ 0,6`).
- Lista de acceso IP: sin apertura global (`0.0.0.0/0`) por defecto. Se agrega solo el/los rangos de egreso de Azure del entorno. **[NV]** Los IP de salida de un entorno Consumption sin VNet no son una IP dedicada y pueden cambiar; método: portal → Container Apps Environment → Overview/Properties (IP de salida) y repetir tras cualquier recreación del entorno; cada cambio de IP exige actualizar la lista en Atlas. Si el rango compartido resultara demasiado amplio o inestable, la decisión del usuario es (a) aceptar una apertura temporal `0.0.0.0/0` con fecha de caducidad automática (días) y usuario mínimo con contraseña fuerte, o (b) pagar VNet + NAT con IP fija (ver costo en §9, no incluido). Mientras tanto la apertura global no se activa.
- Atlas Free admite autenticación SCRAM; la conexión usa TLS (`mongodb+srv`). El driver es PyMongo (sin cambios).

## 8. HTTPS, dominio y proxy

HTTPS con el dominio y certificado administrados de la plataforma (`https://dfpub-api.<dominio-del-entorno>`); sin dominio comprado. `allowInsecure=false`. La aplicación fija `ALLOWED_ORIGINS` al origen exacto, cookies `Secure; HttpOnly; SameSite=Strict`, HSTS, CSP y demás cabeceras (probado en local). **X-Forwarded-For:** el ingress de Azure es el único salto; la aplicación confía en la cabecera **solo** si el par TCP directo está en `TRUSTED_PROXIES` y toma la primera IP no confiable desde la derecha. **[NV]** El rango de la IP desde la cual el ingress llega al contenedor no está documentado en las fuentes consultadas. Procedimiento: desplegar con `TRUSTED_PROXIES=""` (seguro: todos los clientes comparten el mismo cupo de login por IP del salto — protege contra fuerza bruta pero un atacante puede agotar el cupo de los demás: riesgo de denegación a aceptar de forma explícita), observar la IP de par con `az containerapp exec` + `ss -tn`, y fijar `TRUSTED_PROXIES` a ese CIDR más estrecho; verificar que cambiar `X-Forwarded-For` no evita el límite (misma prueba del ensayo local).

Cargo «Dedicated Plan Management»: la documentación indica que los endpoints privados y el mantenimiento planificado generan un cargo de gestión incluso en Consumption **[V]** (https://learn.microsoft.com/en-us/azure/container-apps/billing). La API de precios muestra medidores «Environment Management Hour / Private Endpoint / Planned Maintenance» a US$0,2/h con vigencia desde 2026-09-01 (US$0,2 × 720 h ≈ US$144/mes, que consumiría el crédito). Este plan **no** usa endpoints privados ni mantenimiento planificado y no debe habilitarlos; **[NV]** confirmar en la calculadora de precios y en Cost Management tras el primer recurso que el entorno Consumption no genera ese medidor.

## 9. Costo (USD, región `brazilsouth`; modelo reproducible `scripts/cost_model.py`)

**Reproducción:** `python -m scripts.azure_prices --region brazilsouth --out artifacts/private/t11b/azure_prices.json` (API pública `https://prices.azure.com/api/retail/prices`, consultada el 18/10/2026 00:37 UTC; precios de lista, sin autenticación) y `python -m scripts.cost_model --days 6`. Las tarifas de la cuenta Azure for Students pueden diferir: se contrastan en la calculadora antes de aprobar.

### 9.1 Tarifas y medidores usados

| Medidor | Tarifa | Fuente / vigencia |
|---|---|---|
| Container Apps Consumption — vCPU activa | 0,000024 US$/s | Retail API, vigente desde 2022-06-01 |
| vCPU en reposo (idle) | 0,000003 US$/s | ídem |
| Memoria activa e idle | 0,000003 US$/GiB-s | ídem |
| Peticiones HTTP (solo externas) | 0,40 US$/millón | ídem |
| **Grants gratuitos Consumption** | 180 000 vCPU-s, 360 000 GiB-s y 2 M peticiones **por suscripción y mes** | https://learn.microsoft.com/en-us/azure/container-apps/billing (ms.date 2025-12-09, consultada 18/10/2026) |
| Jobs en Consumption | siempre tarifa activa; sin idle | ídem |
| Container Registry Basic | 0,1666 US$/día (≈ 5,00/mes); datos almacenados 0,10 US$/GB-mes | Retail API |
| Azure Files Standard LRS | 0,08175 US$/GB-mes; escritura/lista 0,015 y lectura 0,0015 US$ por 10 K operaciones | Retail API (Files) |
| Log Analytics ingestión | primeros 5 GB/mes sin cargo; luego 4,6 US$/GB; retención adicional 0,2 US$/GB-mes | Retail API (tramo 0 → 5 GB a 0,0) |
| Salida a Internet | primeros 100 GB/mes sin cargo; luego 0,12 US$/GB | Retail API (tramo 0 → 100 GB a 0,0) |
| Atlas Free | US$ 0 (512 MB, 100 ops/s, 10 GB/semana) | https://www.mongodb.com/docs/atlas/reference/free-shared-limitations/ |
| Medidores «Environment Management Hour», «Environment Private Endpoint», «Environment Planned Maintenance Hour» | 0,2 US$/h | Retail API, vigentes desde 2026-09-01 (ver 9.3) |

### 9.2 Fórmula

Por contenedor de 0,5 vCPU / 1 GiB encendido `T` segundos con fracción activa `f`: `vCPU-s = 0,5·T` y `GiB-s = 1·T`, de los cuales `f` se factura a tarifa activa y `(1−f)` a tarifa idle. Los **grants se restan una sola vez del total de la suscripción** (API + worker + jobs), no una vez por aplicación; como la documentación no precisa a qué medidor se imputan, el modelo da el rango entre «grants aplicados a lo activo» (mínimo) y «sin grants» (máximo). Jobs: `ejecuciones = días·24·60/5`, `segundos activos = ejecuciones·30` a tarifa activa. Fijos: `ACR = 0,1666·días`, `Files = 0,08175·GB·días/30` (0,5 GB), logs sobre los 5 GB gratuitos (1 GB/30 d previstos ⇒ 0), egreso dentro de los 100 GB gratuitos, Atlas 0.

**Un worker que sondea Mongo no se presume ocioso.** Medición local del worker de la imagen esperando trabajos (120 s, 0,5 vCPU, contra Mongo local sin TLS; `artifacts/private/t11b/idle/worker_ocioso.json`): CPU media **0,0097 vCPU** (umbral de idle `< 0,01`; margen insuficiente), red 174 B/s recibidos y 331 B/s enviados (umbral `< 1000 B/s`). Con TLS, DNS SRV y monitores de topología de Atlas el consumo será mayor; por eso el plan usa `f` ∈ {0, 0,25, 1} para el worker y no afirma el estado idle hasta medirlo en Azure (métricas de Container Apps tras el primer despliegue).

### 9.3 Cargo de gestión de entorno (decisión anclada a la documentación)

La página de facturación (https://learn.microsoft.com/en-us/azure/container-apps/billing) dice textualmente que «features such as private endpoints and planned maintenance are subject to a **Dedicated Plan Management** charge regardless of whether you use the Consumption or Dedicated plans», y que con perfiles Dedicated hay una cuota fija de gestión; para un entorno de **solo perfil Consumption, sin endpoints privados ni mantenimiento planificado**, la página no describe ningún cargo de gestión. Los tres medidores de 0,2 US$/h aparecen en la lista de precios con vigencia desde 2026-09-01, pero ninguno se asocia explícitamente en la documentación con un entorno Consumption sin esas funciones. Decisión: **no se presupuesta como cargo seguro ni se descarta**: el entorno propuesto no habilita endpoints privados, mantenimiento planificado ni perfiles Dedicated (comprobable en el Bicep y en el recurso creado); si apareciera el medidor, su peor caso es 0,2·24·6 = **US$ 28,8** hasta el 23/10 (≈ US$ 144/mes), que superaría el límite pedido. Control: el primer recurso que se crea es el **entorno vacío** (sin apps); se revisa en Cost Management en cuanto aparezca el costo (la facturación puede tardar horas) y, si el medidor se cobra, se elimina el grupo de recursos antes de subir nada (pérdida acotada a horas de gestión, ≈ US$ 0,2/h).

### 9.4 Escenarios (6 días de operación hasta el 23/10; mes de 30 días)

Modo A = API min 1 + worker continuo; B = API min 1 + job `worker --once` cada 5 min (30 s por ejecución, **demora máxima visible de 5 min** más el arranque); C = API min 0 (2 h activas/día) + job cada 5 min. `fa` = fracción activa de la API (0,05–1); `fw` = fracción activa del worker (0–1). Totales = cómputo + ACR + Files + logs.

| Escenario | 6 días hasta el 23/10 | Mes de 30 días |
|---|---|---|
| A, `fa`=0,05, `fw`=0 | US$ 4,06 – 5,95 | US$ 26,75 – 29,73 |
| A, `fa`=1, `fw`=0,25 | US$ 7,08 – 12,48 | US$ 56,99 – 62,39 |
| **A, peor caso (`fa`=1, `fw`=1)** | **US$ 11,16 – 16,56** | US$ 77,40 – 82,80 |
| B, `fa`=0,05 … 1 | US$ 1,96 – 9,56 | US$ 16,55 – 47,81 |
| C | US$ 1,01 – 2,44 | US$ 6,77 – 12,17 |

Con 5 días en lugar de 6 el escenario A baja a US$ 3,11 – 13,80 (peor caso).

### 9.5 Conceptos no determinables (valores conservadores)

| Concepto | Supuesto conservador | Rango |
|---|---|---|
| Operaciones y snapshots de Azure Files | < 0,1 GB de datos activos, < 100 K operaciones/mes, snapshots incrementales de pocos MB | < US$ 0,5 |
| Egreso a Internet | respuestas del frontend/API de decenas de MB | US$ 0 (dentro de 100 GB) |
| Log Analytics | 1 GB/mes previsto, tope diario 0,2 GB | US$ 0 (≤ 5 GB); máx. US$ 4,6/mes si se superara el gratuito |
| Peticiones | < 2 M | US$ 0 |
| Medidor de gestión de entorno | ver 9.3 | US$ 0 – 28,8 hasta el 23/10 |
| IP, NAT, VNet, endpoints privados | no se crean | US$ 0 |

### 9.6 Costo hasta el 23/10 y política posterior

- **Estimado (modo A):** US$ 4 – 17 según el comportamiento real de idle del worker y la API; más, **solo si** el medidor de gestión de entorno se cobrara, hasta US$ 28,8 adicionales (no esperado; ver 9.3).
- **Crédito máximo solicitado hasta el 23/10: US$ 20** (cubre el peor caso A con holgura, sin el medidor de gestión). **Condición de parada:** si Cost Management muestra más de US$ 12 acumulados o aparece cualquier medidor no previsto, se pasa a modo C o se elimina el grupo de recursos el mismo día (`az group delete`; los datos viven en Atlas y en el bundle local).
- **Controles reales:** presupuesto y alertas **no cortan el gasto**; el control efectivo es operativo: (1) 1 réplica máxima en cada app, (2) tope diario de logs, (3) un único grupo de recursos para poder eliminarlo de una vez, (4) revisión de Cost Management a las 24 h del primer recurso y diaria, (5) sin pago por uso: la suscripción de estudiantes se detiene al agotar el crédito.
- **Después del curso:** el 24/10 pasar a modo C (≈ US$ 7 – 12/mes) o desmontar (`az group delete`) tras exportar la copia (bundle + Mongo, ver `docs/T11B_ACTA_RECUPERACION_INTEGRAL.md`); Atlas Free se conserva sin costo (se pausa a los 30 días sin conexiones).

> T11B: la plantilla `infra/main.bicep` fue actualizada (share `df-ref` de solo lectura para worker/job, recursos 0,5 vCPU / 1 GiB probados: la generación real 10/07 H21 en contenedor tuvo un pico de memoria de ≈ 406 MiB y 22 s, sin OOM) y vuelve a compilar sin errores ni advertencias con Bicep 0.48.1.

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

**Accesos faltantes:** (1) inicio de sesión de solo lectura: completado el 18/10/2026 (ver estado del preflight); (2) permiso Contributor + UAA sobre un grupo de recursos nuevo; (3) creación en Atlas de un usuario de aplicación mínimo sobre `demand_forecasting_pub` y entrega de su URI por canal privado; (4) lista de acceso IP en Atlas con el/los rangos de egreso (acción del usuario en Atlas); (5) medida del tamaño de la base de publicación (agente de datos) para completar §7.

**Decisiones a aprobar:** (a) crear los recursos de §2 en la región propuesta (o la permitida más cercana); (b) costo máximo autorizado (propuesta: US$20 hasta el 23/10; después modo C ≈ US$7–12/mes o desmontaje); (c) escenario A hasta el 23/10 y paso a C después, o apagar/desmontar el 24/10; (d) política de acceso en Atlas: solo egreso de Azure vs apertura temporal con caducidad vs pagar NAT/VNet; (e) subir la imagen a ACR (primer `docker push`); (f) aceptar el riesgo de límite de login compartido hasta fijar `TRUSTED_PROXIES`; (g) restaurar datos en Atlas solo desde la política de `docs/T11_CONTRATO.md` §4 (sin usuarios, sesiones ni jobs).

Nada de lo anterior se ha ejecutado; cualquier resultado de despliegue en la nube es **pendiente**.
