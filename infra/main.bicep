// T11A - Infraestructura declarativa PARAMETRIZADA para revision estatica. NO DESPLEGADA. No crea nada por si sola.
// Alcance: grupo de recursos existente (az deployment group create ...). Ver docs/T11_PLAN_DESPLIEGUE.md.
// Fase 1: deployApps=false (registro, almacenamiento, logs, entorno). Luego se sube la imagen (accion del usuario).
// Fase 2: deployApps=true (API y worker/job). Los secretos entran como parametros @secure() por canal privado.
targetScope = 'resourceGroup'

@description('Region de despliegue. Debe estar permitida por la politica de la suscripcion Azure for Students (verificar).')
param location string = 'brazilsouth'

@description('Prefijo corto en minusculas para nombres de recursos.')
@minLength(3)
@maxLength(12)
param prefix string = 'dfpub'

@description('Etiqueta de imagen en el registro (use un tag inmutable, p. ej. t11a-<sha7>).')
param imageTag string = 't11a-local'

@description('Despliega las aplicaciones (requiere que la imagen ya exista en el registro).')
param deployApps bool = false

@description('continuous = worker como app con 1 replica; scheduled = job programado con "worker --once".')
@allowed(['continuous', 'scheduled'])
param workerMode string = 'continuous'

@description('Cron del job programado (UTC) cuando workerMode=scheduled.')
param workerCron string = '*/5 * * * *'

@description('Replicas minimas de la API: 1 evita el arranque en frio durante la defensa; 0 escala a cero.')
@allowed([0, 1])
param apiMinReplicas int = 1

@description('Cuota del recurso compartido de archivos en GiB.')
@minValue(1)
@maxValue(100)
param shareQuotaGiB int = 5

@description('Dias de retencion de logs (30 incluidos segun la tabla de precios; verificar en el portal).')
@minValue(30)
@maxValue(90)
param logRetentionDays int = 30

@description('Tope diario de ingesta de logs en GB (acota el costo).')
param logDailyCapGb string = '0.2'

@description('Monta Azure Files en data/reference. false = entornos "express" (T20, 22/10/2026: Azure for Students crea un entorno que NO admite Storage): /data efimero; no se usa la referencia historica T07.')
param useFiles bool = false

@description('Nombre de la base de publicacion en Atlas (no es secreto).')
param mongodbDatabase string = 'demand_forecasting_pub'

@description('IP/CIDR del salto de proxy de confianza para X-Forwarded-For. Vacio = no se confia (seguro, limite global por salto).')
param trustedProxies string = ''

@secure()
@description('URI de Atlas con usuario de aplicacion minimo; se entrega por canal privado. No va en archivos.')
param mongodbUri string = ''

@secure()
@description('Pimienta de limites de acceso (>= 32 caracteres, generada al desplegar).')
param authSecret string = ''

var unique = uniqueString(resourceGroup().id)
var tags = {
  project: 'demand-forecasting'
  task: 't11a'
  data: 'sintetico-y-historico-no-pronostica-octubre'
}
var acrName = toLower('${prefix}acr${unique}')
var storageName = toLower('${prefix}st${take(unique, 8)}')
var shareName = 'df-data'
var apiName = '${prefix}-api'
var workerName = '${prefix}-worker'
var imageRef = '${acr.properties.loginServer}/demand-forecasting:${imageTag}'
var appHost = '${apiName}.${env.properties.defaultDomain}'

resource logs 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: '${prefix}-logs'
  location: location
  tags: tags
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: logRetentionDays
    workspaceCapping: { dailyQuotaGb: json(logDailyCapGb) }
  }
}

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageName
  location: location
  tags: tags
  kind: 'StorageV2'
  sku: { name: 'Standard_LRS' }
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    supportsHttpsTrafficOnly: true
    allowSharedKeyAccess: true // Container Apps (SMB) monta con clave de cuenta; se rota tras el despliegue
    publicNetworkAccess: 'Enabled'
  }
}

