#!/usr/bin/env bash
# Heavy-test wrapper: one at a time on nigian (flock), 15-minute cap, full logs in logs/, trimmed output only.
set -u; cd "$(dirname "$0")/.."; mkdir -p logs; export PW="${PW:-/home/nig/qa-wwtp0313r2/node_modules/playwright}"
PORT=8790; python3 tools/serve.py $PORT > logs/serve.log 2>&1 & SP=$!; trap 'kill $SP 2>/dev/null' EXIT
for i in $(seq 1 40); do curl -s -o /dev/null http://127.0.0.1:$PORT/ && break; sleep 0.25; done
flock /tmp/nigian-heavy-tests.lock timeout 900 bash -c "node tests/engine.mjs > logs/engine.log 2>&1; e=\$?; node tests/smoke.mjs http://127.0.0.1:$PORT/ > logs/smoke.log 2>&1; s=\$?; exit \$((e|s))"; rc=$?
echo "--- engine (tail)"; tail -n 8 logs/engine.log; echo "--- smoke (tail)"; tail -n 40 logs/smoke.log | cut -c1-300; echo "--- grep"; grep -iE "error|warn|FAIL" logs/smoke.log logs/engine.log | grep -v "errors: 0" | head -20; echo "exit $rc"; exit $rc
