FROM python:3.13.4-slim

# Install Node.js (required for Chart.js server-side chart rendering)
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    apt-get purge -y curl && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Chart renderer — install npm deps before copying app code (Docker layer cache)
COPY ./app/chart-renderer/package.json ./app/chart-renderer/
RUN cd app/chart-renderer && npm install --production

# Application code
COPY ./app ./app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80", "--log-level", "debug"]
