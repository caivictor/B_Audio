#!/bin/bash

# Start the WebCaptioner Local Relay Client and UI 
# pointing to the remote STT server at 192.168.0.30

# Kill any existing process running on port 8765 to prevent "Address already in use" errors
echo "Cleaning up any old relay server processes..."
fuser -k 8765/tcp 2>/dev/null || true

# Activate the local virtual environment
source .venv/bin/activate

# Execute the local client 
echo "Starting WebCaptioner UI and local relay..."
python3 client/main.py --remote-url ws://192.168.0.30:8000/transcribe
