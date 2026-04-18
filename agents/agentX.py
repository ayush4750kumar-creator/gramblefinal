"""
agentX.py — Orchestrator
Runs Agents A–G concurrently, collects results, reports totals.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import concurrent.futures, time
from datetime import datetime

import agentA, agentB, agentC, agentD, agentE, agentF, agentG

AGENTS = [
    ("A — After-Market Company News",    agentA.run),
    ("B — Pre-Market Analysis",          agentB.run),
    ("C — After-Session Impact",         agentC.run),
    ("D — Official Statements",          agentD.run),
    ("E — Political/Global",             agentE.run),
    ("F — Exchange & Market",            agentF.run),
    ("G — Trading Session Live",         agentG.run),
]

def run(parallel: bool = True) -> int:
    print("\n" + "═" * 55)
    print(f"🤖 AgentX — Orchestrator  [{datetime.now().strftime('%d %b %Y, %H:%M:%S')}]")
    print("═" * 55)
    t0 = time.time()
    total = 0

    if parallel:
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
            futures = {ex.submit(fn): name for name, fn in AGENTS}
            for fut in concurrent.futures.as_completed(futures):
                name = futures[fut]
                try:
                    saved = fut.result()
                    total += saved
                except Exception as e:
                    print(f"  ✗ Agent {name} crashed: {e}")
    else:
        for name, fn in AGENTS:
            try:
                saved = fn()
                total += saved
            except Exception as e:
                print(f"  ✗ Agent {name} crashed: {e}")

    elapsed = time.time() - t0
    print(f"\n✅ AgentX complete — {total} new articles saved in {elapsed:.1f}s")
    print("═" * 55)
    return total

if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--sequential', action='store_true', help='Run agents one by one')
    args = p.parse_args()
    run(parallel=not args.sequential)
