FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy all requirements files
COPY backend/requirements.txt backend-requirements.txt
COPY frontend/requirements.txt frontend-requirements.txt

# Install dependencies
RUN pip install --no-cache-dir -r backend-requirements.txt
RUN pip install --no-cache-dir -r frontend-requirements.txt

# Copy the application
COPY . .

# Make directory for data
RUN mkdir -p data

# Create and make start script executable
COPY start.sh .
RUN chmod +x start.sh

# Expose both ports
EXPOSE 8080
EXPOSE 8501

# Start the application
CMD ["./start.sh"]