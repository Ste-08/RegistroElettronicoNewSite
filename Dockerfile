FROM python:3.11-slim

WORKDIR /app

# Install system dependencies needed by Flet web
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libsm6 libxrender1 libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Render sets PORT at runtime (default 10000); expose it
EXPOSE 10000

# Run Flet in web/server mode
CMD ["python", "main.py"]
