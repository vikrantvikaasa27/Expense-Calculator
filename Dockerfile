FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for Pillow and matplotlib
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files first for better caching
COPY pyproject.toml .
COPY README.md .

# Install dependencies
RUN pip install --no-cache-dir .

# Copy application code
COPY . .

# Run the bot
CMD ["python", "-m", "app.main"]
