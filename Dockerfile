# Dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements files
COPY backend/requirements.txt backend-requirements.txt
COPY frontend/requirements.txt frontend-requirements.txt

# Install dependencies
RUN pip install --no-cache-dir -r backend-requirements.txt \
    && pip install --no-cache-dir -r frontend-requirements.txt

# Copy the application
COPY . .

# Create start script
RUN echo '#!/bin/bash\npython backend/app.py & streamlit run frontend/app.py' > start.sh
RUN chmod +x start.sh

# Expose ports
EXPOSE 8501
EXPOSE 5000

# Start both services
CMD ["./start.sh"]