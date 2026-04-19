#!/bin/bash
echo "🚀 start.sh beginning..."
node backend/server.js &
sleep 10
echo "🐍 Testing Python..."
python3 --version 2>&1
echo "🐍 Testing import..."
python3 -c "print('Python OK')" 2>&1
echo "🐍 Starting pipeline..."
cd /app && python3 agents/pipeline.py --loop --interval 2 2>&1 || echo "❌ CRASHED: $?"
