"""
System Metrics Collection Agent
-----------------------------------------
This script monitors real-time hardware status, network activity, 
services (SSH, HTTP), and database health (MySQL/MariaDB). 
It persistently stores the historical data in a relational database 
for subsequent visualization and observability via Grafana.
"""

import psutil
import time
import mysql.connector
from datetime import datetime
import sys
import subprocess

# ==========================================
# GENERAL CONFIGURATION & GLOBAL VARIABLES
# ==========================================
# Safety limit: If disk space drops below 500MB, the script halts to prevent OS collapse.
MIN_FREE_DISK_MB = 500  
POLL_INTERVAL_SECONDS = 60  # Data refresh frequency

DB_CONFIG = {
    'host': 'localhost',
    'user': 'elliot',
    'password': '2Moronipa.',
    'database': 'ESI_Practica1'
}

# Dictionary to store the previous MySQL state. 
# Required to calculate deltas/speeds (e.g., translating "Total Queries" into "Queries per Second").
LAST_MYSQL_STATE = {
    'questions': None,
    'bytes_rx': None,
    'bytes_tx': None,
    'timestamp': None
}

# ==========================================
# CORE & FAILSAFE FUNCTIONS
# ==========================================

def connect_to_db():
    """Establishes and returns a connection to the MariaDB/MySQL database."""
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except Exception as e:
        print(f"Error connecting to the database: {e}")
        sys.exit(1)

def verify_safe_disk_space():
    """Failsafe mechanism ('Kill Switch'). Halts the daemon if disk space is critically low."""
    disk_usage = psutil.disk_usage('/')
    free_space_mb = disk_usage.free / (1024 * 1024)
    if free_space_mb < MIN_FREE_DISK_MB:
        print(f"CRITICAL: Low disk space detected ({free_space_mb:.2f} MB). Halting execution.")
        sys.exit(1)

def truncate_table(connection, table_name):
    """Completely empties a dynamic table (TRUNCATE) to overwrite its current state."""
    cursor = connection.cursor()
    try:
        cursor.execute(f"TRUNCATE TABLE {table_name}")
        connection.commit()
    except Exception:
        pass
    finally:
        cursor.close()


# ==========================================
# SPECIFIC METRIC COLLECTORS
# ==========================================

def get_http_latency_breakdown(url="https://www.google.com"):
    """
    Performs an HTTP request using 'curl' and breaks down the latency 
    across the network layers (DNS, TCP, TLS, Server Processing, Transfer).
    """
    try:
        # Specific curl format to extract time metrics in seconds
        curl_format = "%{time_namelookup},%{time_connect},%{time_appconnect},%{time_starttransfer},%{time_total}"
        cmd = ['curl', '-o', '/dev/null', '-s', '-w', curl_format, url]
        output = subprocess.check_output(cmd, universal_newlines=True)
        
        # Convert seconds to milliseconds (x 1000)
        t = [float(x) * 1000 for x in output.strip().split(',')]
        
        # Calculate the time difference between each phase (waterfall steps)
        return {
            'dns_ms': max(0, t[0]), 
            'tcp_ms': max(0, t[1] - t[0]),
            'tls_ms': max(0, t[2] - t[1]), 
            'server_ms': max(0, t[3] - t[2]),
            'transfer_ms': max(0, t[4] - t[3])
        }
    except Exception:
        return {'dns_ms': 0.0, 'tcp_ms': 0.0, 'tls_ms': 0.0, 'server_ms': 0.0, 'transfer_ms': 0.0}

def get_uptime_and_ssh_sessions():
    """Calculates system uptime (in hours) and counts active SSH connections."""
    data = {}
    data['uptime_horas'] = (time.time() - psutil.boot_time()) / 3600.0
    active_ssh_connections = 0
    try:
        # Filter TCP sockets looking for port 22 in ESTABLISHED state
        for conn in psutil.net_connections(kind='tcp'):
            if conn.laddr.port == 22 and conn.status == 'ESTABLISHED':
                active_ssh_connections += 1
    except psutil.AccessDenied:
        pass
    
    data['sesiones_ssh'] = active_ssh_connections
    return data

