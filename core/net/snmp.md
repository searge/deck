---
tags:
  - networking
  - protocols
  - monitoring
aliases:
  - SNMP
title: SNMP
description: SNMP protocol — network device monitoring with OIDs, MIBs, versions, and Prometheus integration.
---

# snmp

SNMP (Simple Network Management Protocol) is a protocol for collecting and organizing information about managed devices on IP networks. Created in 1988, it remains the standard way to monitor network infrastructure — routers, switches, firewalls, servers, printers, UPS systems.

Despite its name, SNMP isn't simple. The protocol itself is straightforward, but the ecosystem of MIBs, OIDs, and versioning adds complexity. Understanding SNMP requires grasping three components: the protocol operations, the data model (SMI/MIB), and the security model (especially in v3).

SNMP operates over UDP ports 161 (agent) and 162 (traps). The choice of UDP reflects its design goals: lightweight polling of many devices where occasional packet loss is acceptable.

## Architecture

SNMP uses a manager-agent model:

```text
┌─────────────┐         ┌─────────────┐
│   Manager   │ ──────> │    Agent    │
│  (NMS/etc)  │ <────── │  (device)   │
└─────────────┘         └─────────────┘
     │                        │
     │ GET/SET requests       │ Responses
     │ <──────────────────────│
     │                        │
     │ TRAP notifications     │
     │ <──────────────────────│
```

**Manager** (or NMS — Network Management System) initiates requests. It queries devices, processes responses, and receives traps. Examples: Prometheus with SNMP exporter, LibreNMS, Zabbix, Nagios.

**Agent** runs on managed devices. It responds to queries, provides access to device data, and sends traps when events occur. Most network equipment ships with an SNMP agent. Linux runs `snmpd`.

**MIB** (Management Information Base) defines what data is available. It's a hierarchical database schema describing variables the agent exposes. Without the MIB, you see raw OIDs; with it, you see meaningful names.

## OIDs and the MIB tree

Every piece of SNMP data has an Object Identifier (OID) — a sequence of numbers forming a path through a global tree:

```text
iso(1)
└── org(3)
    └── dod(6)
        └── internet(1)
            ├── mgmt(2)
            │   └── mib-2(1)
            │       ├── system(1)
            │       │   ├── sysDescr(1)      -> .1.3.6.1.2.1.1.1
            │       │   ├── sysObjectID(2)   -> .1.3.6.1.2.1.1.2
            │       │   ├── sysUpTime(3)     -> .1.3.6.1.2.1.1.3
            │       │   └── sysName(5)       -> .1.3.6.1.2.1.1.5
            │       ├── interfaces(2)
            │       └── ...
            └── private(4)
                └── enterprises(1)
                    ├── cisco(9)
                    ├── hp(11)
                    └── ...
```

Standard MIBs (under mib-2) work across vendors. Enterprise MIBs (under private.enterprises) contain vendor-specific extensions.

## Protocol operations

| Operation | Direction | Purpose |
|-----------|-----------|---------|
| GET | Manager -> Agent | Retrieve specific OID value |
| GETNEXT | Manager -> Agent | Get next OID in tree (for walking) |
| GETBULK | Manager -> Agent | Efficient retrieval of multiple OIDs (v2c+) |
| SET | Manager -> Agent | Modify a value |
| TRAP | Agent -> Manager | Unsolicited event notification |
| INFORM | Agent -> Manager | Acknowledged trap (v2c+) |

Most monitoring uses GET and GETNEXT/GETBULK for polling. SET is used for configuration (when supported). TRAP provides real-time alerts.

## SNMP versions

Three versions exist with different security models:

**SNMPv1** (1988): Original version. Authentication via community string (plaintext password). No encryption. Still widely deployed despite security issues.

**SNMPv2c** (1996): Added GETBULK for efficiency and improved error handling. Kept community string authentication ("c" = community-based). Most common version today.

**SNMPv3** (2002): Proper security model with:

- Authentication (MD5, SHA)
- Encryption (DES, AES)
- Access control (views, groups)

Use v3 for anything security-sensitive. Use v2c only on isolated management networks.

## Data types

SNMP uses ASN.1 data types:

| Type | Description | Example |
|------|-------------|---------|
| INTEGER | Signed 32-bit | Interface status (1=up, 2=down) |
| Counter32 | Monotonic counter, wraps at 2^32 | Bytes transmitted |
| Counter64 | 64-bit counter (v2c+) | High-speed interface counters |
| Gauge32 | Value that can increase/decrease | CPU utilization |
| TimeTicks | Hundredths of seconds | Uptime |
| OCTET STRING | Byte sequence | System description |
| IpAddress | IPv4 address | Interface address |

Counter types require rate calculation: `(current - previous) / interval`. Counters wrap, so handle negative deltas.

## Installing Net-SNMP

On Debian/Ubuntu:

```bash
apt install snmp snmpd snmp-mibs-downloader
```

On Fedora:

```bash
dnf install net-snmp net-snmp-utils
```

Download standard MIBs:

```bash
download-mibs
```

Edit `/etc/snmp/snmp.conf` to load MIBs automatically:

```text
mibs +ALL
```

## Basic queries

Query system description:

```bash
# Using OID
snmpget -v2c -c public localhost .1.3.6.1.2.1.1.1.0

# Using MIB name
snmpget -v2c -c public localhost sysDescr.0
```

Walk the system subtree:

```bash
snmpwalk -v2c -c public localhost system
```

Get interface table:

```bash
snmpwalk -v2c -c public localhost ifTable
```

Bulk retrieval (more efficient):

```bash
snmpbulkwalk -v2c -c public localhost interfaces
```

## SNMPv3 queries

SNMPv3 requires user credentials:

```bash
# Authentication only (authNoPriv)
snmpget -v3 -u myuser -l authNoPriv -a SHA -A "authpassword" \
  localhost sysUpTime.0

# Authentication + encryption (authPriv)
snmpget -v3 -u myuser -l authPriv -a SHA -A "authpassword" \
  -x AES -X "privpassword" localhost sysUpTime.0
```

Security levels:

- `noAuthNoPriv` — username only (not recommended)
- `authNoPriv` — authentication, no encryption
- `authPriv` — authentication + encryption

## Configuring snmpd

Basic `/etc/snmp/snmpd.conf` for monitoring:

```text
# SNMPv2c read-only access
rocommunity public 127.0.0.1
rocommunity monitoring 10.0.0.0/8

# SNMPv3 user
createUser myuser SHA "authpassword" AES "privpassword"
rouser myuser authPriv

# System information
sysLocation "Data Center Rack 5"
sysContact "ops@example.com"
sysName "server01.example.com"

# Extend with custom scripts
extend uptime /usr/bin/uptime
```

Restart after changes:

```bash
systemctl restart snmpd
```

## Prometheus SNMP exporter

For Kubernetes/Prometheus environments:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: snmp-exporter
spec:
  replicas: 1
  selector:
    matchLabels:
      app: snmp-exporter
  template:
    metadata:
      labels:
        app: snmp-exporter
    spec:
      containers:
        - name: snmp-exporter
          image: prom/snmp-exporter:latest
          ports:
            - containerPort: 9116
          volumeMounts:
            - name: config
              mountPath: /etc/snmp_exporter
      volumes:
        - name: config
          configMap:
            name: snmp-exporter-config
```

Configure Prometheus to scrape via the exporter:

```yaml
scrape_configs:
  - job_name: 'snmp'
    static_configs:
      - targets:
          - 192.168.1.1  # Router
          - 192.168.1.2  # Switch
    metrics_path: /snmp
    params:
      module: [if_mib]
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
      - target_label: __address__
        replacement: snmp-exporter:9116
```

## Common OIDs

System information:

```text
sysDescr.0        .1.3.6.1.2.1.1.1.0    System description
sysUpTime.0       .1.3.6.1.2.1.1.3.0    Uptime in ticks
sysName.0         .1.3.6.1.2.1.1.5.0    Hostname
```

Interface statistics:

```text
ifDescr           .1.3.6.1.2.1.2.2.1.2    Interface name
ifOperStatus      .1.3.6.1.2.1.2.2.1.8    Up(1)/Down(2)
ifInOctets        .1.3.6.1.2.1.2.2.1.10   Bytes received
ifOutOctets       .1.3.6.1.2.1.2.2.1.16   Bytes sent
ifInErrors        .1.3.6.1.2.1.2.2.1.14   Input errors
```

Host resources (servers):

```text
hrSystemUptime    .1.3.6.1.2.1.25.1.1     Host uptime
hrMemorySize      .1.3.6.1.2.1.25.2.2     Total memory
hrProcessorLoad   .1.3.6.1.2.1.25.3.3.1.2 CPU load per core
hrStorageUsed     .1.3.6.1.2.1.25.2.3.1.6 Disk usage
```

## Security considerations

### Community string risks

SNMPv1/v2c community strings are sent in plaintext. Treat community strings as passwords:

- Never use "public" or "private" in production
- Use different strings for read-only and read-write
- Restrict access by IP in snmpd.conf
- Isolate SNMP traffic to management VLANs

### SNMPv3 best practices

- Use `authPriv` security level
- Prefer SHA over MD5 for authentication
- Prefer AES over DES for encryption
- Use different users for different access levels
- Rotate credentials periodically

### Firewall rules

Block SNMP from untrusted networks:

```bash
# Allow only from monitoring server
iptables -A INPUT -p udp --dport 161 -s 10.0.0.100 -j ACCEPT
iptables -A INPUT -p udp --dport 161 -j DROP
```

## See also

- [dns](dns.md)
- [tcp_ip_model](tcp_ip_model.md)

## References

- [RFC 3411-3418](https://datatracker.ietf.org/doc/html/rfc3411) — SNMPv3 Architecture
- [RFC 1157](https://datatracker.ietf.org/doc/html/rfc1157) — SNMPv1 Specification
- [Net-SNMP](http://www.net-snmp.org/)
- [Prometheus SNMP Exporter](https://github.com/prometheus/snmp_exporter)
- [OID Repository](http://oid-info.com/)
