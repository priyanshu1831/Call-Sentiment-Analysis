FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements files
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application
COPY . .

# Make directory for data
RUN mkdir -p data

# Create start script
RUN echo '#!/bin/bash\n\
python backend/app.py & \n\
streamlit run frontend/app.py --server.port $PORT --browser.serverAddress 0.0.0.0\n\
wait' > start.sh

RUN chmod +x start.sh

# Expose port
ENV PORT=8501

# Start the application
CMD ["./start.sh"]