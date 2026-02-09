FROM python:3.11-slim

WORKDIR /app

# Install postgres + minimal tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql postgresql-contrib \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Add entrypoint
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Default envs (overrideable at runtime)
ENV PG_HOST=127.0.0.1 \
    PG_PORT=5432 \
    PG_DB=lg \
    PG_USER=lg \
    PG_PASSWORD=lg

ENTRYPOINT ["docker-entrypoint.sh"]
