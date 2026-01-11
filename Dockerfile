FROM python:3.12-slim

# ---------------------------------------------------------------------
# CRITICAL PERFORMANCE FIX: Prevent CPU Oversubscription
# ---------------------------------------------------------------------
# By default, NumPy/Pandas try to use multiple threads per request.
# On Cloud Run (2 vCPU), this causes thread contention, leading to 
# timeouts and the "Join" refresh loop you saw.
# We force math libraries to use 1 thread, letting Gradio manage user concurrency.
ENV OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    VECLIB_MAXIMUM_THREADS=1 \
    NUMEXPR_NUM_THREADS=1 \
    PYTHONUNBUFFERED=1 \
    FORWARDED_ALLOW_IPS="*"

# Install system dependencies
# Added 'sqlite3' for debug and 'wget' for downloading data during build
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    gcc \
    python3-dev \
    sqlite3 \
    wget \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements-apps.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements-apps.txt && \
    pip install aimodelshare --no-dependencies

# ---------------------------------------------------------------------
# Cache Conversion Layer
# ---------------------------------------------------------------------
# 1. Copy the converter script first
COPY convert_db.py .

# 2. Copy available cache files (with wildcard support)
# Note: At least one file matching this pattern must exist in the build context
# or the Docker build will fail. The convert_db.py script will handle cases where
# only one of the two cache files is present.
COPY prediction_cache*.json.gz ./

# 3. RUN the conversion immediately. 
# This burns the optimized SQLite DB into the image layer.
# The script handles both cache files and merges them if both exist,
# or processes just one if only one is present.
RUN echo "=== Starting Cache Conversion ===" && \
    python convert_db.py && \
    echo "=== Cleaning up cache files ===" && \
    rm -f prediction_cache.json.gz prediction_cache_full_models.json.gz && \
    echo "=== Cache conversion complete ==="

# ---------------------------------------------------------------------
# DATA CACHING: Download raw data during build
# ---------------------------------------------------------------------
# We download the CSV once here so the app never has to fetch it at runtime.
# This prevents GitHub rate-limiting issues on Cloud Run.
RUN wget -O compas.csv "https://raw.githubusercontent.com/propublica/compas-analysis/master/compas-scores-two-years.csv"

# ---------------------------------------------------------------------
# Final Setup
# ---------------------------------------------------------------------
COPY . .

# Healthcheck to ensure container is responsive
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import socket,os; s=socket.socket(); s.settimeout(2); s.connect(('127.0.0.1', int(os.environ.get('PORT','8080')))); s.close()" || exit 1

EXPOSE 8080

# This runs the dispatcher script to select the correct app
CMD ["python", "launch_entrypoint.py"]
