#!/bin/bash
if [ "$SERVICE_TYPE" = "pipeline" ]; then
    echo "🐍 Starting pipeline..."
    python3 agents/pipeline.py --loop --interval 2
else
    echo "🌐 Starting server..."
    node backend/server.js
fi
