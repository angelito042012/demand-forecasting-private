# Preguntas frecuentes para la sustentación

**Preparado:** 2026-11-10 | **Evaluación:** 13/11/2026

---

## Base de datos y despliegue

**¿Qué base de datos usan y por qué?**
MongoDB Atlas (cluster M0 free tier, São Paulo). Elegimos MongoDB porque los datos de ventas tienen esquema variable entre fuentes (14 archivos Excel con formatos distintos) y la estructura de documentos facilita almacenar pronósticos, planes y snapshots de inventario sin migraciones de esquema. Atlas porque ofrece tier gratuito con 512 MB, suficiente para nuestro dataset.

**¿Cuánto pesa la base y cuánto queda disponible?**
135.45 MB de 512 MB usados (26.5%). Contiene 130,747 documentos de ventas (enero–septiembre 2026), 50 productos de inventario reconstruido y sus índices. Queda espacio para ~2 años más de datos al ritmo actual.

**¿Cómo protegen la base de datos?**
- Autenticación con usuario/contraseña (rol readWrite limitado a la base del proyecto)
- Network Access restringido por IP (no 0.0.0.0/0 en producción)
- Conexión cifrada (TLS/SSL obligatorio en Atlas)
- Credenciales en variables de entorno, nunca en código ni en git

**¿Cómo se despliega la aplicación?**
- **Local:** Docker Compose con 4 servicios (API Python/FastAPI, frontend Angular, Caddy como proxy HTTPS, MongoDB)
- **Nube:** Azure Container Apps (API + worker) + Atlas (base de datos) + Caddy (HTTPS gestionado por Azure)
- La imagen Docker se construye desde el repositorio y se sube a Azure Container Registry

**¿Cuánto cuesta mantener esto en producción?**
- Atlas M0: gratis (hasta 512 MB)
- Azure Container Apps: ~$3-5/mes con uso mínimo (1 réplica API + 1 worker)
- Con créditos de estudiante ($100): alcanza para ~20 meses de operación
- Si la empresa asume: el costo es marginal comparado con el beneficio de automatizar la reposición

---

## Modelo y pronóstico

**¿Qué modelo usan y por qué no uno más sofisticado?**
Promedio móvil de 28 días (promedio_28). Evaluamos Random Forest y XGBoost en T06/T07, pero ninguno superó consistentemente al promedio_28 en WAPE para pronóstico a nivel de SKU (RF WAPE 0.93 vs promedio_28 WAPE 0.87 en horizonte 14 días). La razón: con ~270 días de historia y alta variabilidad por SKU, los modelos complejos sobreajustan. El promedio_28 es robusto, interpretable y operativamente más simple.

**¿Cuál es el error del modelo?**
WAPE (Weighted Absolute Percentage Error): 0.37 con origen 31/08, 0.43 con origen 31/07. Esto significa que, en promedio ponderado por volumen, el pronóstico se desvía ~37-43% de la demanda real. Es alto a nivel de SKU individual, pero aceptable a nivel de categoría para una MYPE sin sistema previo.

**¿Por qué no usaron MAPE?**
MAPE es indefinido cuando la demanda real es 0 (división por cero), lo cual ocurre frecuentemente a nivel de SKU. WAPE pondera por volumen y está definido siempre que haya al menos una venta. Reportamos ambos donde es posible, con cobertura explícita.

**¿Qué es la comparación línea base vs resultados?**
Comparamos la política de reposición simulada (pronóstico con datos hasta julio) contra la propuesta (datos hasta octubre) usando el mismo motor de simulación, misma demanda real de septiembre, mismo stock inicial y mismos parámetros. Resultado: fill_rate simulada 0.94 vs propuesta 0.85 (L7). La diferencia se debe únicamente a la ventana de pronóstico — es un ejercicio académico, no evidencia de impacto real.

---

## Datos

**¿De dónde vienen los datos?**
14 archivos Excel de la empresa: 7 de ventas y 7 de compras (marzo–septiembre 2026), más enero–febrero de una importación anterior. Total: 130,747 registros de ventas, 5,006 SKUs, 37 categorías, 9 meses.

