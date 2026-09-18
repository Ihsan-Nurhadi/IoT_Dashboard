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

# Default command: jalankan unified runner
CMD ["python", "runner.py"]
