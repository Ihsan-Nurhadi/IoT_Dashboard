# Gunakan image Python yang ringan
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install dependencies sistem
# Kita hanya butuh netcat untuk script entrypoint (opsional) 
# dan lib dependencies ringan.
RUN apt-get update && apt-get install -y \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements dan install
COPY requirements.txt /app/
# Sekarang install akan jauh lebih cepat dan lancar
RUN pip install --no-cache-dir -r requirements.txt

# Copy seluruh code project
COPY . /app/

# Expose port
EXPOSE 8000

# Command default
CMD ["gunicorn", "django_mqtt.wsgi:application", "--bind", "0.0.0.0:8000"]