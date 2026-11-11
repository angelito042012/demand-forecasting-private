# Evidencias de mejora tecnica

**Fecha:** 2026-11-11
**Proyecto:** Sistema de prevision de demanda y compras — Capstone
**Evaluacion:** 13/11/2026

---

## 1. Resumen ejecutivo

El sistema paso de un prototipo funcional (entrega 23/10/2026) a una plataforma modular,
documentada y desplegada en la nube. Se realizaron 178 commits desde octubre, cubriendo
reestructuracion del frontend, extension del pipeline operativo, nuevos scripts de operacion,
documentacion formal de calidad y despliegue en Azure Container Apps.

| Metrica | Antes (23/10) | Despues (11/11) | Cambio |
|---|---|---|---|
| Archivos en `frontend/src/app/core/` | 14 archivos planos | 5 subdirectorios (guards, interceptors, models, services, utils) + barrels | Modularizado |
| Componentes UI | `app/ui/` (11 archivos sueltos) | `app/shared/components/` con barrel index | Reorganizado |
| Modelos TypeScript | 1 archivo monolitico (`models.ts`, 634 lineas) | 13 archivos por dominio (backtest, forecast, plan, run, etc.) | Separacion de responsabilidades |
| Servicios API | 1 archivo (`api.service.ts`, ~300 lineas) | 10 servicios especializados + clase base | Responsabilidad unica |
| Tests unitarios | ~500 | ~500 (actualizados a nueva estructura) | Mantenidos |
| Documentos de evidencia | ~80 | 115+ | +35 documentos |
| Scripts operativos | 0 (solo pipeline) | 4 (`import_operativo`, `convert_ene_feb`, `import_directo`, `calc_rotation`) | Operacion sin mongorestore |
| Despliegue | Solo local (Docker Compose) | Azure Container Apps + Atlas | Produccion en nube |

## 2. Reestructuracion del frontend (commit `db3c45f`)

### 2.1 Problema

El frontend tenia una estructura plana en `core/` con 14+ archivos de distintas responsabilidades
mezclados: modelos, servicios, guards, interceptors y utilidades en el mismo directorio.
El archivo `models.ts` era un monolito de 634 lineas con todas las interfaces del sistema.

### 2.2 Solucion

Reorganizacion a estructura modular con separacion por responsabilidad:

```
frontend/src/app/core/
  guards/          -- auth.guard.ts, role.guard.ts, index.ts
  interceptors/    -- http.interceptor.ts, demo.ts, index.ts
  models/          -- 13 archivos por dominio (backtest, forecast, plan, ...)
  services/        -- 10 servicios especializados + api-base.ts
  utils/           -- age, errors, format, load, reco-calc, ux-text, wide-main
frontend/src/app/shared/
  components/      -- 11 componentes UI con barrel index
  directives/
  pipes/
  styles/          -- _variables.scss, _mixins.scss, index.scss
frontend/src/environments/
  environment.ts, environment.prod.ts
```

### 2.3 Evidencia

- **136 archivos** modificados en el commit `db3c45f`
- **3,169 inserciones / 1,610 eliminaciones**
- Git detecto correctamente los renames (auth.guard, http.interceptor, etc.)
- Barrel exports (`index.ts`) en cada subdirectorio para imports limpios
- Todos los tests actualizados y compilando (`app.spec.ts`, `core.spec.ts`, etc.)

### 2.4 Mejoras adicionales del frontend

| Mejora | Archivo | Descripcion |
|---|---|---|
| PostCSS + Tailwind | `.postcssrc.json`, `angular.json` | Configuracion de PostCSS con Tailwind y autoprefixer |
| Variables SCSS | `shared/styles/_variables.scss` | Tokens de diseno centralizados |
| Mixins reutilizables | `shared/styles/_mixins.scss` | Patrones CSS compartidos |
| Environments | `environments/environment.ts` | Configuracion por entorno (dev/prod) |
| Package updates | `package.json` | Actualizacion de dependencias Angular |

## 3. Extension del pipeline operativo

### 3.1 Calendario y ventana de entrenamiento

| Archivo | Cambio | Proposito |
|---|---|---|
| `pipeline/data/calendar.py` | Extender fechas hasta 2026-09-30 | Cubrir datos de septiembre |
| `pipeline/data/training_access.py` | Ajustar ventana de entrenamiento | Incluir ventas hasta septiembre |
| `pipeline/generate/config.py` | Actualizar constantes de generacion | Alinear con nuevo calendario |
| `pipeline/generate/validate.py` | Ajustar validaciones | Aceptar rango extendido |
| `pipeline/generate/baseline.py` | Alinear baseline | Consistencia con calendario |

### 3.2 Publicacion y esquema

| Archivo | Cambio |
|---|---|
| `pipeline/publish/builders.py` | Ajuste de formato en constructores |
| `pipeline/publish/schema.py` | Actualizacion de version de esquema |
| `pipeline/publish/source.py` | Limpieza de formato de fuentes |

