import random
import time
import threading
import logging
import os
import json
import base64
from urllib.request import Request, urlopen
from http.server import HTTPServer, BaseHTTPRequestHandler
from prometheus_client import (
    start_http_server,
    Counter,
    Gauge,
    Histogram,
    Info,
    generate_latest,
    CONTENT_TYPE_LATEST,
)


class LokiHandler(logging.Handler):
    """Push log entries directly to Grafana Cloud Loki via HTTP."""

    def __init__(self):
        super().__init__()
        self.url = os.environ.get("GRAFANA_LOGS_URL", "")
        username = os.environ.get("GRAFANA_LOGS_USERNAME", "")
        token = os.environ.get("GRAFANA_CLOUD_TOKEN", "")
        if username and token:
            cred = base64.b64encode(f"{username}:{token}".encode()).decode()
            self.auth = f"Basic {cred}"
        else:
            self.auth = ""
        self.batch = []
        self.lock = threading.Lock()
        self._start_flush_thread()

    def _start_flush_thread(self):
        def flusher():
            while True:
                time.sleep(5)
                self.flush()
        t = threading.Thread(target=flusher, daemon=True)
        t.start()

    def emit(self, record):
        if not self.url or not self.auth:
            return
        ts = str(int(record.created * 1e9))
        level = record.levelname.lower()
        msg = self.format(record)
        with self.lock:
            self.batch.append((ts, msg, level))

    def flush(self):
        with self.lock:
            if not self.batch:
                return
            entries = self.batch[:]
            self.batch.clear()

        by_level = {}
        for ts, msg, level in entries:
            by_level.setdefault(level, []).append([ts, msg])

        streams = []
        for level, values in by_level.items():
            streams.append({
                "stream": {
                    "job": "network-generator",
                    "compose_service": "network-generator",
                    "level": level,
                },
                "values": values,
            })

        payload = json.dumps({"streams": streams}).encode()
        req = Request(self.url, data=payload)
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", self.auth)
        try:
            urlopen(req, timeout=5)
        except Exception:
            pass


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("network-generator")
loki = LokiHandler()
loki.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
log.addHandler(loki)

# =============================================================================
# Device inventory
# =============================================================================

ROUTERS = [
    {"hostname": "core-rtr-01", "model": "ISR-4451", "vendor": "Cisco", "site": "dc-east", "role": "core"},
    {"hostname": "core-rtr-02", "model": "ISR-4451", "vendor": "Cisco", "site": "dc-west", "role": "core"},
]

SWITCHES = [
    {"hostname": "access-sw-01", "model": "C9300-48P", "vendor": "Cisco", "site": "dc-east", "role": "access"},
    {"hostname": "access-sw-02", "model": "C9300-48P", "vendor": "Cisco", "site": "dc-west", "role": "access"},
    {"hostname": "dist-sw-01", "model": "C9500-24Y4C", "vendor": "Cisco", "site": "dc-east", "role": "distribution"},
]

LOAD_BALANCERS = [
    {"hostname": "lb-01", "model": "BIG-IP-i5800", "vendor": "F5", "site": "dc-east", "role": "load_balancer"},
    {"hostname": "lb-02", "model": "BIG-IP-i5800", "vendor": "F5", "site": "dc-west", "role": "load_balancer"},
]

ALL_DEVICES = ROUTERS + SWITCHES + LOAD_BALANCERS

ROUTER_INTERFACES = [
    "GigabitEthernet0/0", "GigabitEthernet0/1",
    "GigabitEthernet0/2", "GigabitEthernet0/3",
    "Loopback0",
]

SWITCH_INTERFACES = [f"GigabitEthernet1/0/{p}" for p in range(1, 25)] + [
    "TenGigabitEthernet1/1/1", "TenGigabitEthernet1/1/2",
]

LB_INTERFACES = ["mgmt", "external", "internal", "ha"]

