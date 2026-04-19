#!/bin/bash
node backend/server.js &
sleep 10
cd /app
python3 -c "
import sys
sys.path.insert(0, 'agents')
print('Testing imports...')
try:
    import agentX; print('✅ agentX')
except Exception as e: print(f'❌ agentX: {e}')
try:
    import agentY; print('✅ agentY')
except Exception as e: print(f'❌ agentY: {e}')
try:
    import agentZ; print('✅ agentZ')
except Exception as e: print(f'❌ agentZ: {e}')
try:
    import agentO; print('✅ agentO')
except Exception as e: print(f'❌ agentO: {e}')
try:
    import agentP; print('✅ agentP')
except Exception as e: print(f'❌ agentP: {e}')
try:
    import agentGroq; print('✅ agentGroq')
except Exception as e: print(f'❌ agentGroq: {e}')
try:
    import agentH; print('✅ agentH')
except Exception as e: print(f'❌ agentH: {e}')
print('All done!')
" 2>&1
python3 agents/pipeline.py --loop --interval 2 2>&1
