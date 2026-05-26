#!/bin/bash
# Simulates an I/O spike and storage alert by creating and deleting a 500MB file.

echo "[*] Writing a 500MB dummy file to disk to saturate I/O..."
dd if=/dev/zero of=heavyFile.img bs=1M count=500 status=progress
echo "[*] File created. Holding state for 20 seconds..."
sleep 20
echo "[*] Cleaning up the dummy file..."
rm heavyFile.img
echo "[✔] Disk I/O test completed."
