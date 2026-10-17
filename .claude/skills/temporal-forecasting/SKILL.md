---
name: temporal-forecasting
description: Construye y evalua pronosticos de demanda con cortes temporales y control de fuga para este proyecto.
---

Lee los criterios A03-A05 de docs/CONTRATOS.md. Reserva agosto de 2026 como test y usa marzo-julio para entrenamiento y validacion, si la auditoria confirma meses completos. Ajusta imputacion, escalado, seleccion de variables e hiperparametros solo dentro de cada train. Documenta cualquier cambio de corte antes de abrir resultados test.
Compara naive, naive semanal y media movil con Random Forest y un boosting. Features temporales usan shift antes de rolling. Precios futuros deben haber sido conocidos al emitir; ventas futuras no pueden aparecer en rezagos del horizonte multistep. Evalua ventanas de igual horizonte y frecuencia que la corrida operacional.
Reporta MAE, RMSE, MAPE, R2 y WAPE con denominadores validos, cobertura y tamaño de muestra. Ceros y series constantes requieren tratamiento explicito, no epsilon que esconda el problema. No prometas MAPE menor de 15% ni R2 mayor de 0.85; informa si se cumplen.
Devuelve dataset hash, seed, dependencias, fechas, modelos, configuracion y resultados. Si ML no supera baseline, conserva evidencia y recomienda el mejor modelo validado sin ocultar el resultado.

Hallazgo vigente: leer docs/AUDITORIA_DATOS.md. Los seis meses ya tienen detalle por producto. Conservar agosto reservado y resolver negativos tipo 7, dias sin registros y consistencia de categorias. Los datos operativos de inventario siguen pendientes.

Actualización autorizada: aplicar docs/DECISIONES_DATOS.md. Créditos tipo 7 confirmados; excluir los tres días sin comprimir calendario; catálogo por corte; inventario sintético reference_v1 permitido para escenarios. No solicitar otra vez estas decisiones ni presentar simulación como inventario o política reales.
