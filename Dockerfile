# ---------------------------------------------------------------------------
# Arepas API — App Runner container image
#
# Build for linux/amd64 (App Runner):
#   docker buildx build --platform linux/amd64 -t arepas-api .
#
# Run locally (mirrors App Runner env, no local data — S3 required):
#   docker run -p 8000:8000 \
#     -e AREPAS_S3_BUCKET=arepas-data-637423382120 \
#     -e AREPAS_S3_MODELS_BUCKET=arepas-models-637423382120 \
#     -e AREPAS_COGNITO_USER_POOL_ID=us-east-1_vTMsQp9bx \
#     -e AREPAS_COGNITO_CLIENT_ID=7iar8pck9bprbudr4sl0sugbc2 \
#     -e AREPAS_AUTH_MODE=cognito \
#     arepas-api
#
# Local dev (keeps full local behaviour — no S3, no Cognito):
#   uvicorn src.api.main:app --reload --port 8000
# ---------------------------------------------------------------------------
FROM python:3.11-slim

# Suppress interactive prompts during apt
ENV DEBIAN_FRONTEND=noninteractive

# Install OS deps: libgl1 needed by Pillow/OpenCV, curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Python dependencies ─────────────────────────────────────────────────────
# Install CPU-only PyTorch first (avoids pulling the 2+ GB CUDA wheels).
# The --index-url switch applies only to the torch/torchvision packages.
COPY requirements-container.txt .
RUN pip install --no-cache-dir \
        torch==2.4.1 torchvision==0.19.1 \
        --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements-container.txt

# ── Bake GroundingDINO weights ───────────────────────────────────────────────
# Download grounding-dino-tiny (~172 MB) at build time so the container starts
# without a network download.  The HuggingFace cache lives at /root/.cache.
RUN python -c "\
from transformers import AutoProcessor, AutoModelForZeroShotObjectDetection; \
AutoProcessor.from_pretrained('IDEA-Research/grounding-dino-tiny'); \
AutoModelForZeroShotObjectDetection.from_pretrained('IDEA-Research/grounding-dino-tiny'); \
print('GroundingDINO weights cached OK')"

# ── Application code ─────────────────────────────────────────────────────────
# Copy only the source tree and config (not data/, outputs/, .venv/, etc.)
COPY src/ src/
COPY config/ config/
COPY schema/ schema/

# ── Runtime config ───────────────────────────────────────────────────────────
# App Runner sets AREPAS_S3_*, AREPAS_COGNITO_*, AREPAS_AUTH_MODE via service
# environment variables. These defaults allow a bare `docker run` to boot and
# show an explicit error if S3 is not configured, rather than silently failing.
ENV AREPAS_AUTH_MODE=cognito \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# App Runner expects the container to listen on PORT (default 8080).
# Uvicorn binds to 0.0.0.0:${PORT:-8080} so both App Runner and local docker
# run work without changing the command.
EXPOSE 8080

# Healthcheck — App Runner also does its own but this helps local testing.
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8080}/api/checkpoints || exit 1

CMD ["sh", "-c", "uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1"]
