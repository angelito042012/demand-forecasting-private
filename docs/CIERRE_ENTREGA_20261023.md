# Cierre de la entrega para la exposición del 23/10/2026 (19:30 Lima)

**Estado: NO es un cierre total.** Faltan la rotación y comprobación de la credencial de Atlas y la aceptación final de Rogelio (la prueba administrativa «Generar plan» ya fue satisfactoria). Todo lo demás verificable hoy está terminado y documentado.

## 1. Qué quedó terminado y con qué evidencia
| Entregable | Evidencia |
|---|---|
| Plan de noviembre v2 publicado (ventas y existencias al corte del 20/10, 7/14 días, 50 productos) | `CONGELACION_ENTREGA_20261023.md` §1 y §3; `verif_final_resultado.json`; 3110044: 18.214 · 25 (7 d) · 21 (14 d, llega tarde) |
| Recomendaciones explicables («Entender la compra»: frase de cálculo, 14 pasos, nota del plazo largo) | `T22_PILOTO_COMPRA_RECOMENDADA.md` §6; navegador 22/22 en local y nube |
| Pantallas Inicio, Ventas previstas, Existencias, Compra recomendada a 100 % de zoom | `T22_PILOTO_COMPRA_RECOMENDADA.md`, `T22_PLAN_EXTENSION_PILOTO.md` §5; 36/36 + 20/20 |
| Evaluación académica separada con su etiqueta de inventario simulado | recorrido público 12/12; pantalla «Evaluación académica» |
| Alcance de «Cargar datos» y «Crear análisis» aclarado (reglas reales del servidor) | `T22_ALCANCE_DATOS_Y_PLAN.md`; alcance 7/7 |
| Existencias: qué movimientos entran en el plan (impacto en cantidades: ninguno) | `T22_ALCANCE_DATOS_Y_PLAN.md` §2; `verif_stock_plan.mjs` |
| **TRUSTED_PROXIES corregido** (`192.168.0.1/32`) | `T22_TRUSTED_PROXIES_Y_CREDENCIAL.md` §1 (medición, revisión publicada, 20 fallos → 429, cabecera falsa no evade, otro cliente 401) |
| Publicación en Azure + Atlas, API/worker conectados, roles, HTTPS | `CONGELACION_ENTREGA_20261023.md` §3–4; `seg_publica.mjs` |
| Congelación y recuperación verificada | `CONGELACION_ENTREGA_20261023.md` §1–2 (imagen anterior `t22f-fb1661b`, paquete de datos con restauración verificada 23/10) |
| Consumo observado y disponibilidad | US$ 1,544 hasta el 22/10 (observado); ≈ US$ 3,5 al 23/10 (proyección); API y worker 1/1 |
| Manuales y material para el grupo | ver §5 |
| Hechos para alinear el informe académico (sin tocar el Word) | `HECHOS_PARA_INFORME_ACADEMICO.md` |

## 2. Qué quedó fuera del alcance
- **Actualización operativa autónoma** (nuevos cortes desde la aplicación): pospuesta; trabajo futuro (`T22_VIABILIDAD_ACTUALIZACION_OPERATIVA.md`). Incorporar cortes nuevos requiere un procedimiento técnico y datos posteriores al 20/10 que hoy no existen completos.
- Ejecución de compras, medición de impacto o ahorro en la empresa; nuevos modelos; repetición de T12; latencia p95 y 5 sesiones simultáneas medidas en la nube; informe académico Word.
- Continuidad del servicio después del 23/10 (no asumida).

## 3. Qué depende de Rogelio
0. ~~Prueba administrativa «Generar plan»~~: **hecha y satisfactoria** (§4).
1. **Credencial de Atlas:** entregar los **nombres y roles** de los Database Users (sin contraseñas); con eso identifico el afectado, guío la rotación paso a paso y compruebo que el acceso antiguo dejó de funcionar y que API y worker siguen conectados.
2. **Aceptación final** de la aplicación (no se registra sin su respuesta).
3. **Decisión sobre el servicio después del 23/10** (continuar ≈ US$ 1,9/día o escalar a 0 conservando datos).

## 4. Prueba humana pendiente (una sola acción)
**Acción:** inicia sesión como **administrador** (`pub_admin`), abre **Compra recomendada**, baja al formulario y pulsa **«Generar plan»** sin cambiar ningún valor.
**Resultado esperado:** aviso verde «Ya existía un plan con exactamente estos datos: se reutilizó y no se calculó de nuevo»; la **versión 2** sigue vigente y no aparece una versión 3 (el selector de versión sigue mostrando solo v2 y v1).
**Resultado real (23/10/2026, ejecutado por Rogelio como `pub_admin`): SATISFACTORIO.** Apareció «Ya existía un plan con exactamente estos datos: se reutilizó y no se calculó de nuevo»; el selector siguió en v2 y solo mostró v1 y v2 (sin v3). **Contraste del servidor** (`verif_final.mjs` el 23/10/2026 03:20 UTC, después de la prueba): 2 planes, v2 `plan-2026-11-d20261021-d72cbd8fa9bd` (creado 22/10 02:10 UTC, vigente) y v1 `plan-2026-11-d20261018-831a5df711f4`; 3110044 sigue en 25 / 21. Registrado por la respuesta de Rogelio; el soporte repitió la comprobación en servidor. Esto **no** equivale a la aceptación final.
Si aparece una versión 3, **no seguir** y avisar: significaría que los datos o parámetros cambiaron.

## 5. Dónde están los manuales y el material
- Manuales: `docs/MANUAL_USUARIO.md`, `docs/MANUAL_OPERACION.md` (§9–10).
- Guía rápida lector/administrador: `docs/GUIA_RAPIDA.md` · Demostración con 3110044: `docs/DEMOSTRACION_3110044.md` · Explicación sencilla: `docs/EXPLICACION_SIMPLE.md` · Modelos y método: `docs/MODELOS_Y_METODO_OPERATIVO.md` · Preguntas frecuentes: `docs/PREGUNTAS_FRECUENTES_EXPOSICION.md` · Hechos para el informe: `docs/HECHOS_PARA_INFORME_ACADEMICO.md` · Congelación: `docs/CONGELACION_ENTREGA_20261023.md`.
- Respaldo visual (13 capturas del recorrido con 3110044, sin contraseñas): `artifacts/private/respaldo_visual/` (privado; contiene nombres y cantidades de productos: solo para la exposición).

## 6. Qué depende de la empresa
Confirmar las **compras 11452 y 11455** (fecha de recepción futura registrada; hoy no se suman como pedidos por recibir) y las **13 diferencias de inventario** entre la existencia reconstruida y el stock del sistema (hoy sin ajustes). También confirmar plazos de entrega y reserva si quieren tratarlos como condiciones reales del proveedor (hoy son parámetros configurados). Mientras no respondan, las pantallas las muestran como pendientes.

## 7. Resultado de la corrida de pruebas de backend de esta entrega
`.venv\Scripts\python -m pytest tests/backend tests/jobs tests/plan tests/publish tests/inventory -q` el 23/10/2026 (≈ 03:05 UTC): **777 aprobadas, 4 omitidas, 0 fallas** (407 s). Frontend `ng test`: 312/312. No se ejecutaron pruebas de modelos ni T12.
