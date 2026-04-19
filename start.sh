#!/bin/bash
node backend/server.js &
sleep 10
echo "PWD: $(pwd)"
echo "LS: $(ls)"
python3 agents/pipeline.py --loop --interval 2 2>&1
