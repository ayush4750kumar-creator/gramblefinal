#!/bin/bash
echo "🌐 Starting server..."
node backend/server.js &

echo "🐍 Starting pipeline..."
python3 agents/pipeline.py --loop --interval 5

wait
