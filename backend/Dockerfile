FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHON_UNBUFFERED 1

WORKDIR /app

# Install system dependencies, Node.js, and ffmpeg for video processing
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    curl \
    ffmpeg \
    && curl -sL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/