def get_mysql_metrics(connection):
    """
    Extracts internal MariaDB variables. 
    Mathematically calculates Queries Per Second (QPS) and Bandwidth (KB/s).
    """
    global LAST_MYSQL_STATE
    metrics = {
        'mysql_qps': 0.0, 'mysql_threads': 0,
        'mysql_slow_queries': 0, 'mysql_aborted_connects': 0,
        'mysql_bytes_rx_ps': 0.0, 'mysql_bytes_tx_ps': 0.0
    }

    try:
        cursor = connection.cursor()
        # Request global engine status
        cursor.execute("SHOW GLOBAL STATUS WHERE Variable_name IN ('Threads_connected', 'Slow_queries', 'Aborted_connects', 'Questions', 'Bytes_received', 'Bytes_sent')")
        results = dict(cursor.fetchall())

        # Direct / static metrics
        metrics['mysql_threads'] = int(results.get('Threads_connected', 0)) 
        metrics['mysql_slow_queries'] = int(results.get('Slow_queries', 0)) 
        metrics['mysql_aborted_connects'] = int(results.get('Aborted_connects', 0)) 

        # Cumulative historical variables (require speed calculation)
        current_q = int(results.get('Questions', 0))
        current_rx = int(results.get('Bytes_received', 0))
        current_tx = int(results.get('Bytes_sent', 0))
        current_time = time.time()

        # If we have data from the previous execution, calculate the Delta (Speed)
        if LAST_MYSQL_STATE['timestamp'] is not None:
            delta_t = current_time - LAST_MYSQL_STATE['timestamp']
            if delta_t > 0:
                # QPS = (Current Queries - Previous Queries) / Elapsed Seconds
                metrics['mysql_qps'] = max(0, (current_q - LAST_MYSQL_STATE['questions']) / delta_t)
                # Divide by 1024 to convert Bytes to Kilobytes
                metrics['mysql_bytes_rx_ps'] = max(0, (current_rx - LAST_MYSQL_STATE['bytes_rx']) / delta_t / 1024)
                metrics['mysql_bytes_tx_ps'] = max(0, (current_tx - LAST_MYSQL_STATE['bytes_tx']) / delta_t / 1024)

        # Save the current state for the next iteration
        LAST_MYSQL_STATE = {
            'questions': current_q, 
            'bytes_rx': current_rx, 
            'bytes_tx': current_tx, 
            'timestamp': current_time
        }
        cursor.close()
    except Exception as e:
        print(f"Error extracting MySQL metrics: {e}")

    return metrics


# ==========================================
# DYNAMIC TABLE FUNCTIONS (Maps and Graphs)
# ==========================================

def update_active_tcp_ports(connection):
    """Scans the machine and records local TCP ports currently in use and their state."""
    active_ports = {}
    timestamp_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    try:
        for conn in psutil.net_connections(kind='tcp'):
            if conn.laddr:
                port = conn.laddr.port
                status = conn.status
                # The dictionary key is a tuple (port, status) to separate data based on whether 
                # connections are in LISTEN or ESTABLISHED states.
                key = (port, status)
                # Increment the connection counter
                active_ports[key] = active_ports.get(key, 0) + 1
    except psutil.AccessDenied:
        pass

    if active_ports:
        insert_data = [(p, s, c, timestamp_str) for (p, s), c in active_ports.items()]
        cursor = connection.cursor()
        try:
            cursor.execute("TRUNCATE TABLE puertos_activos")
            query = "INSERT INTO puertos_activos (puerto, estado, cantidad, timestamp) VALUES (%s, %s, %s, %s)"
            cursor.executemany(query, insert_data)
            connection.commit()
        except Exception as e:
            print(f"Error updating active TCP ports: {e}")
        finally:
            cursor.close()

