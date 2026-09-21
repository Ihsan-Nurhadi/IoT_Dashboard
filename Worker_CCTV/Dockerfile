FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Jakarta

WORKDIR /app

# Install system dependencies required for OpenCV, FFmpeg, curl, and network utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    ffmpeg \
    iputils-ping \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Download go2rtc binary (ultra-low latency WebRTC & H.264 zero-copy streaming engine)
RUN ARCH=$(uname -m) && \
    if [ "$ARCH" = "x86_64" ]; then GOARCH="amd64"; \
    elif [ "$ARCH" = "aarch64" ]; then GOARCH="arm64"; \
    else GOARCH="amd64"; fi && \
    curl -L -s "https://github.com/AlexxIT/go2rtc/releases/download/v1.9.8/go2rtc_linux_${GOARCH}" -o /usr/local/bin/go2rtc && \
    chmod +x /usr/local/bin/go2rtc

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Expose default Gateway API port & WebRTC port
EXPOSE 3001
EXPOSE 8555/tcp
EXPOSE 8555/udp

# Start the Gateway API service
CMD ["python", "main.py"]
