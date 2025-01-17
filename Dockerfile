FROM python:3.9-slim

WORKDIR /app

# Install system dependencies including curl for health checks
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy backend and frontend requirements separately
COPY backend/requirements.txt ./backend/requirements.txt
COPY frontend/requirements.txt ./frontend/requirements.txt

# Install dependencies for both services
RUN pip install --no-cache-dir -r backend/requirements.txt \
    && pip install --no-cache-dir -r frontend/requirements.txt

# Create directory structure
RUN mkdir -p backend frontend data

# Copy both applications
COPY backend ./backend
COPY frontend ./frontend

# Create and make start script executable
COPY start.sh .
RUN chmod +x start.sh

# Set environment variables
ENV PORT=8501
ENV BACKEND_URL=http://localhost:8080
ENV FLASK_APP=backend/app.py
ENV FLASK_ENV=production
ENV FLASK_PORT=8080
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV CORS_ALLOW_ORIGIN=*

# Expose both ports
EXPOSE 8080
EXPOSE 8501

# Health check for the backend service
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8080/healthz || exit 1

# Start both services using the start script
CMD ["./start.sh"]