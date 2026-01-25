FROM python:3.11-slim

# Install pustaka sistem minimal untuk pengolahan gambar dan Glib
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Sisanya tetap sama
COPY requirements.txt .
RUN pip install --no-cache-dir --default-timeout=100 -r requirements.txt

COPY . .

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "django_mqtt.wsgi:application"]