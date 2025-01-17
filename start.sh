#!/bin/bash

# Function to log messages with timestamps
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Function to check if a process is running
check_process() {
    if ps -p $1 > /dev/null; then
        return 0
    else
        return 1
    fi
}

# Function to wait for backend health
wait_for_backend() {
    local retries=30
    local wait_time=2
    local endpoint="http://localhost:8080/healthz"
    
    log "Waiting for backend to be ready..."
    
    for i in $(seq 1 $retries); do
        if curl -s -f $endpoint > /dev/null; then
            log "Backend is ready!"
            return 0
        fi
        log "Backend not ready yet (attempt $i/$retries)..."
        sleep $wait_time
    done
    
    log "ERROR: Backend failed to become ready"
    return 1
}

# Function to handle cleanup on script exit
cleanup() {
    log "Cleaning up processes..."
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null
    fi
    exit
}

# Set up trap for cleanup
trap cleanup SIGTERM SIGINT

# Environment variables with defaults
: ${PORT:=8501}
: ${FLASK_PORT:=8080}
: ${FLASK_HOST:=0.0.0.0}
: ${STREAMLIT_SERVER_ADDRESS:=0.0.0.0}

log "Starting services with PORT=$PORT"

# Create necessary directories
mkdir -p data
log "Created data directory"

# Start backend service
log "Starting backend service on port $FLASK_PORT..."
python backend/app.py &
BACKEND_PID=$!

# Wait for backend to be healthy
if ! wait_for_backend; then
    log "ERROR: Backend failed to start properly"
    cleanup
    exit 1
fi

log "Backend service started successfully (PID: $BACKEND_PID)"

# Start frontend service
log "Starting frontend service on port $PORT..."
streamlit run frontend/app.py --server.port $PORT --server.address $STREAMLIT_SERVER_ADDRESS &
FRONTEND_PID=$!

# Wait for frontend to start
sleep 5

# Check if frontend started successfully
if ! check_process $FRONTEND_PID; then
    log "ERROR: Frontend failed to start"
    cleanup
    exit 1
fi

log "Frontend service started successfully (PID: $FRONTEND_PID)"

# Monitor both processes
while true; do
    if ! check_process $BACKEND_PID; then
        log "ERROR: Backend process died unexpectedly"
        cleanup
        exit 1
    fi
    
    if ! check_process $FRONTEND_PID; then
        log "ERROR: Frontend process died unexpectedly"
        cleanup
        exit 1
    fi
    
    sleep 10
done