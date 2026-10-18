# syntax=docker/dockerfile:1
# Una sola imagen para los roles api | worker | worker-once | scheduler (deploy/entrypoint.sh).
# Sin datos, sin .env, sin .git: el contexto lo restringe .dockerignore. Los secretos entran por variables
# de entorno (o archivos montados) al arrancar el contenedor, nunca en la imagen.

# --- Etapa 1: Angular compilado con el lockfile (npm ci, reproducible) ---------------------------------
FROM node:24-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/angular.json frontend/tsconfig.json frontend/tsconfig.app.json ./
COPY frontend/public ./public
COPY frontend/src ./src
RUN npx ng build --configuration production

# --- Etapa 2: dependencias Python fijadas (requirements.lock.txt) --------------------------------------
FROM python:3.12-slim AS pydeps
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1
COPY requirements.lock.txt /tmp/requirements.lock.txt
# Se excluyen herramientas de desarrollo (pytest, ruff, ...); --no-deps respeta exactamente el lock
# (en Linux xgboost declara ademas nvidia-nccl, solo para GPU; no se instala).
RUN grep -viE '^(pytest|pluggy|iniconfig|pygments|ruff|colorama)==' /tmp/requirements.lock.txt > /tmp/runtime.txt \
 && python -m venv /opt/venv \
 && /opt/venv/bin/pip install --no-deps -r /tmp/runtime.txt

# --- Etapa 3: imagen final, usuario no root ------------------------------------------------------------
FROM python:3.12-slim AS runtime
ENV PATH=/opt/venv/bin:$PATH PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    APP_ENV=production MPLCONFIGDIR=/tmp/mpl DF_UPLOADS_DIR=/data/uploads FRONTEND_DIST_DIR=/app/frontend/dist/frontend/browser
RUN groupadd --system --gid 10001 app && useradd --system --uid 10001 --gid app --home-dir /nonexistent --shell /usr/sbin/nologin app \
 && mkdir -p /app /data/uploads && chown -R app:app /data
COPY --from=pydeps /opt/venv /opt/venv
WORKDIR /app
COPY backend ./backend
COPY pipeline ./pipeline
COPY config ./config
COPY --from=web /web/dist/frontend/browser ./frontend/dist/frontend/browser
COPY deploy/entrypoint.sh /usr/local/bin/df-entrypoint
RUN chmod 0555 /usr/local/bin/df-entrypoint
USER app
VOLUME ["/data"]
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD ["python", "-c", "import sys,urllib.request as u; sys.exit(0 if u.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=4).status == 200 else 1)"]
ENTRYPOINT ["/usr/local/bin/df-entrypoint"]
CMD ["api"]
