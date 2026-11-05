# ==============================================
# Multi-stage build: Frontend + Backend
# ==============================================

# --- Stage 1: Build frontend ---
FROM node:22-slim AS frontend-build
WORKDIR /app/viewer
COPY viewer/package.json viewer/package-lock.json ./
COPY viewer/vendor/openaec-ui-react ./vendor/openaec-ui-react
RUN npm ci
COPY viewer/ ./
COPY scripts/dependency-notices.mjs /app/scripts/dependency-notices.mjs
RUN node /app/scripts/dependency-notices.mjs /app/viewer/node_modules > /app/FRONTEND-NOTICES.txt

# OIDC config baked into frontend at build time
ARG VITE_OIDC_AUTHORITY=https://auth.open-aec.com/application/o/bim-validator-oidc/
ARG VITE_OIDC_CLIENT_ID=bim-validator
ENV VITE_OIDC_AUTHORITY=$VITE_OIDC_AUTHORITY
ENV VITE_OIDC_CLIENT_ID=$VITE_OIDC_CLIENT_ID

ENV NODE_OPTIONS="--max-old-space-size=3072"
RUN npm run check:blueprint && npm run build

# --- Stage 2: Production image ---
FROM python:3.11-slim

WORKDIR /app

# Install system deps for ifcopenshell
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY server/requirements.txt ./server/requirements.txt
COPY requirements-release.txt ./requirements-release.txt
RUN pip install --no-cache-dir -r requirements-release.txt

# Install the ifc_validator package
COPY pyproject.toml README.md LICENSE THIRD-PARTY-NOTICES.txt ./
COPY src/ ./src/
RUN pip install --no-cache-dir --no-deps -e .

COPY scripts/third_party_notices.py ./scripts/third_party_notices.py
COPY --from=frontend-build /app/viewer/vendor ./viewer/vendor
RUN python scripts/third_party_notices.py > /tmp/THIRD-PARTY-NOTICES.txt \
    && mv /tmp/THIRD-PARTY-NOTICES.txt /app/THIRD-PARTY-NOTICES.txt

# Copy server code
COPY server/ ./server/

# Copy IDS fixtures
COPY ids-bestanden/ ./ids-bestanden/

# Copy built frontend from stage 1
COPY --from=frontend-build /app/viewer/dist ./viewer/dist
COPY --from=frontend-build /app/FRONTEND-NOTICES.txt ./FRONTEND-NOTICES.txt

# Create temp directories and persistent project storage
RUN useradd --uid 10001 --create-home validator \
    && mkdir -p /tmp/ifc_uploads /tmp/ifc_processed /tmp/ids_validation_jobs /data/projects \
    && chown -R validator:validator /data /tmp/ifc_uploads /tmp/ifc_processed /tmp/ids_validation_jobs

ENV DATABASE_URL=sqlite+aiosqlite:////data/bimvalidator.db
ENV PROJECT_FILES_DIR=/data/projects
USER validator

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
