FROM python:3.11-slim

WORKDIR /app

# Prevent Python from writing pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application
COPY . /app/
RUN sed -i 's/\r$//' /app/start.sh && chmod +x /app/start.sh

EXPOSE 8000

CMD ["sh", "-c", "/app/start.sh"]
