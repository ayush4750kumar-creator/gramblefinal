#!/bin/bash
echo "🚀 start.sh beginning..."
node backend/server.js &
NODE_PID=$!
echo "✅ Node started with PID $NODE_PID"
sleep 10
echo "🐍 Starting Python pipeline..."
python3 agents/pipeline.py --loop --interval 2
echo "❌ Pipeline exited!"
