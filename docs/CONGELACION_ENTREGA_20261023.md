# Congelación de la versión entregada (exposición 23/10/2026 19:30 Lima)

Registro de qué está efectivamente publicado, cómo recuperarlo y qué evidencias lo respaldan. Después del cierre solo se admiten correcciones que bloqueen el uso o la exposición.

## 1. Versión efectivamente publicada (comprobada en Azure el 23/10/2026 02:50–03:00 UTC = 22/10 21:50–22:00 Lima)
| Elemento | Valor |
|---|---|
| URL | https://dfpub-api.ashyglacier-9e3e37bc.brazilsouth.azurecontainerapps.io |
| Imagen en producción (API y worker) | `dfpubacrlwtfi63hqyb7u.azurecr.io/demand-forecasting:t22g-a9119ae` — digest `sha256:08982312dbb2d259c75e396c74282ae1ecc50356632088b6d7c9913241fb18c0` |
| Commit del código de la imagen | **`a9119ae`** («T22: alcance de datos y plan operativo, Ayuda y manuales por rol») |
| Revisión / réplicas | `dfpub-api--latest` réplica `…47b0586216f1` (creada 23/10 02:13 UTC, 0 reinicios, `TRUSTED_PROXIES=192.168.0.1/32`); `dfpub-worker--latest` réplica `…af01443a…` (creada 01:25 UTC, 0 reinicios); ambas 1/1 |
| Base de datos | Atlas Free `demand-forecasting-dev`, base `demand_forecasting_pub`; usuario de aplicación `dfpub_app` (`readWrite` solo en esa base) |
| Plan vigente | `plan-2026-11-d20261021-d72cbd8fa9bd` (v2, decisión 21/10, corte de ventas 20/10, existencia reconstruida `invrec-20261020-445045630003`); conservado `plan-2026-11-d20261018-831a5df711f4` (v1, corte 30/09) |
| Dataset operativo | `plds-1f4717744dc3` (15 fuentes, corte 20/10; el 21/10 parcial queda fuera) |
**Checkpoint documental (distinto del de código):** etiqueta Git **`entrega-20261023`** (commit de documentación posterior a `a9119ae`: cambios solo en `docs/` e `infra/main.bicep` —valor por defecto `trustedProxies`—, sin cambios de código de la aplicación; `backend/` y `pipeline/` no cambian desde `d68513c`). Etiquetas intermedias: `t22-piloto-3`, `t22-extension-1`, `t22-alcance-1`, `t22-proxies-1`.

## 2. Recuperación verificada
- **Imagen anterior estable:** `t22f-fb1661b` — digest `sha256:ff780b7c40644e9af408c3ca2d598eb8c2e43b4d2ffe03f1b5475c3ab7bce774`, **estuvo en producción y pasó** alcance 7/7, recorrido público 12/12, extensión 36/36, piloto 20/20 y «Entender la compra» 22/22 antes de pasar a `t22g` (que solo añade la sección de Ayuda). Más antiguas conservadas en el registro: `t22e-2fdc5e9`, `t20c-5460230`, `t20r-ffa877f`. Volver atrás: `az containerapp update -g rg-demand-forecasting-pub -n dfpub-api --image dfpubacrlwtfi63hqyb7u.azurecr.io/demand-forecasting:t22f-fb1661b` (y `dfpub-worker`), luego medir la IP de salida y compararla con la lista de Atlas (`MANUAL_OPERACION.md` §9).
- **Datos:** paquete `artifacts/private/cloud_bundle_20261021/` (manifiesto con huellas por colección); **restauración verificada de nuevo el 23/10/2026 02:54 UTC** en una base temporal: `RESTAURACION VERIFICADA` (conteos y huellas idénticos). Atlas contiene los datos cargados y verificados por huella el 22/10.
- **No se eliminó ningún recurso.**

