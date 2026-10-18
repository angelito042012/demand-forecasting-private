#!/bin/sh
# Roles de la imagen: api | worker | worker-once | scheduler | scheduler-once | cli <args...>
set -eu
role="${1:-api}"
[ "$#" -gt 0 ] && shift
case "$role" in
  api)
    # El proxy de confianza lo gestiona la aplicacion (TRUSTED_PROXIES); uvicorn nunca reescribe la IP del cliente.
    exec python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --no-proxy-headers \
      --timeout-graceful-shutdown 20 --log-level warning "$@" ;;
  worker)       exec python -m pipeline.jobs.worker "$@" ;;
  worker-once)  exec python -m pipeline.jobs.worker --once "$@" ;;
  scheduler)
    if [ "${DF_SCHEDULER_ENABLE:-false}" != "true" ]; then
      echo "El temporizador esta deshabilitado por defecto (DF_SCHEDULER_ENABLE=true para activarlo)." >&2; exit 3
    fi
    exec python -m pipeline.jobs.scheduler --loop --enable "$@" ;;
  scheduler-once) exec python -m pipeline.jobs.scheduler --once "$@" ;;
  cli)          exec python -m backend.cli "$@" ;;
  *) echo "Rol desconocido: $role (api|worker|worker-once|scheduler|scheduler-once|cli)" >&2; exit 2 ;;
esac