BGP_PEERS = {
    "core-rtr-01": [
        {"peer": "10.0.0.2", "asn": "65002", "description": "core-rtr-02"},
        {"peer": "10.0.1.1", "asn": "65100", "description": "isp-upstream-1"},
        {"peer": "10.0.2.1", "asn": "65200", "description": "isp-upstream-2"},
    ],
    "core-rtr-02": [
        {"peer": "10.0.0.1", "asn": "65001", "description": "core-rtr-01"},
        {"peer": "10.0.3.1", "asn": "65100", "description": "isp-upstream-1"},
        {"peer": "10.0.4.1", "asn": "65300", "description": "cdn-peer"},
    ],
}

LB_VIRTUAL_SERVERS = {
    "lb-01": [
        {"name": "vs-web-https", "address": "192.168.1.10", "port": "443", "pool": "pool-web-east"},
        {"name": "vs-api-https", "address": "192.168.1.11", "port": "443", "pool": "pool-api-east"},
        {"name": "vs-app-http", "address": "192.168.1.12", "port": "80", "pool": "pool-app-east"},
    ],
    "lb-02": [
        {"name": "vs-web-https", "address": "192.168.2.10", "port": "443", "pool": "pool-web-west"},
        {"name": "vs-api-https", "address": "192.168.2.11", "port": "443", "pool": "pool-api-west"},
        {"name": "vs-app-http", "address": "192.168.2.12", "port": "80", "pool": "pool-app-west"},
    ],
}

LB_POOL_MEMBERS = {
    "lb-01": {
        "pool-web-east": ["web-east-01:8080", "web-east-02:8080", "web-east-03:8080"],
        "pool-api-east": ["api-east-01:8080", "api-east-02:8080"],
        "pool-app-east": ["app-east-01:3000", "app-east-02:3000", "app-east-03:3000", "app-east-04:3000"],
    },
    "lb-02": {
        "pool-web-west": ["web-west-01:8080", "web-west-02:8080", "web-west-03:8080"],
        "pool-api-west": ["api-west-01:8080", "api-west-02:8080"],
        "pool-app-west": ["app-west-01:3000", "app-west-02:3000", "app-west-03:3000", "app-west-04:3000"],
    },
}

# =============================================================================
# Metric definitions
# =============================================================================

device_info = Info(
    "network_device",
    "Network device information",
    ["hostname", "site", "role"],
)

# --- Device-level gauges ---
device_uptime = Gauge(
    "network_device_uptime_seconds",
    "Device uptime in seconds",
    ["hostname", "site", "role"],
)
device_cpu = Gauge(
    "network_device_cpu_usage_percent",
    "CPU utilization percentage",
    ["hostname", "site", "role"],
)
device_memory = Gauge(
    "network_device_memory_usage_percent",
    "Memory utilization percentage",
    ["hostname", "site", "role"],
)
device_temperature = Gauge(
    "network_device_temperature_celsius",
    "Device temperature in Celsius",
    ["hostname", "site", "role", "sensor"],
)

# --- Interface counters ---
if_bytes_in = Counter(
    "network_interface_received_bytes_total",
    "Total bytes received on interface",
    ["hostname", "interface", "site", "role"],
)
if_bytes_out = Counter(
    "network_interface_transmitted_bytes_total",
    "Total bytes transmitted on interface",
    ["hostname", "interface", "site", "role"],
)
if_packets_in = Counter(
    "network_interface_received_packets_total",
    "Total packets received on interface",
    ["hostname", "interface", "site", "role"],
)
if_packets_out = Counter(
    "network_interface_transmitted_packets_total",
    "Total packets transmitted on interface",
    ["hostname", "interface", "site", "role"],
)
if_errors_in = Counter(
    "network_interface_received_errors_total",
    "Total receive errors on interface",
    ["hostname", "interface", "site", "role"],
)
if_errors_out = Counter(
    "network_interface_transmitted_errors_total",
    "Total transmit errors on interface",
    ["hostname", "interface", "site", "role"],
)
if_drops_in = Counter(
    "network_interface_received_drops_total",
    "Total inbound drops on interface",
    ["hostname", "interface", "site", "role"],
)
if_drops_out = Counter(
    "network_interface_transmitted_drops_total",
    "Total outbound drops on interface",
    ["hostname", "interface", "site", "role"],
)
if_speed = Gauge(
    "network_interface_speed_bits",
    "Interface speed in bits per second",
    ["hostname", "interface", "site", "role"],
)
if_oper_status = Gauge(
    "network_interface_oper_status",
    "Interface operational status (1=up, 0=down)",
    ["hostname", "interface", "site", "role"],
)
if_utilization = Gauge(
    "network_interface_utilization_percent",
    "Interface bandwidth utilization percentage",
    ["hostname", "interface", "site", "role", "direction"],
)

