FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Install dependencies sistem
RUN apt-get update && apt-get install -y netcat-openbsd

# Install python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gunicorn

COPY . /app/

EXPOSE 8000

# Command default untuk Web Server
CMD ["gunicorn", "NMS_Backend.wsgi:application", "--bind", "0.0.0.0:8000"]