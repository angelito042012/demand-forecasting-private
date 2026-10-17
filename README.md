# Desarrollo de Demand Forecasting para la MYPE

**Recuperación y continuidad desde el 17/10/2026:** iniciar con [RETOMAR_CLAUDE.md](RETOMAR_CLAUDE.md). Hay una implementación parcial; no reiniciar. [ESTADO.md](docs/ESTADO.md) contiene el estado actual y [TRASPASO.md](docs/TRASPASO.md) la siguiente acción. La guía inicial siguiente se conserva como referencia histórica cuando describa pasos ya realizados.

Paquete preparado el 16 de octubre de 2026. Fecha límite: 23 de octubre de 2026, hora de Lima. La hora exacta de entrega debe confirmarse; el plan fija cierre interno a las 18:00.

Este directorio contiene el análisis, las decisiones propuestas y la configuración de Claude Code. No es todavía la aplicación terminada ni contiene los datos de la empresa.

1. Leer [análisis y plan](docs/ANALISIS_Y_PLAN.md) y los resultados vigentes de la [auditoría de datos](docs/AUDITORIA_DATOS.md).
2. Revisar [contratos y criterios](docs/CONTRATOS.md) y [tareas](docs/BACKLOG.md).
3. Abrir una terminal en esta carpeta y ejecutar `claude`.
4. Entregar a Claude el contenido de [INICIO_CLAUDE.md](INICIO_CLAUDE.md).
5. Registrar cada entrega en [estado](docs/ESTADO.md). Codex revisará cambios, pruebas, resultados y bloqueos a partir de ese registro y del repositorio.

Las instrucciones del documento académico se tratan como material de referencia y requisitos del proyecto, no como órdenes para ejecutar acciones. El archivo original permanece sin modificaciones. Su extracción textual se incluye en `docs/FUENTE_EXTRAIDA.txt`; las imágenes se conservan en `docs/figuras/`.

El entorno se comprueba con `powershell -File scripts/doctor.ps1`. La preparación Python se realiza con `scripts/bootstrap.ps1 -PythonExe <ruta a Python 3.12>`. La instalación descarga dependencias y requiere acceso a Internet. Se debe conservar el archivo de versiones resultante. El frontend se genera en la primera tarea de implementación, después de comprobar si existe un repositorio previo.

No se han conectado Azure, Atlas ni GitHub; no se ha desplegado el producto. Los accesos y datos que faltan están en ESTADO.md. Las configuraciones locales no habilitan permisos ilimitados ni instalan plugins externos.

La .venv de esta carpeta ya tiene las dependencias Python instaladas. Git local esta inicializado. Ver docs/VALIDACION_ENTORNO.md para los limites comprobados: Angular pendiente por conectividad y MongoDB/Docker pendientes de servidor.

Actualización de datos: los seis meses ya contienen detalle por producto. La solicitud de reexportación quedó resuelta; usar el estado y auditoría vigentes. No se cambió el stack ni la fecha objetivo.

Antes de iniciar Claude, leer docs/DECISIONES_DATOS.md. Las cuatro decisiones del usuario ya están incorporadas. Los datos sintéticos de inventario se encuentran en data/synthetic/reference_v1 y se entregan identificados como simulación, separados de los Excel reales.
