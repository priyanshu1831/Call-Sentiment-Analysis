FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
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

# Copy both applications
COPY backend ./backend
COPY frontend ./frontend

# Make directory for data
RUN mkdir -p data

# Create and make start script executable
COPY start.sh .
RUN chmod +x start.sh

# Set environment variables
ENV PORT=8501
ENV BACKEND_URL=http://call-sentiment-analysis.railway.internal:8080
ENV FLASK_APP=backend/app.py
ENV FLASK_ENV=production
ENV FLASK_PORT=8080
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV CORS_ALLOW_ORIGIN=*

# Expose both ports
EXPOSE 8080
EXPOSE 8501

# Start both services using the start script
CMD ["./start.sh"]