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
* **Advanced Application Telemetry:** * Breaks down **HTTPS response latency** across all network layers (DNS, TCP handshake, TLS negotiation, TTFB, and Transfer).
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
 ┣ 📂 src/
 ┃ ┗ 🐍 system_monitor.py
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
Download the project to your local machine:
```bash
git clone [https://github.com/imoroc/Linux-Observability-Agent.git](https://github.com/imoroc/Linux-Observability-Agent.git)
cd Linux-Observability-Agent
```

### 2. Database Setup
Log into your MariaDB/MySQL console as root (`sudo mysql -u root -p`) and set up the database and the required telemetry user:
```sql
CREATE DATABASE ESI_Practica1;
CREATE USER 'elliot'@'localhost' IDENTIFIED BY '2Moronipa.';
GRANT ALL PRIVILEGES ON ESI_Practica1.* TO 'elliot'@'localhost';
FLUSH PRIVILEGES;
```
*Note: The exact SQL scripts to create the tables (`registro_metricas`, `arbol_procesos`, `vecinos_red`, `puertos_activos`) are documented on page 3 of the `docs/technical_report.pdf`.*

### 3. Install Agent Dependencies
Install the required Python libraries for OS inspection and database connection:
```bash
sudo apt update
pip3 install psutil mysql-connector-python
```

### 4. Run the Telemetry Agent
You can test the agent manually in your terminal to verify data ingestion:
```bash
python3 src/system_monitor.py
```
*(For a production-like deployment, configure it as a background daemon using `systemd`. Instructions for the `monitor.service` configuration are detailed in the `docs/technical_report.pdf`).*

### 5. Visualizing Data (Grafana)
1. Open your Grafana web interface.
2. Go to **Connections > Data Sources** and add **MySQL**.
3. Point it to `localhost:3306`, Database: `ESI_Practica1`, User: `elliot`, Password: `2Moronipa.`.
4. The telemetry agent updates the historical tables (Time-Series) and truncates the dynamic tables (for ECharts Network Topology) every 60 seconds.

---

## Chaos Engineering (Stress Tests)

You can validate the resilience of the observability stack and trigger visual spikes in the Grafana dashboards by executing the stress testing suite.

Before running, grant execution permissions to the scripts:
```bash
cd stress-tests/
chmod +x *.sh
```

**Example: Simulating a Database Concurrency Overload**
This will simulate 50 concurrent users blasting the database with SQL queries, spiking the QPS (Queries Per Second) panel.
```bash
./stress_mysql.sh
[*] Preparing MySQL/MariaDB stress test...
Enter the database password for user 'elliot': 
[*] Launching mysqlslap (50 concurrent connections, 10 iterations)...
[✔] Database test completed.
```

---

### 👨‍💻 Authors

Iván Moro Cienfuegos, Pablo March Ortega and Nicolás Reyes Gutiérrez
