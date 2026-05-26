#!/bin/bash
# Simulates a CPU bottleneck by stressing a single core for 30 seconds.

echo "[*] Starting CPU stress test (1 core, 30 seconds)..."
taskset -c 0 stress --cpu 1 --timeout 30s
echo "[✔] CPU test completed."