# --- BGP metrics (routers) ---
bgp_state = Gauge(
    "network_bgp_session_state",
    "BGP session state (1=established, 0=down)",
    ["hostname", "peer", "remote_asn", "description", "site"],
)
bgp_prefixes_received = Gauge(
    "network_bgp_prefixes_received",
    "Number of prefixes received from BGP peer",
    ["hostname", "peer", "remote_asn", "description", "site"],
)
bgp_uptime = Gauge(
    "network_bgp_session_uptime_seconds",
    "BGP session uptime in seconds",
    ["hostname", "peer", "remote_asn", "description", "site"],
)
bgp_messages_in = Counter(
    "network_bgp_messages_received_total",
    "Total BGP messages received",
    ["hostname", "peer", "remote_asn", "site"],
)
bgp_messages_out = Counter(
    "network_bgp_messages_sent_total",
    "Total BGP messages sent",
    ["hostname", "peer", "remote_asn", "site"],
)

# --- OSPF metrics (routers) ---
ospf_neighbors = Gauge(
    "network_ospf_neighbor_count",
    "Number of OSPF neighbors",
    ["hostname", "site", "area"],
)
routing_table_size = Gauge(
    "network_routing_table_entries",
    "Number of entries in routing table",
    ["hostname", "site", "protocol"],
)

# --- Switch-specific metrics ---
switch_mac_table = Gauge(
    "network_switch_mac_table_entries",
    "Number of MAC address table entries",
    ["hostname", "site"],
)
switch_mac_table_capacity = Gauge(
    "network_switch_mac_table_capacity",
    "MAC address table capacity",
    ["hostname", "site"],
)
switch_vlan_count = Gauge(
    "network_switch_active_vlans",
    "Number of active VLANs",
    ["hostname", "site"],
)
switch_stp_changes = Counter(
    "network_switch_stp_topology_changes_total",
    "Total STP topology changes",
    ["hostname", "site"],
)
switch_poe_watts = Gauge(
    "network_switch_poe_power_watts",
    "PoE power consumption in watts",
    ["hostname", "site", "slot"],
)
switch_poe_budget = Gauge(
    "network_switch_poe_budget_watts",
    "Total PoE power budget in watts",
    ["hostname", "site", "slot"],
)

