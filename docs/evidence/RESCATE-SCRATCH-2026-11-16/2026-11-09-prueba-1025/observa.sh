#!/bin/bash
# Observa el kernel 7.0.0-1025 con carga de GPU real. Sale con rc=3 al primer indicio de falla; rc=0 si cumple el tiempo limpio.
DUR=${1:-6000}; OUT=$HOME/scratch/blackbox/2026-11-09-prueba-1025; FIRMAS='rpcRecvPoll|Xid|Oops|BUG:|hung task|soft lockup|NVRM.*(timed|fail|Out of memory)'
t0=$(date +%s); n=0
echo "inicio $(date -Is) kernel $(uname -r)" > $OUT/log.txt
while [ $(( $(date +%s) - t0 )) -lt $DUR ]; do
  # carga: 4 peticiones de chat en paralelo, ~300 tokens cada una
  for i in 1 2 3 4; do
    curl -s -m 120 http://127.0.0.1:8000/v1/chat/completions -H 'Content-Type: application/json' \
      -d '{"model":"nemotron-local","max_tokens":300,"messages":[{"role":"user","content":"Explica en detalle como funciona un compilador de principio a fin."}]}' -o /dev/null -w '%{http_code} ' >> $OUT/carga.txt &
  done; wait; echo >> $OUT/carga.txt
  n=$((n+1))
  f=$(journalctl -k -b --no-pager 2>/dev/null | grep -c -E -i "$FIRMAS")
  g=$(nvidia-smi --query-gpu=temperature.gpu,power.draw,utilization.gpu,memory.used --format=csv,noheader 2>&1 | head -1)
  echo "$(date +%T) ronda=$n firmas=$f gpu=[$g] mem_avail_mb=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)" >> $OUT/log.txt
  if [ "$f" != "0" ]; then echo "FALLA firmas=$f" >> $OUT/log.txt; journalctl -k -b --no-pager | grep -E -i "$FIRMAS" | head -20 >> $OUT/log.txt; exit 3; fi
  sleep 25
done
echo "fin limpio $(date -Is) rondas=$n" >> $OUT/log.txt; exit 0
