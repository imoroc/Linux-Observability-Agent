#!/bin/bash
# Generates a massive Rx (Receive) network spike by downloading a 100MB dummy file.

echo "[*] Generating download traffic (100MB) to saturate bandwidth..."
wget -O /dev/null http://speedtest.tele2.net/100MB.zip
echo "[✔] Network test completed."