## 3. Evidencias vigentes y comprobaciones de cierre (nube, 23/10/2026)
| Comprobación | Resultado |
|---|---|
| `health` | `ok`, base de datos `ok` |
| API ↔ Atlas dentro de la réplica real | `ping` ok; usuario `dfpub_app`; `readWrite` solo en `demand_forecasting_pub`; escritura en otra base **denegada** |
| Worker ↔ Atlas dentro de la réplica real | `ping` ok (IP de salida `20.206.93.129`); referencia T07 materializada desde Mongo al iniciar |
| Reinicio real (no solo configuración 1/1) | nombres de réplica nuevos, `restartCount 0`, log del worker «referencia T07 materializada» tras cada actualización |
| Acceso por roles (`seg_publica.mjs`) | sin sesión 401; POST sin/ con CSRF inválido 403; lector 403 incluso con CSRF válido; administrador 422 (llega a validación, no crea nada); cookie HttpOnly/Secure/SameSite=Strict; HTTP→HTTPS 301; HSTS, CSP, X-Frame-Options |
| Recorrido público (`e2e_publica.mjs`) | 12/12 |
| Pantallas (`e2e_t22_extension.mjs`, `e2e_t22_piloto.mjs`, `e2e_t22_entender.mjs`, `e2e_t22_alcance.mjs`) | 36/36 · 20/20 · 22/22 · 7/7 |
| Conservación del plan (`verif_final.mjs`, 23/10 02:52 UTC) | 2 versiones intactas (v2 vigente, v1); v2: 50 productos, corte 20/10, existencia reconstruida; **3110044**: previsión 18.214, 0.607/día, existencia 0, compra **25** (7 d, llega 28/10, OK) y **21** (14 d, llega 04/11, LLEGA_TARDE, faltante en el mes 1.821); 19 con compra en cada plazo, 10 «llega tarde» a 14 d, 13 diferencias, pendientes `COMPRAS_11452_11455` y `DIFERENCIAS_INVENTARIO` |
| Frontend | `ng test` 312/312 y `ng build` correcto |
| Backend | sin cambios desde `d68513c`; `tests/backend tests/jobs tests/plan tests/publish tests/inventory`: **777 aprobadas, 4 omitidas, 0 fallas** (23/10/2026) |
Pruebas de los modelos o de T12: **no se repitieron** (resultados y sellos conservados).

## 4. Seguridad
- **TRUSTED_PROXIES: corregido.** Configuración `192.168.0.1/32` en `dfpub-api` (también por defecto en `infra/main.bicep`); medición: el par TCP es `192.168.0.1` y Azure sobrescribe `X-Forwarded-For`; revisión publicada = la actual (réplica `…47b0586216f1`); pruebas: 20 fallos → 429, `X-Forwarded-For` falsificado no evade, otro cliente 401, recorrido 12/12 y roles/CSRF intactos (`T22_TRUSTED_PROXIES_Y_CREDENCIAL.md`).
- **Credencial expuesta de Atlas: PENDIENTE; Rogelio decidió posponerla hasta después del 23/10** (se necesitarán los nombres y roles de los Database Users; no se actúa por descarte). La seguridad **no** está totalmente cerrada. `dfpub_app` y los accesos de API/worker no se tocan hasta tener evidencia.
- Sin `0.0.0.0/0`, TLS verificado, sin credenciales en el repositorio (revisión de secretos sin hallazgos).

## 5. Operación, consumo y disponibilidad
- **Consumo observado** (Cost Management API, costo real, consulta 23/10/2026 02:54 UTC, datos con retraso): **US$ 1,544 acumulados hasta el 22/10/2026** (Container Apps 1,447; Container Registry 0,097; Log Analytics y Storage 0,00). Aún no hay cifra del 23/10.
- **Proyección (no observada):** ≈ US$ 1,9 por día con API y worker en 1/1 → ≈ US$ 3,5 al cierre del 23/10 (< US$ 8 de revisión y < US$ 20 de techo). Sin cargos de bolsillo ni cambio de plan.
- **Disponibilidad para la exposición:** API y worker en mínimo 1 réplica (sin arranque en frío), Atlas Free (≈ 320 de 512 MB). No se identificó ningún impedimento para mantener el servicio hasta el 23/10 19:30 Lima.
- **Después del 23/10 no se asume continuidad:** requiere una decisión de Rogelio (continuar ≈ US$ 1,9/día o escalar a 0 réplicas conservando los datos; ACR ≈ US$ 0,10–0,17/día fijo). No se elimina nada sin copia verificada y orden expresa.


## 6. Aceptación y congelación
Alcance funcional aceptado por Rogelio el 23/10/2026 (ver `CIERRE_ENTREGA_20261023.md` §0; excluye actualización autónoma y mejoras económicas reales). La versión `t22g-a9119ae` queda congelada para la exposición; solo se modifica ante una incidencia que impida utilizarla.
