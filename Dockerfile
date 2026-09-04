FROM node:22-alpine AS frontend

WORKDIR /build

COPY affiche-frontend/package.json affiche-frontend/package-lock.json ./
RUN npm ci

COPY affiche-frontend/ ./
RUN npm run build

FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY affiche-backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY affiche-backend/affiche/ ./affiche/

COPY affiche-backend/alembic.ini .

COPY affiche-backend/resources/ ./resources/

COPY LICENSE ./LICENSE

COPY --from=frontend /build/dist ./static

ENV PYTHONUNBUFFERED=1 \
    CONFIG_DIR=/data/config

RUN mkdir -p /data/config/db /data/config/posters /data/config/log

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health').raise_for_status()" || exit 1

CMD ["uvicorn", "affiche.main:app", "--host", "0.0.0.0", "--port", "8000"]
