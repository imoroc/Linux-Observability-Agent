#!/bin/bash
# Forces RAM usage to the limit to trigger swap partition activity.

echo "[*] Starting RAM saturation test (1GB, 60 seconds)..."
stress --vm 2 --vm-bytes 1G --timeout 60s
echo "[✔] RAM and Swap test completed."