resource files 'Microsoft.Storage/storageAccounts/fileServices@2023-05-01' = {
  parent: storage
  name: 'default'
  properties: {
    shareDeleteRetentionPolicy: { enabled: true, days: 7 }
  }
}

resource share 'Microsoft.Storage/storageAccounts/fileServices/shares@2023-05-01' = {
  parent: files
  name: shareName
  properties: {
    shareQuota: shareQuotaGiB
    enabledProtocols: 'SMB'
    accessTier: 'TransactionOptimized'
  }
}

// Paquete de referencia de runtime (T11B R14): CSV/NPZ T07 + manifiesto con anclajes; montaje de SOLO LECTURA en el worker.
resource shareRef 'Microsoft.Storage/storageAccounts/fileServices/shares@2023-05-01' = {
  parent: files
  name: 'df-ref'
  properties: {
    shareQuota: 1
    enabledProtocols: 'SMB'
  }
}

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  tags: tags
  sku: { name: 'Basic' }
  properties: {
    adminUserEnabled: false
  }
}

resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${prefix}-id'
  location: location
  tags: tags
}

// AcrPull = 7f951dda-4ed3-4680-a7ca-43fe172d538d
resource acrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: acr
  name: guid(acr.id, identity.id, 'acrpull')
  properties: {
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
  }
}

resource env 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${prefix}-env'
  location: location
  tags: tags
  properties: {
    workloadProfiles: [{ name: 'Consumption', workloadProfileType: 'Consumption' }]
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logs.properties.customerId
        sharedKey: logs.listKeys().primarySharedKey
      }
    }
  }
}

resource envStorage 'Microsoft.App/managedEnvironments/storages@2024-03-01' = if (useFiles) {
  parent: env
  name: 'dfdata'
  properties: {
    azureFile: {
      accountName: storage.name
      accountKey: storage.listKeys().keys[0].value
      shareName: share.name
      accessMode: 'ReadWrite'
    }
  }
}

resource envStorageRef 'Microsoft.App/managedEnvironments/storages@2024-03-01' = if (useFiles) {
  parent: env
  name: 'dfref'
  properties: {
    azureFile: {
      accountName: storage.name
      accountKey: storage.listKeys().keys[0].value
      shareName: shareRef.name
      accessMode: 'ReadOnly'
    }
  }
}

var commonEnv = [
  { name: 'APP_ENV', value: 'production' }
  { name: 'APP_TIMEZONE', value: 'America/Lima' }
  { name: 'MONGODB_DATABASE', value: mongodbDatabase }
  { name: 'MONGODB_URI', secretRef: 'mongodb-uri' }
  { name: 'AUTH_SECRET', secretRef: 'auth-secret' }
  { name: 'ALLOWED_ORIGINS', value: 'https://${appHost}' }
  { name: 'TRUSTED_PROXIES', value: trustedProxies }
  { name: 'DF_UPLOADS_DIR', value: useFiles ? '/data/uploads' : '/tmp/uploads' }
]
var commonSecrets = [
  { name: 'mongodb-uri', value: mongodbUri }
  { name: 'auth-secret', value: authSecret }
]
var registryConfig = [{ server: acr.properties.loginServer, identity: identity.id }]
var volumes = !useFiles ? [] : [
  {
    name: 'data'
    storageType: 'AzureFile'
    storageName: 'dfdata'
    // el contenedor corre como uid 10001; sin esto la montura SMB seria de root
    mountOptions: 'uid=10001,gid=10001,file_mode=0660,dir_mode=0770,nobrl'
  }
]
var volumeMounts = useFiles ? [{ volumeName: 'data', mountPath: '/data' }] : []
// el worker/job monta ademas el paquete de referencia (solo lectura); la API NO lo monta
var refVolume = {
  name: 'reference'
  storageType: 'AzureFile'
  storageName: 'dfref'
  mountOptions: 'uid=10001,gid=10001,file_mode=0440,dir_mode=0550,nobrl'
}
var workerVolumes = useFiles ? concat(volumes, [refVolume]) : volumes
var workerMounts = useFiles ? concat(volumeMounts, [{ volumeName: 'reference', mountPath: '/reference' }]) : volumeMounts
var workerEnv = useFiles ? concat(commonEnv, [{ name: 'DF_RUNTIME_REFERENCE_DIR', value: '/reference' }]) : commonEnv

