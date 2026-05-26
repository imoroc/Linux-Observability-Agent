#!/bin/bash
# Simulates 50 concurrent users querying the database to spike QPS and thread count.

echo "[*] Preparing MySQL/MariaDB stress test..."
read -s -p "Enter the database password for user 'elliot': " DB_PASS
echo ""

echo "[*] Launching mysqlslap (50 concurrent connections, 10 iterations)..."
mysqlslap --user=elliot --password="$DB_PASS" --concurrency=50 --iterations=10 --auto-generate-sql

echo "[✔] Database test completed."
