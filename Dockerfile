FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Set environment variables
ENV PORT=8080
ENV PYTHONUNBUFFERED=1

EXPOSE 8080

CMD ["gunicorn", "api:app", "--bind", "0.0.0.0:8080", "--workers", "2", "--timeout", "120"]

