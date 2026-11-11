# Pendientes del equipo para la evaluacion del 13/11/2026

**Fecha:** 11/11/2026
**Evaluacion:** 13/11/2026 (quedan 2 dias)
**Repo:** `github.com/angelito042012/demand-forecasting-private` (branch `master`)

---

## Estado actual

Todo el codigo, documentacion tecnica y despliegue estan listos:

- 115+ documentos de evidencia en `docs/`
- Deploy en Azure Container Apps (imagen v5, revision `capstone-api--0000005`)
- URL publica: `https://capstone-api.icypebble-fc2fe1de.brazilsouth.azurecontainerapps.io`
- Atlas Network Access configurado (temporal 1 semana)
- 13/13 requisitos funcionales implementados, 7/7 no funcionales cumplidos
- Ultimo commit: `13613df` (11/11/2026)

---

## 1. VIDEO DE SUSTENTACION (critico, 95% de la nota)

**Estado:** Guion listo, falta grabar y subir.
**Archivo:** `docs/GUION_VIDEO.md`
**Duracion:** Maximo 10 minutos (3 teoria + 7 producto)

### Estructura del video

| Tiempo | Bloque | Contenido |
|---|---|---|
| 0:00–0:30 | Apertura | Titulo, autor, problema en una frase |
| 0:30–3:00 | Teoria | Datos (6 Excel, mar-ago), metodo (promedio_28, RF comparador), evaluacion (WAPE, limites) |
| 3:00–3:30 | Producto: Inicio | Login, barra de analisis, menu principal |
| 3:30–4:15 | Producto: Mis analisis | Tarjetas, seleccionar analisis, versiones |
| 4:15–5:15 | Producto: Ventas previstas | Buscar producto, comparar metodos |
| 5:15–6:30 | Producto: Reposicion | Aviso de inventario simulado, sugerencias, calculo |
| 6:30–7:30 | Producto: Evaluacion | Error del promedio, detalle academico, simulacion |
| 7:30–8:30 | Producto: Evaluacion agosto | Advertencias, bloque de 21 dias |
| 8:30–9:30 | Producto: Admin | Cargar datos, crear analisis |
| 9:30–10:00 | Cierre | Resumen honesto, pendientes, que no se concluye |

### Que mostrar en el video

- **Ejecucion local** (Docker Compose) o la URL de Azure si Atlas sigue activo
- **NO** mostrar credenciales, `.env`, ni tokens
- **NO** afirmar mejora real ni impacto empresarial medido
- Cifras de referencia: WAPE SKU 0.78 (T12), WAPE categoria 0.12 (T12)
- Mencionar que el inventario es **simulado con supuestos**

### Quien y cuando

- **Todos** deben participar o al menos uno graba y narra
- **Fecha limite:** 12/11 para grabar, 13/11 a primera hora para subir
- Subir a YouTube/Drive y pegar el enlace en la entrega

---

## 2. ARTICULO CIENTIFICO (version inicial)

**Estado:** No existe. Hay que redactarlo.
**Insumos disponibles en el repo:**

| Seccion del articulo | Donde encontrar el contenido |
|---|---|
| Introduccion / problema | `docs/INFORME_FINAL_BORRADOR.md` §1-2 |
| Metodologia | `docs/MODELOS_Y_METODO_OPERATIVO.md`, `docs/T12_PROTOCOLO.md` |
| Resultados | `docs/T12_RESULTADOS.md`, `docs/HECHOS_PARA_INFORME_ACADEMICO.md` |
| Discusion / limitaciones | `docs/LIMITACIONES_Y_MEJORAS.md` |
| Conclusiones | `docs/INFORME_FINAL_BORRADOR.md` §12 |
| Referencias | `docs/INFORME_FINAL_BORRADOR.md` (pendientes de verificar) |

### Estructura sugerida (4-6 paginas)

1. **Titulo:** Sistema de prevision de demanda para una MYPE de cuidado personal
2. **Resumen / Abstract** (200 palabras)
3. **Introduccion:** problema, objetivos, justificacion
4. **Metodologia:** datos (6 Excel, mar-sep 2026), particion temporal, promedio_28 vs RF vs cero
5. **Resultados:** WAPE, MAPE con cobertura, simulacion de reposicion, metricas T12
6. **Discusion:** limitaciones (datos censurados, inventario simulado, sin impacto real medido)
7. **Conclusiones y trabajo futuro**
8. **Referencias**

### Quien

- Repartir secciones entre los miembros del equipo
- **Fecha limite:** borrador para el 12/11, revision cruzada el 13/11