def update_network_neighbors(connection):
    """Reads the OS ARP table to map devices on the local network."""
    neighbors = []
    timestamp_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        with open('/proc/net/arp', 'r') as f:
            next(f)  # Skip the header
            for line in f:
                parts = line.split()
                # Discard zeroed and invalid MAC addresses
                if len(parts) >= 4 and parts[3] != "00:00:00:00:00:00":
                    neighbors.append((parts[0], parts[3], timestamp_str))
    except Exception:
        pass

    if neighbors:
        cursor = connection.cursor()
        try:
            cursor.execute("TRUNCATE TABLE vecinos_red")
            query = "INSERT INTO vecinos_red (ip, mac, timestamp) VALUES (%s, %s, %s)"
            cursor.executemany(query, neighbors)
            connection.commit()
        except Exception:
            pass
        finally:
            cursor.close()

def update_process_tree(connection):
    """Iterates through all active processes, discovers their parent processes, and stores the topology."""
    processes = []
    pid_list = []
    raw_data = []
    timestamp_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Step 1: Raw data collection
    for proc in psutil.process_iter(['pid', 'ppid', 'name', 'cpu_percent']):
        try:
            pid = proc.info['pid']
            ppid = proc.info['ppid']
            name = str(proc.info['name'])[:95]
            cpu = float(proc.info['cpu_percent']) if proc.info['cpu_percent'] is not None else 0.0

            if pid > 0:
                pid_list.append(pid)
                raw_data.append((pid, ppid, name, cpu))
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    # Step 2: Broken tree correction (Orphaned processes)
    for pid, ppid, name, cpu in raw_data:
        safe_parent = ppid
        # If the parent is dead or missing, attach the process to 'systemd' (pid 1) to prevent ECharts rendering failures
        if ppid is None or ppid not in pid_list:
            safe_parent = 1 if pid != 1 else 0
        
        processes.append((pid, safe_parent, name, cpu, timestamp_str))

    # Step 3: Database Insertion
    cursor = connection.cursor()
    try:
        cursor.execute("TRUNCATE TABLE arbol_procesos")
        query = "INSERT INTO arbol_procesos (pid, ppid, nombre, cpu_uso, timestamp) VALUES (%s, %s, %s, %s, %s)"
        cursor.executemany(query, processes)
        connection.commit()
    except Exception:
        pass
    finally:
        cursor.close()


# ==========================================
# MAIN PIPELINE & ASSEMBLY
# ==========================================

def collect_all_metrics(connection):
    """Assembles the central dictionary containing all hardware and system metrics."""
    metrics = {}

    # --- CPU ---
    metrics['cpu_percent'] = psutil.cpu_percent(interval=None)
    cores = psutil.cpu_percent(percpu=True)
    metrics['cpu_core_1'] = cores[0] if len(cores) > 0 else 0.0
    metrics['cpu_core_2'] = cores[1] if len(cores) > 1 else 0.0

    # --- Memory ---
    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()
    metrics['ram_usada_mb'] = memory.used / (1024 * 1024)
    metrics['ram_disponible_mb'] = memory.available / (1024 * 1024)
    metrics['ram_percent'] = memory.percent
    metrics['swap_usada_mb'] = swap.used / (1024 * 1024)

    # --- Disk ---
    disk = psutil.disk_usage('/')
    disk_io = psutil.disk_io_counters()
    metrics['disco_count_read'] = disk_io.read_count
    metrics['disco_count_write'] = disk_io.write_count
    metrics['disco_usado_porcentaje'] = disk.percent
    metrics['disco_usado_bytes'] = disk.used

    # --- Network ---
    net_io = psutil.net_io_counters()
    metrics['red_bytes_enviados'] = net_io.bytes_sent
    metrics['red_bytes_recibidos'] = net_io.bytes_recv

    # --- System ---
    metrics['num_procesos'] = len(psutil.pids())
    try:
        load1, load5, load15 = psutil.getloadavg()
        metrics['load_1m'] = load1
    except AttributeError:
        metrics['load_1m'] = 0.0

    # Integrate external advanced metrics
    metrics.update(get_http_latency_breakdown())
    metrics.update(get_uptime_and_ssh_sessions())
    metrics.update(get_mysql_metrics(connection))

    return metrics

