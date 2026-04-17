FROM python:3.12-slim

# Non-root user for security
RUN useradd --create-home --shell /bin/bash app

WORKDIR /app

# Install dependencies first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY src/ ./src/

# Data directory (will be overridden by volume mount)
RUN mkdir -p /data && chown app:app /data

USER app

ENTRYPOINT ["python", "src/main.py"]
# Default: normal mode. Override CMD to pass --save for init.
CMD []
