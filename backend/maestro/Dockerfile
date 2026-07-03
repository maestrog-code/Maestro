# Use Python 3.12 slim image for a lightweight footprint
FROM python:3.12-slim

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Set work directory
WORKDIR /app

# Install system dependencies needed for Postgres and building Python packages
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Run the application (using Uvicorn for local/dev, replace with Gunicorn for strict prod if preferred)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