**¿Cómo garantizan la calidad de los datos?**
- Validación en importación: `import_operativo preview` verifica formato, tipos y duplicados antes de escribir
- Conciliación: totales del CSV comparados contra Excel original
- Fechas excluidas: 03/04, 12/04 y 07/06 (anomalías identificadas en auditoría)
- TIPO_DOC=7 separado como notas de crédito (no se mezclan con ventas)
- Diccionario de variables documentado (`docs/DICCIONARIO_VARIABLES.md`)

**¿Cómo manejan el inventario?**
Existencia reconstruida a partir de un conteo físico único (18/10/2026, 50 productos). No hay integración en tiempo real con el sistema de la empresa. Limitación documentada: el stock se desactualiza tras el conteo.

---

## Funcionalidad

**¿Qué porcentaje de funcionalidad tiene el sistema?**
13 de 13 requisitos funcionales implementados (100%). Ver `docs/MATRIZ_COBERTURA_REQUISITOS.md`. El sistema permite: importar datos, generar pronósticos, calcular compra recomendada, consultar ventas/inventario/compras por la interfaz web, autenticación con roles, y herramientas de análisis (rotación, comparación de políticas).

**¿Qué no puede hacer el sistema?**
- No se integra automáticamente con el ERP/sistema de la empresa
- No envía alertas (email/WhatsApp)
- No actualiza stock en tiempo real
- No captura estacionalidad (limitación del modelo)
- Ver `docs/LIMITACIONES_Y_MEJORAS.md` para lista completa

---

## Calidad y pruebas

**¿Cuántas pruebas tiene el sistema?**
- Backend/pipeline: 324 tests + 9 scheduler = 333
- Frontend: 280 tests + build
- Navegador (e2e): 25 escenarios
- Seguridad (e2e): 12 verificaciones
- Recálculo independiente: 100 resultados sin diferencias
- Total: ~750 verificaciones

**¿Cómo manejan los defectos?**
Registro formal en `docs/REGISTRO_DEFECTOS.md`: 10 defectos resueltos (cada uno con commit de fix y test de regresión), 3 conocidos no resueltos con mitigación documentada. Cero regresiones introducidas por fixes.

**¿Tienen control de versiones?**
Git con repositorio privado en GitHub. 40+ commits documentados. Cada cambio tiene mensaje descriptivo, autor y fecha. Congelación de evaluación T12 registrada antes del test.

---

## Seguridad y ética

**¿Qué medidas de seguridad implementaron?**
- HTTPS obligatorio (redirect HTTP→HTTPS)
- Sesiones HttpOnly, Secure, SameSite=Strict
- CSRF protection
- Roles: lector (solo consulta) y admin (genera planes, carga datos)
- Credenciales nunca en código (variables de entorno)
- Headers: HSTS, CSP, X-Frame-Options, nosniff

**¿Qué compromisos éticos asumieron?**
- No presentar datos sintéticos como evidencia real
- No fabricar resultados ni impacto empresarial
- Separar hechos de supuestos en toda la documentación
- No manipular la evaluación T12 post-facto
- Datos de la empresa tratados como confidenciales
- Cada integrante escribe su propio compromiso ético

---

## Preguntas difíciles que podrían hacer

**"¿Por qué el fill_rate propuesto es MENOR que el simulado?"**
Porque la ventana propuesta (origen octubre) tiene menos datos históricos que la simulada (origen julio, que incluye meses de alta actividad). Es contraintuitivo pero coherente: un pronóstico con más historia captura mejor el patrón. La comparación es justa porque controla todas las variables excepto la ventana.

**"¿Realmente le sirve esto a la empresa?"**
El sistema provee una herramienta que la empresa no tenía: pronóstico cuantitativo por producto y recomendación de compra con escenarios. Sin embargo, no podemos medir impacto real sin datos operativos de noviembre y validación de la política de reposición. Lo documentamos como propuesta, no como resultado validado.

**"¿Por qué no activaron el scheduler?"**
Porque requiere una fuente de stock estable y actualizada. Sin un compromiso de la empresa de entregar datos periódicos, el scheduler regeneraría el mismo plan con datos desactualizados. Está implementado, testeado (9/9) y documentado, listo para activar cuando la condición se cumpla.

**"¿Qué pasa si la credencial de Atlas se filtra?"**
Tenemos un procedimiento documentado de 4 pasos para rotarla (`docs/PROCEDIMIENTO_ROTACION_CREDENCIAL.md`). La migración a credenciales propias de Milton ya se ejecutó, lo cual efectivamente rota la credencial operativa.
