# Enterprise Linux Observability & Chaos Engineering

<div align="center">

  ![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
  ![Grafana](https://img.shields.io/badge/Grafana-F46800?style=for-the-badge&logo=grafana&logoColor=white)
  ![MariaDB](https://img.shields.io/badge/MariaDB-003545?style=for-the-badge&logo=mariadb&logoColor=white)
  ![Linux](https://img.shields.io/badge/Linux-FCC624?style=for-the-badge&logo=linux&logoColor=black)
  ![Bash](https://img.shields.io/badge/Chaos_Engineering-4EAA25?style=for-the-badge&logo=gnu-bash&logoColor=white)
  ![SRE](https://img.shields.io/badge/Architecture-SRE_%26_Telemetry-blue?style=for-the-badge)

</div>

> **ABOUT THIS PROJECT:**
> This repository contains a custom-built **Telemetry Agent and Observability Stack** designed to monitor Linux OS performance, dynamic network topologies, and database health in real-time.
>
> Unlike standard out-of-the-box exporters, this system implements a native Python daemon directly integrated with `systemd`, paired with a **Chaos Engineering** testing suite to simulate and visualize critical infrastructure bottlenecks.

<div align="center">
  <img width="800" src="assets/dashboard.png" alt="Grafana Main Dashboard" />
</div>

---

## Architecture & Key Features

* **Custom `systemd` Daemon:** The Python agent (`system_monitor.py`) runs as a highly available background service, ensuring automated recovery and continuous telemetry data ingestion into a relational database.
* **Deep OS & Hardware Metrics:** Tracks precise CPU/Core loads, RAM/Swap usage boundaries, Disk I/O operations, and system load averages (`psutil`).
* **Dynamic Network Topology (ECharts):** Dynamically extracts the OS ARP table and maps local network nodes. Monitors all active TCP socket states (LISTEN vs. ESTABLISHED).
* **Advanced Application Telemetry:**
  * Breaks down **HTTPS response latency** across all network layers (DNS, TCP handshake, TLS negotiation, TTFB, and Transfer).
  * Extracts internal **MariaDB/MySQL health metrics** (Queries Per Second, TX/RX Bandwidth, Active Threads).
* **Chaos Engineering Suite:** Includes 6 specialized Bash scripts to simulate high-load operational scenarios (CPU saturation, RAM swap-thrashing, Network I/O spikes, and Database concurrency overload).

---

## Project Structure

```text
Linux-Observability-Agent
 ┣ 📂 assets/
 ┃ ┗ 🖼️ dashboard.png
 ┣ 📂 docs/
 ┃ ┣ 📜 presentation_slides.pdf
 ┃ ┗ 📜 technical_report.pdf
 ┣ 📂 grafana/
 ┃ ┗ 📜 dashboard.json
 ┣ 📂 src/
 ┃ ┣ 🐍 system_monitor.py
 ┃ ┗ 📜 monitor.service
 ┗ 📂 stress-tests/
   ┣ 📜 stress_cpu.sh
   ┣ 📜 stress_disk.sh
   ┣ 📜 stress_mysql.sh
   ┣ 📜 stress_network.sh
   ┣ 📜 stress_processes.sh
   ┗ 📜 stress_ram.sh
```

---

## Getting Started & Reproduction Guide

Follow these steps to deploy the telemetry agent and replicate this observability stack on your own Linux environment (Ubuntu/Debian recommended).

### Prerequisites

Ensure you have the following installed on your Linux machine:

* Python 3 & `pip`
* MariaDB or MySQL Server
* Grafana

### 1. Clone the Repository

```bash
git clone https://github.com/imoroc/Linux-Observability-Agent.git
cd Linux-Observability-Agent
```

### 2. Database Setup

Log into your MariaDB/MySQL console as root (`sudo mysql -u root -p`) and run the following to create the database, user, and all required tables:

```sql
CREATE DATABASE ESI_Practica1;
CREATE USER 'elliot'@'localhost' IDENTIFIED BY '2Moronipa.';
GRANT ALL PRIVILEGES ON ESI_Practica1.* TO 'elliot'@'localhost';
FLUSH PRIVILEGES;

USE ESI_Practica1;

-- Main historical metrics table (time-series)
CREATE TABLE registro_metricas (
  id INT AUTO_INCREMENT PRIMARY KEY,
  timestamp DATETIME NOT NULL,
  cpu_percent FLOAT, cpu_core_1 FLOAT, cpu_core_2 FLOAT,
  ram_usada_mb FLOAT, ram_disponible_mb FLOAT, ram_percent FLOAT, swap_usada_mb FLOAT,
  disco_count_read BIGINT, disco_count_write BIGINT, disco_usado_porcentaje FLOAT,
  disco_usado_bytes BIGINT,
  red_bytes_enviados BIGINT, red_bytes_recibidos BIGINT,
  num_procesos INT, load_1m FLOAT,
  sesiones_ssh INT, uptime_horas FLOAT,
  dns_ms FLOAT, tcp_ms FLOAT, tls_ms FLOAT, server_ms FLOAT, transfer_ms FLOAT,
  mysql_qps FLOAT, mysql_threads INT, mysql_slow_queries INT, mysql_aborted_connects INT,
  mysql_bytes_rx_ps FLOAT, mysql_bytes_tx_ps FLOAT
);

-- Dynamic snapshot tables (truncated on every iteration)
CREATE TABLE arbol_procesos (
  pid INT, ppid INT, nombre VARCHAR(100), cpu_uso FLOAT, timestamp DATETIME
);
CREATE TABLE vecinos_red (
  ip VARCHAR(15), mac VARCHAR(17), timestamp DATETIME
);
CREATE TABLE puertos_activos (
  puerto INT, estado VARCHAR(20), cantidad INT, timestamp DATETIME
);
```

### 3. Install Agent Dependencies

```bash
sudo apt update
pip3 install psutil mysql-connector-python
```

### 4. Run the Telemetry Agent (Manual / Test Mode)

To quickly verify data ingestion is working correctly:

```bash
python3 src/system_monitor.py
```

### 5. Deploy as a `systemd` Daemon (Production)

For a production deployment, the agent runs as a persistent background service that survives reboots and auto-restarts on failure.

First, configure the service file by replacing the placeholders with your actual username and the absolute path to the cloned repository. You can do this automatically with:

```bash
sed -i "s|YOUR_USER|$USER|g; s|/path/to/Linux-Observability-Agent|$(pwd)|g" src/monitor.service
```

Then install and enable the service:

```bash
sudo cp src/monitor.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable monitor.service
sudo systemctl start monitor.service
```

Verify it is running:

```bash
sudo systemctl status monitor.service
```

### 6. Visualizing Data (Grafana)

**Import the pre-built dashboard:**

1. Open your Grafana web interface.
2. Navigate to **Dashboards > Import**.
3. Upload the `grafana/dashboard.json` file.
4. Go to **Connections > Data Sources**, add a **MySQL** data source and point it to `localhost:3306`, Database: `ESI_Practica1`, User: `elliot`, Password: `2Moronipa.`.
5. Select it as the data source for the imported dashboard and click **Import**.

The agent updates the historical time-series tables and truncates the dynamic snapshot tables (Network Topology, Process Tree, TCP Ports) every 60 seconds.

---

## Chaos Engineering (Stress Tests)

Validate the resilience of the observability stack and trigger visual spikes in the Grafana dashboards by executing the stress testing suite.

Grant execution permissions before running:

```bash
cd stress-tests/
chmod +x *.sh
```

| Script | What it simulates |
|---|---|
| `stress_cpu.sh` | Saturates a single CPU core to 100% for 30 seconds |
| `stress_ram.sh` | Forces RAM beyond physical limits, activating Swap |
| `stress_disk.sh` | Writes a 500 MB file to spike Disk I/O and storage alerts |
| `stress_network.sh` | Downloads a large file to `/dev/null` generating pure Rx traffic |
| `stress_processes.sh` | Spawns 50 background processes to spike the process count |
| `stress_mysql.sh` | Simulates 50 concurrent DB users to spike QPS |

**Example — Database Concurrency Overload:**

```bash
./stress_mysql.sh
[*] Preparing MySQL/MariaDB stress test...
Enter the database password for user 'elliot': 
[*] Launching mysqlslap (50 concurrent connections, 10 iterations)...
[✔] Database test completed.
```

---

### 👨‍💻 Authors

**Iván Moro Cienfuegos, Pablo March Ortega and Nicolás Reyes Gutiérrez.**
