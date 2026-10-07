# Builds for linux/arm64 (QNAP TS-932X) and linux/amd64 alike.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    DATA_DIR=/data TZ=Asia/Taipei

WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir . \
 && playwright install --with-deps chromium \
 && rm -rf /var/lib/apt/lists/*

VOLUME /data
EXPOSE 8000
CMD ["cruise", "serve", "--host", "0.0.0.0", "--port", "8000"]