def insert_metrics_to_db(connection, metrics):
    """Inserts the complete historical dictionary into the main relational table."""
    cursor = connection.cursor()
    query = """
        INSERT INTO registro_metricas
        (timestamp, cpu_percent, cpu_core_1, cpu_core_2 , ram_usada_mb, ram_disponible_mb, ram_percent,
         swap_usada_mb, disco_count_read, disco_count_write, disco_usado_porcentaje, red_bytes_enviados,
         red_bytes_recibidos, num_procesos, load_1m, disco_usado_bytes,
         sesiones_ssh, uptime_horas, dns_ms, tcp_ms, tls_ms, server_ms, transfer_ms,
         mysql_qps, mysql_threads, mysql_slow_queries, mysql_aborted_connects, mysql_bytes_rx_ps, mysql_bytes_tx_ps)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    timestamp_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    values = (
        timestamp_str,
        metrics['cpu_percent'], metrics['cpu_core_1'], metrics['cpu_core_2'],
        metrics['ram_usada_mb'], metrics['ram_disponible_mb'], metrics['ram_percent'],
        metrics['swap_usada_mb'], metrics['disco_count_read'], metrics['disco_count_write'],
        metrics['disco_usado_porcentaje'], metrics['red_bytes_enviados'], metrics['red_bytes_recibidos'],
        metrics['num_procesos'], metrics['load_1m'], metrics['disco_usado_bytes'],
        metrics['sesiones_ssh'], metrics['uptime_horas'],
        metrics['dns_ms'], metrics['tcp_ms'], metrics['tls_ms'], metrics['server_ms'], metrics['transfer_ms'],
        metrics['mysql_qps'], metrics['mysql_threads'],
        metrics['mysql_slow_queries'], metrics['mysql_aborted_connects'],
        metrics['mysql_bytes_rx_ps'], metrics['mysql_bytes_tx_ps']
    )

    try:
        cursor.execute(query, values)
        connection.commit()
    except Exception as e:
        print(f"Error inserting metrics: {e}")
    finally:
        cursor.close()

# ==========================================
# EXECUTION LOOP (ENTRY POINT)
# ==========================================

if __name__ == "__main__":
    db_conn = connect_to_db()
    print("Initializing advanced metrics collection...")

    # Purge dynamic tables in case of an abrupt machine reboot
    truncate_table(db_conn, "registro_metricas")
    truncate_table(db_conn, "arbol_procesos")
    truncate_table(db_conn, "puertos_activos")

    # Prime the CPU metric (the first call to psutil always returns 0)
    psutil.cpu_percent(interval=1)

    try:
        while True:
            # 1. Survival Check
            verify_safe_disk_space()

            # 2. Collect and Insert Main Historical Data
            system_data = collect_all_metrics(db_conn)
            insert_metrics_to_db(db_conn, system_data)

            # 3. Collect Dynamic Graph Data
            update_process_tree(db_conn)
            update_network_neighbors(db_conn)
            update_active_tcp_ports(db_conn) 

            print(f"[{datetime.now().strftime('%H:%M:%S')}] Telemetry data inserted successfully.")
            
            # 4. Sleep until the next polling cycle
            time.sleep(POLL_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        print("\nCollection halted by the user. Closing connections...")
    finally:
        # Always close connections to prevent memory leaks
        if db_conn.is_connected():
            db_conn.close()
            print("Database connection closed gracefully.")
