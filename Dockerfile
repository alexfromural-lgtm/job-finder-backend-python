FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies (needed for psycopg2 sync in alembic)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Also install psycopg2 for Alembic sync migrations
RUN pip install --no-cache-dir psycopg2-binary

# Copy source
COPY . .

# Expose the port
EXPOSE 5002

# Entrypoint: run migrations then start uvicorn
ENTRYPOINT ["/bin/sh", "-c", "bash /app/scripts/docker-entrypoint.sh"]
