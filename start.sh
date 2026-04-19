#!/bin/bash
node backend/server.js &
sleep 10
python3 agents/pipeline.py --loop --interval 2