## 4. Backend: limpieza de la capa de datos

| Archivo | Cambio |
|---|---|
| `backend/app/data/common.py` | Limpieza de imports |
| `backend/app/data/inventory.py` | Formato y organizacion |
| `backend/app/data/observed.py` | Formato consistente |
| `backend/app/data/plan.py` | Limpieza de imports |
| `backend/app/data/stock.py` | Formato consistente |

## 5. Nuevos scripts operativos

| Script | Commit | Proposito |
|---|---|---|
| `scripts/import_operativo.py` | `114efcd` | CLI de importacion de ventas y stock sin mongorestore |
| `scripts/convert_ene_feb.py` | `db3c45f` | Conversion de Excel "Ventas detalladas" al formato estandar |
| `scripts/import_directo.py` | `db3c45f` | Importacion directa a Atlas sin cola de jobs |
| `scripts/calc_rotation.py` | (backlog T9) | Calculo de indicador de rotacion de inventario |
| `scripts/compare_policies.py` | (backlog T8) | Comparacion de politica simulada vs propuesta |

## 6. Documentacion de calidad agregada

| Documento | Fecha | Contenido |
|---|---|---|
| `REGISTRO_DEFECTOS.md` | 10/11 | 10 defectos resueltos + 3 conocidos con severidad y commits |
| `MATRIZ_COBERTURA_REQUISITOS.md` | 10/11 | 13 RF + 7 RNF mapeados a modulos, pruebas y evidencia |
| `MATRIZ_RIESGOS_ACTUALIZADA.md` | 10/11 | 7 riesgos tecnicos + 5 de proyecto + 6 cerrados |
| `LIMITACIONES_Y_MEJORAS.md` | 10/11 | Limitaciones por area + mejoras futuras priorizadas |
| `GUIA_PRUEBAS_V3.md` | 10/11 | Guia completa de pruebas y traspaso v3 |
| `DEPLOY_AZURE.md` | 11/11 | Guia paso a paso de despliegue en Azure Container Apps |
| `QA_SUSTENTACION.md` | 11/11 | Preguntas y respuestas preparadas para la sustentacion |
| `T13C_REVISION_INDEPENDIENTE.md` | 06/11 | Revision de coherencia codigo-documentacion post-T12 |
| `T13D_ACTA_RECORRIDO.md` | 06/11 | Acta del recorrido de aceptacion humana |
| `DICCIONARIO_VARIABLES.md` | 06/11 | Diccionario de constantes parametrizadas del pipeline |

## 7. Correccion de defectos tecnicos

| Defecto | Severidad | Commit | Descripcion |
|---|---|---|---|
| D01–D03 | Alta | `a728017`, `f0bae1d`, `462e7f5` | Publicacion de plan: relevo, purga y error ambiguo |
| D04 | Media | `667828b` | Pantalla usaba mocks en vez de datos del plan real |
| D05 | Media | `616b5ef` | Importador no verificaba CSV contra Excel original |
| D06 | Baja | `1ae03cb` | TypeError en `coverage_days()` con valor None |
| D07 | Media | Sesion | `cantidad` como string en MongoDB causaba `$sum` = 0 |
| D10 | Baja | `7e6b557` | Formato alternativo de Excel no reconocido |

## 8. Despliegue en nube

| Componente | Tecnologia | Estado |
|---|---|---|
| API + Worker | Azure Container Apps | Desplegado (imagen `v7`, revision `capstone-api--0000007`, 11/11/2026) |
| Base de datos | MongoDB Atlas (Free Tier, 512 MB) | Operativo (~246 MB) |
| Registro de imagenes | Azure Container Registry | Configurado |
| Proxy HTTPS | Caddy (local) / Azure managed (nube) | Configurado |
| Documentacion | `docs/DEPLOY_AZURE.md` | Completa |

## 9. Mejora en pruebas

| Area | Archivos actualizados | Motivo |
|---|---|---|
| Backend API | `test_data_api.py`, `test_t10_api.py`, `test_t11_final_api.py` | Esquemas actualizados |
| Operaciones | `test_t10_chain.py` | Imports por nueva estructura |
| Frontend | 15+ archivos `.spec.ts` | Imports actualizados por modularizacion |
| Config | `t10_config.json` | Alineacion con pipeline extendido |

## 10. Metricas de cambio acumuladas

```
Commits desde 01/10/2026:        178
Archivos en ultimo refactoring:  136
Documentos de evidencia nuevos:  ~35
Defectos corregidos:             10
Defectos conocidos:              3
Scripts operativos nuevos:       5
Requisitos funcionales cubiertos: 13/13
Requisitos no funcionales:       7/7
```

---

**Referencia:** commits en `github.com/angelito042012/demand-forecasting-private`, branch `master`.
