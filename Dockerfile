FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    gcc \
    python3-dev \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements-apps.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements-apps.txt && \
    pip install aimodelshare --no-dependencies

COPY . .

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import socket,os; s=socket.socket(); s.settimeout(2); s.connect(('127.0.0.1', int(os.environ.get('PORT','8080')))); s.close()" || exit 1

EXPOSE 8080
CMD ["python", "launch_entrypoint.py"]
