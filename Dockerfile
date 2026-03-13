FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Expose the port Flet runs on
EXPOSE 8080

# Run the app in web mode
CMD ["python", "main.py"]
