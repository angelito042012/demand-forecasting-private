# Validación del entorno preparado

Fecha de referencia: 16/10/2026, America/Lima.

| Elemento | Resultado |
|---|---|
| Claude Code | 2.1.302 instalado; autenticación existente confirmada |
| Git | 2.55.0; repositorio local inicializado en esta carpeta, sin remoto |
| Node | 24.19.0 disponible |
| Python local | .venv creada con Python 3.12.14 |
| Dependencias Python | Instaladas; pip check sin incompatibilidades; versiones en requirements.lock.txt |
| Angular | Descarga pendiente: dos consultas al registro npm fallaron con ECONNRESET |
| Docker | CLI disponible; motor Linux no accesible |
| MongoDB | Sin servidor local ni Atlas conectado |
| Azure | Usuario confirma que no tiene acceso |
| Extensiones | Python y Angular detectadas en VS Code |
| Datos | Segunda auditoría completada: seis meses detallados; inventario operativo pendiente |

La creación inicial del entorno Python falló por permisos sobre la carpeta temporal del entorno de ejecución. Se corrigió usando una carpeta temporal dentro del espacio de trabajo; se reparó pip y se completó la instalación. bootstrap.ps1 incorpora el uso de una carpeta temporal local para próximas ejecuciones.

El archivo requirements.in contiene rangos iniciales. requirements.lock.txt conserva las versiones efectivamente instaladas; una reinstalación usa ese archivo. El entorno local depende del Python base de esta máquina; el ZIP no incluye .venv y debe reinstalarse en otra computadora.

Para completar infraestructura local, iniciar Docker Desktop y comprobar su motor, o preparar MongoDB por otra vía compatible. No se ha creado un servidor ficticio ni se ha declarado una conexión inexistente. Para Angular, recuperar acceso al registro npm y ejecutar scripts/prepare-frontend.ps1; ese script no fue ejecutado porque la consulta previa al registro falló.

Las reglas de lectura de .env en la configuración Claude son una defensa parcial, no una barrera completa frente a comandos de terminal. No guardar secretos en prompts, archivos versionados ni reportes de evidencia.

No se ha ejecutado una sesión de implementación de Claude ni se han medido consumos futuros. INICIAR_CLAUDE.ps1 abre una sesión interactiva con el encargo preparado. Las skills y agentes son locales al proyecto y requieren iniciar Claude desde esta carpeta.

Comprobaciones finales: importacion correcta de FastAPI, PyMongo, pandas, NumPy, scikit-learn, XGBoost y openpyxl; doctor completo con resultado de dependencias correcto. Cuatro skills validadas y cinco agentes con referencias a skills existentes. No son pruebas de producto.

Escenario sintético reference_v1 generado y verificado: conservación de stock en cada día/SKU, no negatividad, balance final de CSV exportados y demanda proxy = atención simulada + faltante simulado. Categoría del SKU 16140041 verificada con corte previo a agosto. No constituye evidencia de mejora real ni pruebas de la aplicación completa.
