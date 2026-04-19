#!/bin/bash
if [ "$SERVICE_TYPE" = "pipeline" ]; then
    echo "🐍 Starting pipeline..."
    cd /app
    python3 agents/pipeline.py --loop --interval 5
else
    echo "🌐 Starting server..."
    node backend/server.js
fi
