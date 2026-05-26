#!/bin/bash
# Simulates a process-spawning anomaly (Fork bomb lite).

echo "[*] Spawning 50 background processes (Sleep 60s)..."
for i in {1..50}; do
    sleep 60 &
done
echo "[✔] Processes spawned. Check the Grafana process tree dashboard."
