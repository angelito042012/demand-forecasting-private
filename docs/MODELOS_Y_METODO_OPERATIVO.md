# Qué se evaluó (Random Forest y XGBoost), por qué el método operativo es `promedio_28` y por qué no afirmamos ahorro

Resumen de los hechos medidos en el proyecto (fuentes: `docs/T05_RESULTADOS.md`, `T06_RESULTADOS.md`, `T07_RESULTADOS.md`, `T12_RESULTADOS.md`, `SELECCION_CONGELADA.md`). **No se repitieron experimentos ni se reabrió T12** para esta entrega. WAPE = error absoluto total ÷ unidades vendidas (menos es mejor; 0,78 ≈ 78 % del volumen vendido, **no** «78 % de acierto»).

## 1. Qué se comparó
- **Referencias simples (T05):** `cero`, `último día`, `naive semanal`, **`promedio_28`** (media diaria de los últimos 28 días con datos válidos).
- **Aprendizaje automático (T06, marzo–julio, 5 folds de desarrollo, partición temporal, sin fuga):** **Random Forest** y **XGBoost**.
- **T07:** horizontes 10/14/21 días y simulación junio–julio; el comparador experimental es el **Random Forest por categoría distribuido a SKU** (`rf_distribuido`); XGBoost **no avanzó** a T07/T12 porque no cumplió la regla en T06.
- **T12 (evaluación final de agosto de 2026, una sola vez, con selección congelada el 17/10 antes de leer agosto):** `promedio_28` frente a RF y control `cero`.

## 2. Resultados clave (cifras reales de los reportes)
**T06, SKU, WAPE a 7 días (5 folds):** cero 1,000 · último día 1,312 · naive semanal 1,057 · **promedio_28 0,992** · Random Forest 1,058 (favorable en 1 de 5 folds) · XGBoost 1,017 (2 de 5). **Ningún método de ML cumplió la regla preregistrada para SKU.** A nivel **categoría** RF sí cumplió la regla (WAPE 0,394 frente a 0,403 de `promedio_28`; 3 de 5 folds) y XGBoost no (0,437).
**T07, SKU, acumulado a 14 días (4 folds de desarrollo):** `promedio_28` 0,873 frente a RF distribuido 0,929 → **RF no mejoró** (0 de 4 folds).
**T12, agosto 2026, SKU-almacén, cohorte primaria (n = 3.401), acumulado a 14 días:** **`promedio_28` 0,781** · RF distribuido 0,791 · cero 1,000; sesgo relativo 0,020 (promedio_28) y 0,030 (RF). Con un solo bloque **RF no puede declararse ganador**. Honestidad: en la cohorte de **historia corta** (357 SKU) RF fue mejor (0,801 frente a 1,062 a 14 días) y esa diferencia se informa, pero no cambia el método congelado.

## 3. Por qué el método operativo es `promedio_28`
1. **Ningún modelo superó de forma estable a `promedio_28`** en la evaluación predefinida (T06, T07) y en la final (T12): la diferencia a favor del promedio fue pequeña pero consistente.
2. Es **simple y explicable** con una cuenta (unidades vendidas ÷ días válidos de los últimos 28 días); el usuario puede reproducirla en la pantalla «Entender la compra».
3. No necesita reentrenar, no depende de variables que la empresa no registra y evita complejidad sin ventaja demostrada.
4. La elección se **congeló antes de mirar agosto** (selección y hash en `config/seleccion_congelada.*`): no se eligió el método después de ver el resultado.

## 4. Por qué no afirmamos ahorro (ni mejora empresarial)
- La simulación de agosto (T12, escenario L = 7, S = 7) usa **inventario simulado con supuestos**: stock inicial, costos (65 % de la mediana de precio), mantenimiento de stock, plazo y seguridad son supuestos; no hay proveedores ni mínimos reales y se simula un almacén.
- La demanda usada es **proxy** (ventas observadas, posiblemente limitadas por quiebres de stock reales desconocidos).
- Resultado de la simulación: fill rate `promedio_28` 0,7792 frente a RF 0,7812 y referencia fija 0,7561; la política con mejor servicio también tenía **más stock y más compras** (compras supuestas 309.792 frente a 326.713 con RF y 267.440 con la referencia fija), y una ventaja así **no se presenta como mejora**; no se calculó ahorro ni utilidad.
- Es **un solo bloque de 21 días**: sin intervalo de confianza ni tres folds.
- El plan de noviembre es un **plan bajo supuestos**: no se ejecutó ninguna compra y no se midió impacto en la empresa. Ninguna cifra de la aplicación debe leerse como ahorro o beneficio demostrado.

## 5. Qué sí puede afirmarse
- Hay un método **trazable y reproducible** (partición temporal, selección congelada, auditorías) y un plan **explicable** producto por producto.
- Las limitaciones y los resultados desfavorables (RF y XGBoost) están documentados y conservados.
