FROM --platform=linux/amd64 python:3.11-slim

# Install system dependencies (ffmpeg for audio processing)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN python -m pip install --upgrade pip

WORKDIR /app
COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY . .

EXPOSE 5000

# Use shell form so $PORT gets expanded (Railway sets PORT env var)
CMD gunicorn api:app --bind 0.0.0.0:${PORT:-5000} --workers 2 --timeout 120