resource api 'Microsoft.App/containerApps@2024-03-01' = if (deployApps) {
  name: apiName
  location: location
  tags: tags
  identity: { type: 'UserAssigned', userAssignedIdentities: { '${identity.id}': {} } }
  dependsOn: [acrPull]
  properties: {
    managedEnvironmentId: env.id
    workloadProfileName: 'Consumption'
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
        allowInsecure: false // solo HTTPS con el certificado de la plataforma
      }
      registries: registryConfig
      secrets: commonSecrets
    }
    template: {
      containers: [
        {
          name: 'api'
          image: imageRef
          args: ['api']
          resources: { cpu: json('0.5'), memory: '1Gi' }
          env: commonEnv
          volumeMounts: volumeMounts
          probes: [
            { type: 'Liveness', httpGet: { path: '/api/v1/health', port: 8000 }, periodSeconds: 30, failureThreshold: 3, initialDelaySeconds: 20 }
            { type: 'Readiness', httpGet: { path: '/api/v1/health', port: 8000 }, periodSeconds: 15 }
          ]
        }
      ]
      volumes: volumes
      scale: { minReplicas: apiMinReplicas, maxReplicas: 1 } // 1 replica maxima: un solo escritor del recurso compartido
    }
  }
}

resource worker 'Microsoft.App/containerApps@2024-03-01' = if (deployApps && workerMode == 'continuous') {
  name: workerName
  location: location
  tags: tags
  identity: { type: 'UserAssigned', userAssignedIdentities: { '${identity.id}': {} } }
  dependsOn: [acrPull]
  properties: {
    managedEnvironmentId: env.id
    workloadProfileName: 'Consumption'
    configuration: {
      activeRevisionsMode: 'Single'
      registries: registryConfig
      secrets: commonSecrets
    }
    template: {
      containers: [
        {
          name: 'worker'
          image: imageRef
          args: ['worker']
          resources: { cpu: json('0.5'), memory: '1Gi' } // medido en contenedor (T11B): generacion 10/07 H21 pico ~406 MiB de 1 GiB sin OOM
          env: workerEnv
          volumeMounts: workerMounts
        }
      ]
      volumes: workerVolumes
      scale: { minReplicas: 1, maxReplicas: 1 }
    }
  }
}

resource workerJob 'Microsoft.App/jobs@2024-03-01' = if (deployApps && workerMode == 'scheduled') {
  name: '${prefix}-worker-job'
  location: location
  tags: tags
  identity: { type: 'UserAssigned', userAssignedIdentities: { '${identity.id}': {} } }
  dependsOn: [acrPull]
  properties: {
    environmentId: env.id
    workloadProfileName: 'Consumption'
    configuration: {
      triggerType: 'Schedule'
      replicaTimeout: 1800
      replicaRetryLimit: 1
      scheduleTriggerConfig: { cronExpression: workerCron, parallelism: 1, replicaCompletionCount: 1 }
      registries: registryConfig
      secrets: commonSecrets
    }
    template: {
      containers: [
        {
          name: 'worker-once'
          image: imageRef
          args: ['worker-once']
          resources: { cpu: json('0.5'), memory: '1Gi' }
          env: workerEnv
          volumeMounts: workerMounts
        }
      ]
      volumes: workerVolumes
    }
  }
}

output registryLoginServer string = acr.properties.loginServer
output appUrl string = 'https://${appHost}'
output environmentDefaultDomain string = env.properties.defaultDomain
output outboundIpsNote string = 'Consulte las IP de salida del entorno en el portal (Container Apps Environment > Properties) para la lista de acceso de Atlas.'
