# Gunakan base image Python yang ringan
FROM python:3.10-slim

# Hindari pembuatan file .pyc dan aktifkan log output langsung
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Jakarta

WORKDIR /app

# Install dependensi
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy seluruh script dan konfigurasi
COPY . .

# Healthcheck: cek apakah file /tmp/worker_alive diperbarui dalam 60 detik terakhir
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import os, time, sys; sys.exit(0 if os.path.exists('/tmp/worker_alive') and (time.time() - os.path.getmtime('/tmp/worker_alive') < 60) else 1)"

# Default command: jalankan unified runner
CMD ["python", "runner.py"]