# --- Load balancer metrics ---
lb_connections_active = Gauge(
    "network_lb_active_connections",
    "Current active connections",
    ["hostname", "virtual_server", "address", "port", "site"],
)
lb_connections_total = Counter(
    "network_lb_connections_total",
    "Total connections handled",
    ["hostname", "virtual_server", "address", "port", "site"],
)
lb_bytes_in = Counter(
    "network_lb_received_bytes_total",
    "Total bytes received by virtual server",
    ["hostname", "virtual_server", "site"],
)
lb_bytes_out = Counter(
    "network_lb_transmitted_bytes_total",
    "Total bytes transmitted by virtual server",
    ["hostname", "virtual_server", "site"],
)
lb_requests_total = Counter(
    "network_lb_http_requests_total",
    "Total HTTP requests by status code",
    ["hostname", "virtual_server", "status_code", "site"],
)
lb_request_duration = Histogram(
    "network_lb_request_duration_seconds",
    "HTTP request duration in seconds",
    ["hostname", "virtual_server", "site"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)
lb_ssl_handshakes = Counter(
    "network_lb_ssl_handshakes_total",
    "Total SSL/TLS handshakes",
    ["hostname", "site", "tls_version"],
)
lb_pool_member_status = Gauge(
    "network_lb_pool_member_status",
    "Pool member health status (1=up, 0=down)",
    ["hostname", "pool", "member", "site"],
)
lb_pool_member_connections = Gauge(
    "network_lb_pool_member_active_connections",
    "Active connections to pool member",
    ["hostname", "pool", "member", "site"],
)
lb_connection_table_util = Gauge(
    "network_lb_connection_table_utilization_percent",
    "Connection table utilization",
    ["hostname", "site"],
)

# =============================================================================
# State tracking for realistic simulation
# =============================================================================

state = {
    "uptimes": {},
    "bgp_uptimes": {},
    "bgp_states": {},
    "interface_status": {},
    "pool_member_status": {},
    "tick": 0,
}


def init_state():
    for d in ALL_DEVICES:
        h = d["hostname"]
        state["uptimes"][h] = random.randint(86400, 86400 * 90)

    for rtr in ROUTERS:
        h = rtr["hostname"]
        for peer_info in BGP_PEERS.get(h, []):
            key = f"{h}:{peer_info['peer']}"
            state["bgp_states"][key] = 1
            state["bgp_uptimes"][key] = random.randint(3600, 86400 * 30)

    for rtr in ROUTERS:
        for iface in ROUTER_INTERFACES:
            state["interface_status"][f"{rtr['hostname']}:{iface}"] = 1
    for sw in SWITCHES:
        for iface in SWITCH_INTERFACES:
            state["interface_status"][f"{sw['hostname']}:{iface}"] = 1
    for lb in LOAD_BALANCERS:
        for iface in LB_INTERFACES:
            state["interface_status"][f"{lb['hostname']}:{iface}"] = 1

    for lb in LOAD_BALANCERS:
        for pool_name, members in LB_POOL_MEMBERS.get(lb["hostname"], {}).items():
            for member in members:
                state["pool_member_status"][f"{lb['hostname']}:{pool_name}:{member}"] = 1


def simulate_interface_traffic(hostname, interfaces, device, base_rate_mbps):
    """Increment interface counters with realistic traffic patterns."""
    site = device["site"]
    role = device["role"]
    for iface in interfaces:
        key = f"{hostname}:{iface}"
        status = state["interface_status"].get(key, 1)

        if "Loopback" in iface:
            speed = 0
            if_speed.labels(hostname, iface, site, role).set(0)
            if_oper_status.labels(hostname, iface, site, role).set(1)
            continue

        if "TenGig" in iface:
            speed = 10_000_000_000
            rate = base_rate_mbps * random.uniform(3.0, 8.0)
        elif "Gig" in iface:
            speed = 1_000_000_000
            rate = base_rate_mbps * random.uniform(0.3, 1.5)
        else:
            speed = 1_000_000_000
            rate = base_rate_mbps * random.uniform(0.1, 0.5)

        if_speed.labels(hostname, iface, site, role).set(speed)
        if_oper_status.labels(hostname, iface, site, role).set(status)

        if status == 0:
            continue

        # Add time-of-day variation (simulate business hours pattern)
        hour_factor = 0.6 + 0.4 * abs(((state["tick"] % 288) - 144) / 144.0)
        rate *= hour_factor

        bytes_per_sec_in = rate * 1_000_000 / 8 * random.uniform(0.8, 1.2)
        bytes_per_sec_out = rate * 1_000_000 / 8 * random.uniform(0.6, 1.0)

        if_bytes_in.labels(hostname, iface, site, role).inc(bytes_per_sec_in * 10)
        if_bytes_out.labels(hostname, iface, site, role).inc(bytes_per_sec_out * 10)

        avg_pkt_size = random.uniform(400, 1200)
        if_packets_in.labels(hostname, iface, site, role).inc(bytes_per_sec_in * 10 / avg_pkt_size)
        if_packets_out.labels(hostname, iface, site, role).inc(bytes_per_sec_out * 10 / avg_pkt_size)

        if random.random() < 0.02:
            if_errors_in.labels(hostname, iface, site, role).inc(random.randint(1, 5))
        if random.random() < 0.01:
            if_errors_out.labels(hostname, iface, site, role).inc(random.randint(1, 3))
        if random.random() < 0.03:
            if_drops_in.labels(hostname, iface, site, role).inc(random.randint(1, 10))
        if random.random() < 0.02:
            if_drops_out.labels(hostname, iface, site, role).inc(random.randint(1, 5))

        util_in = min(100, (bytes_per_sec_in * 8 / speed) * 100) if speed > 0 else 0
        util_out = min(100, (bytes_per_sec_out * 8 / speed) * 100) if speed > 0 else 0
        if_utilization.labels(hostname, iface, site, role, "in").set(round(util_in, 2))
        if_utilization.labels(hostname, iface, site, role, "out").set(round(util_out, 2))


def simulate_routers():
    for rtr in ROUTERS:
        h = rtr["hostname"]
        site = rtr["site"]
        role = rtr["role"]

        state["uptimes"][h] += 10
        device_uptime.labels(h, site, role).set(state["uptimes"][h])

        cpu_base = 25 + random.gauss(0, 5)
        if state["tick"] % 60 < 5:
            cpu_base += random.uniform(10, 25)
        device_cpu.labels(h, site, role).set(max(1, min(100, cpu_base)))
        device_memory.labels(h, site, role).set(max(20, min(90, 55 + random.gauss(0, 5))))
        device_temperature.labels(h, site, role, "cpu").set(round(32 + random.gauss(0, 1.5), 1))
        device_temperature.labels(h, site, role, "intake").set(round(24 + random.gauss(0, 1), 1))

        simulate_interface_traffic(h, ROUTER_INTERFACES, rtr, base_rate_mbps=200)

        for peer_info in BGP_PEERS.get(h, []):
            peer = peer_info["peer"]
            asn = peer_info["asn"]
            desc = peer_info["description"]
            key = f"{h}:{peer}"

            # BGP flaps — core-rtr-01 to AS65200 is unstable (flaky upstream)
            flap_rate = 0.008 if (h == "core-rtr-01" and asn == "65200") else 0.001
            if random.random() < flap_rate:
                state["bgp_states"][key] = 0
                state["bgp_uptimes"][key] = 0
                log.warning("BGP session DOWN: %s -> %s (AS%s)", h, peer, asn)
            elif state["bgp_states"][key] == 0 and random.random() < 0.1:
                state["bgp_states"][key] = 1
                log.info("BGP session RESTORED: %s -> %s (AS%s)", h, peer, asn)

            if state["bgp_states"][key] == 1:
                state["bgp_uptimes"][key] += 10

            bgp_state.labels(h, peer, asn, desc, site).set(state["bgp_states"][key])
            bgp_uptime.labels(h, peer, asn, desc, site).set(state["bgp_uptimes"][key])

            if state["bgp_states"][key] == 1:
                base_prefixes = {"65100": 120000, "65200": 85000, "65300": 45000}
                pfx = base_prefixes.get(asn, 500) + random.randint(-100, 100)
                bgp_prefixes_received.labels(h, peer, asn, desc, site).set(pfx)
                bgp_messages_in.labels(h, peer, asn, site).inc(random.randint(2, 10))
                bgp_messages_out.labels(h, peer, asn, site).inc(random.randint(2, 8))
            else:
                bgp_prefixes_received.labels(h, peer, asn, desc, site).set(0)

        ospf_neighbors.labels(h, site, "0.0.0.0").set(random.choice([3, 3, 3, 4, 4, 2]))
        routing_table_size.labels(h, site, "connected").set(random.randint(8, 12))
        routing_table_size.labels(h, site, "ospf").set(random.randint(40, 60))
        routing_table_size.labels(h, site, "bgp").set(random.randint(180000, 220000))
        routing_table_size.labels(h, site, "static").set(random.randint(3, 8))


def simulate_switches():
    for sw in SWITCHES:
        h = sw["hostname"]
        site = sw["site"]
        role = sw["role"]

        state["uptimes"][h] += 10
        device_uptime.labels(h, site, role).set(state["uptimes"][h])
        device_cpu.labels(h, site, role).set(max(1, min(100, 15 + random.gauss(0, 3))))
        device_memory.labels(h, site, role).set(max(15, min(80, 40 + random.gauss(0, 4))))
        device_temperature.labels(h, site, role, "cpu").set(round(30 + random.gauss(0, 1.5), 1))
        device_temperature.labels(h, site, role, "intake").set(round(22 + random.gauss(0, 1), 1))

        simulate_interface_traffic(h, SWITCH_INTERFACES, sw, base_rate_mbps=50)

        switch_mac_table.labels(h, site).set(random.randint(800, 2500))
        switch_mac_table_capacity.labels(h, site).set(16384)
        switch_vlan_count.labels(h, site).set(random.choice([12, 14, 15, 16]))

        if random.random() < 0.005:
            switch_stp_changes.labels(h, site).inc(1)
            log.warning("STP topology change detected on %s", h)

        switch_poe_watts.labels(h, site, "1").set(round(random.uniform(180, 350), 1))
        switch_poe_budget.labels(h, site, "1").set(740.0)


def simulate_load_balancers():
    for lb in LOAD_BALANCERS:
        h = lb["hostname"]
        site = lb["site"]
        role = lb["role"]

        state["uptimes"][h] += 10
        device_uptime.labels(h, site, role).set(state["uptimes"][h])

        # lb-01 is the problem device: thermal issues → CPU spikes → cascading failures
        if h == "lb-01":
            temp = round(44 + random.gauss(0, 2), 1)
            if state["tick"] % 30 < 6:
                temp += random.uniform(2, 5)
            device_temperature.labels(h, site, role, "cpu").set(temp)

            cpu = 48 + random.gauss(0, 8)
            if temp > 48:
                cpu += random.uniform(8, 18)
            device_cpu.labels(h, site, role).set(max(1, min(100, cpu)))
            device_memory.labels(h, site, role).set(max(30, min(95, 72 + random.gauss(0, 5))))
        else:
            device_cpu.labels(h, site, role).set(max(1, min(100, 35 + random.gauss(0, 8))))
            device_memory.labels(h, site, role).set(max(30, min(90, 60 + random.gauss(0, 5))))
            device_temperature.labels(h, site, role, "cpu").set(round(34 + random.gauss(0, 1.5), 1))

        simulate_interface_traffic(h, LB_INTERFACES, lb, base_rate_mbps=300)

        for vs in LB_VIRTUAL_SERVERS.get(h, []):
            name = vs["name"]
            addr = vs["address"]
            port = vs["port"]

            active = int(random.gauss(1500, 300))
            active = max(100, min(5000, active))
            lb_connections_active.labels(h, name, addr, port, site).set(active)
            lb_connections_total.labels(h, name, addr, port, site).inc(random.randint(50, 200))

            lb_bytes_in.labels(h, name, site).inc(random.randint(5_000_000, 50_000_000))
            lb_bytes_out.labels(h, name, site).inc(random.randint(20_000_000, 200_000_000))

            rps = random.randint(200, 800)
            if h == "lb-01":
                lb_requests_total.labels(h, name, "200", site).inc(int(rps * 0.85))
                lb_requests_total.labels(h, name, "301", site).inc(int(rps * 0.03))
                lb_requests_total.labels(h, name, "304", site).inc(int(rps * 0.02))
                lb_requests_total.labels(h, name, "404", site).inc(int(rps * 0.02))
                lb_requests_total.labels(h, name, "500", site).inc(int(rps * 0.02))
                lb_requests_total.labels(h, name, "502", site).inc(int(rps * 0.035))
                lb_requests_total.labels(h, name, "503", site).inc(int(rps * 0.025))
            else:
                lb_requests_total.labels(h, name, "200", site).inc(int(rps * 0.92))
                lb_requests_total.labels(h, name, "301", site).inc(int(rps * 0.03))
                lb_requests_total.labels(h, name, "304", site).inc(int(rps * 0.02))
                lb_requests_total.labels(h, name, "404", site).inc(int(rps * 0.015))
                lb_requests_total.labels(h, name, "500", site).inc(int(rps * 0.005))
                lb_requests_total.labels(h, name, "502", site).inc(int(rps * 0.005))
                lb_requests_total.labels(h, name, "503", site).inc(int(rps * 0.005))

            for _ in range(random.randint(20, 50)):
                if h == "lb-01":
                    latency = random.lognormvariate(-1.8, 1.0)
                else:
                    latency = random.lognormvariate(-2.5, 0.8)
                lb_request_duration.labels(h, name, site).observe(min(latency, 10.0))

        lb_ssl_handshakes.labels(h, site, "TLSv1.3").inc(random.randint(100, 500))
        lb_ssl_handshakes.labels(h, site, "TLSv1.2").inc(random.randint(10, 50))

        # lb-01 pool members flap much more often
        pool_fail_rate = 0.015 if h == "lb-01" else 0.003
        pool_recover_rate = 0.10 if h == "lb-01" else 0.15

        for pool_name, members in LB_POOL_MEMBERS.get(h, {}).items():
            for member in members:
                pkey = f"{h}:{pool_name}:{member}"
                if random.random() < pool_fail_rate:
                    state["pool_member_status"][pkey] = 0
                    log.warning("Pool member DOWN: %s/%s on %s", pool_name, member, h)
                elif state["pool_member_status"].get(pkey, 1) == 0 and random.random() < pool_recover_rate:
                    state["pool_member_status"][pkey] = 1
                    log.info("Pool member RESTORED: %s/%s on %s", pool_name, member, h)

                lb_pool_member_status.labels(h, pool_name, member, site).set(
                    state["pool_member_status"].get(pkey, 1)
                )
                if state["pool_member_status"].get(pkey, 1) == 1:
                    lb_pool_member_connections.labels(h, pool_name, member, site).set(
                        random.randint(50, 400)
                    )
                else:
                    lb_pool_member_connections.labels(h, pool_name, member, site).set(0)

        total_conns = sum(
            lb_connections_active.labels(h, vs["name"], vs["address"], vs["port"], site)._value.get()
            for vs in LB_VIRTUAL_SERVERS.get(h, [])
        )
        max_conns = 100_000
        lb_connection_table_util.labels(h, site).set(round(total_conns / max_conns * 100, 2))


def generate_network_events():
    """Emit realistic network log events at varying rates."""
    tick = state["tick"]

    for d in ALL_DEVICES:
        h, site, role = d["hostname"], d["site"], d["role"]

        # Routine: SNMP poll success (every ~30s per device)
        if tick % 3 == 0:
            log.info("SNMP poll OK: %s (%s) response_time=%.0fms", h, site, random.uniform(2, 15))

        # Interface flap (rare)
        if random.random() < 0.004:
            iface = random.choice(["GigabitEthernet0/0/1", "TenGigE0/1", "Ethernet1/48", "Port-channel1"])
            log.warning("Interface %s on %s changed state to DOWN", iface, h)
            if random.random() < 0.8:
                log.info("Interface %s on %s changed state to UP", iface, h)

    # Auth events
    if random.random() < 0.03:
        user = random.choice(["admin", "netops", "monitoring", "backup-svc"])
        host = random.choice([d["hostname"] for d in ALL_DEVICES])
        src = f"10.{random.randint(1,10)}.{random.randint(1,254)}.{random.randint(1,254)}"
        log.info("SSH login accepted for user '%s' on %s from %s", user, host, src)

    if random.random() < 0.008:
        user = random.choice(["root", "admin", "test"])
        host = random.choice([d["hostname"] for d in ALL_DEVICES])
        src = f"10.{random.randint(1,10)}.{random.randint(1,254)}.{random.randint(1,254)}"
        log.warning("SSH login FAILED for user '%s' on %s from %s (bad password)", user, host, src)

    # Config changes (infrequent)
    if random.random() < 0.005:
        host = random.choice([d["hostname"] for d in ALL_DEVICES])
        user = random.choice(["netops", "admin"])
        log.info("Configuration changed on %s by user '%s' via SSH", host, user)

    # NTP sync
    if tick % 30 == 0:
        for d in ALL_DEVICES:
            offset = random.gauss(0, 0.5)
            log.info("NTP sync %s: stratum=2 offset=%.3fms", d["hostname"], offset)

    # OSPF neighbor events
    if random.random() < 0.006:
        rtr = random.choice(ROUTERS)
        neighbor_id = f"10.0.{random.randint(0,3)}.{random.randint(1,4)}"
        log.warning("OSPF neighbor %s on %s changed state to DOWN", neighbor_id, rtr["hostname"])
        if random.random() < 0.9:
            log.info("OSPF neighbor %s on %s changed state to FULL", neighbor_id, rtr["hostname"])

    # LB health monitor
    if random.random() < 0.01:
        lb = random.choice(LOAD_BALANCERS)
        pool = random.choice(list(LB_POOL_MEMBERS.get(lb["hostname"], {}).keys()))
        log.info("Health monitor check passed for pool %s on %s", pool, lb["hostname"])

    # lb-01 thermal cascade events
    if random.random() < 0.04:
        log.warning("Fan speed increased to %d RPM on lb-01 (temperature threshold)", random.randint(4500, 6000))
    if random.random() < 0.02:
        log.warning("THERMAL WARNING: CPU temperature on lb-01 exceeded 50C (current: %.1fC)", 50 + random.uniform(0, 4))
    if random.random() < 0.015:
        log.error("SSL handshake timeout on lb-01 vip-web-east:443 (client %s)", f"10.{random.randint(1,20)}.{random.randint(1,254)}.{random.randint(1,254)}")
    if random.random() < 0.01:
        log.error("Connection table pressure on lb-01: %d%% utilized, new connections delayed", random.randint(78, 92))

    # ACL/firewall hits
    if random.random() < 0.02:
        host = random.choice([d["hostname"] for d in ALL_DEVICES])
        src_ip = f"10.{random.randint(1,20)}.{random.randint(1,254)}.{random.randint(1,254)}"
        dst_ip = f"10.{random.randint(1,20)}.{random.randint(1,254)}.{random.randint(1,254)}"
        port = random.choice([22, 443, 80, 8080, 3306, 5432])
        action = random.choices(["permit", "deny"], weights=[85, 15])[0]
        log.info("ACL hit on %s: %s %s -> %s:%d", host, action, src_ip, dst_ip, port)


def set_device_info():
    for d in ALL_DEVICES:
        device_info.labels(d["hostname"], d["site"], d["role"]).info(
            {"model": d["model"], "vendor": d["vendor"]}
        )


def update_loop():
    while True:
        state["tick"] += 1
        simulate_routers()
        simulate_switches()
        simulate_load_balancers()
        generate_network_events()
        time.sleep(10)


class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/metrics" or self.path == "/":
            output = generate_latest()
            self.send_response(200)
            self.send_header("Content-Type", CONTENT_TYPE_LATEST)
            self.end_headers()
            self.wfile.write(output)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    init_state()
    set_device_info()

    port = int(os.environ.get("PORT", "9090"))
    log.info("Starting network metrics generator on :%d", port)
    log.info(
        "Simulating %d routers, %d switches, %d load balancers",
        len(ROUTERS), len(SWITCHES), len(LOAD_BALANCERS),
    )

    update_thread = threading.Thread(target=update_loop, daemon=True)
    update_thread.start()

    server = HTTPServer(("0.0.0.0", port), MetricsHandler)
    log.info("Metrics server ready on :%d", port)
    server.serve_forever()
