#!/bin/bash
node backend/server.js &
sleep 10
cd /app
python3 agents/pipeline.py --loop --interval 2 2>&1
