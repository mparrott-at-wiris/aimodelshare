# Use python 3.12 slim for smaller image size (~100MB base)
FROM python:3.12-slim

# 1. Install system dependencies
# libgl1-mesa-glx is needed for visual libraries like seaborn/matplotlib
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2. Install Dependencies (Cached Layer)
# We copy requirements first to leverage Docker layer caching
COPY requirements-apps.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements-apps.txt

# 3. Copy Application Code
COPY . .

# 4. Runtime Config
EXPOSE 8080
CMD ["python", "launch_entrypoint.py"]