---

## 3. INFORME FINAL DOCX (consolidado)

**Estado:** Borrador parcial en `documentacion/Informe_Capstone_0911.docx`
**Borrador MD:** `docs/INFORME_FINAL_BORRADOR.md`

### Secciones que faltan completar o integrar

| Seccion | Fuente en el repo | Accion |
|---|---|---|
| Capitulo de metodologia | `docs/MODELOS_Y_METODO_OPERATIVO.md` | Integrar en formato de informe |
| Capitulo VII: resultados operativos/economicos | `docs/T12_RESULTADOS.md`, `docs/EVALUACION_T06_T07_METRICAS.md` | Redactar narrativa + tablas |
| Analisis costo-beneficio | `docs/T11_PLAN_DESPLIEGUE.md` (costos Azure estimados) | Formatear como seccion formal |
| Limitaciones y mejoras futuras | `docs/LIMITACIONES_Y_MEJORAS.md` | Copiar y dar formato |
| Evidencia de despliegue | `docs/DEPLOY_AZURE.md`, `docs/EVIDENCIAS_MEJORA_TECNICA.md` | Parrafo + capturas |
| Compromiso etico | Redactar (cada miembro firma) | Nuevo |
| Anexos | Matrices, reportes de prueba | Referenciar los MD |

### Quien

- Un miembro consolida el DOCX, otros revisan secciones asignadas
- **Fecha limite:** version completa el 12/11

---

## 4. EVIDENCIAS YA LISTAS (solo revisar)

Estos documentos **ya existen** en `docs/` y cubren los requisitos del profesor:

| Requisito del profesor | Documento |
|---|---|
| Registro de cambios | `git log`, `docs/ESTADO.md` |
| Evidencias de mejora tecnica | `docs/EVIDENCIAS_MEJORA_TECNICA.md` |
| Reporte de pruebas | `docs/GUIA_PRUEBAS_V3.md`, `docs/T12_RESULTADOS.md` |
| Matriz de cobertura de requisitos | `docs/MATRIZ_COBERTURA_REQUISITOS.md` |
| Registro de defectos | `docs/REGISTRO_DEFECTOS.md` |
| Matriz de riesgos actualizada | `docs/MATRIZ_RIESGOS_ACTUALIZADA.md` |
| Revision SQA | `docs/T13C_REVISION_INDEPENDIENTE.md` |
| Control de versiones | GitHub (`master`), 180+ commits |
| Despliegue | `docs/DEPLOY_AZURE.md`, Azure Container Apps operativo |
| Limitaciones y mejoras | `docs/LIMITACIONES_Y_MEJORAS.md` |
| Plan de calidad | `docs/GUIA_PRUEBAS_V3.md`, `docs/PLAN_CALIDAD.md` (si existe) |
| Evaluacion de indicadores | `docs/INDICADOR_ROTACION.md`, `docs/T12_RESULTADOS.md` |
| Comparacion linea base vs resultados | `docs/T12_RESULTADOS.md`, `docs/EVALUACION_T06_T07_METRICAS.md` |

---

## 5. DISTRIBUCION SUGERIDA DE TRABAJO

| Miembro | Tarea principal | Tarea secundaria |
|---|---|---|
| Miembro 1 | Grabar video (narrador) | Revisar DOCX |
| Miembro 2 | Articulo cientifico (intro + metodologia) | Apoyar video (diapositivas) |
| Miembro 3 | Articulo cientifico (resultados + discusion) | Consolidar DOCX |
| Miembro 4 | DOCX informe final (cap VII + costo-beneficio) | Revisar articulo |

Ajustar segun el numero real de integrantes.

---

## 6. CHECKLIST FINAL (13/11)

- [ ] Video grabado y subido (enlace listo)
- [ ] Articulo cientifico version inicial (PDF o DOCX)
- [ ] Informe final DOCX consolidado con todas las secciones
- [ ] Compromiso etico firmado por cada miembro
- [ ] Verificar que la URL de Azure responde: `https://capstone-api.icypebble-fc2fe1de.brazilsouth.azurecontainerapps.io/api/v1/health`
- [ ] Repositorio GitHub actualizado con ultimos cambios
- [ ] ZIP del repo enviado si el profesor lo requiere

---

**Contacto:** Si tienen dudas tecnicas sobre el codigo o los documentos, revisar primero
`docs/ESTADO.md` y `docs/BACKLOG.md`. Para el video, seguir el guion en `docs/GUION_VIDEO.md`.
