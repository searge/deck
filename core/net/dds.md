---
tags:
  - networking
  - protocols
  - robotics
aliases:
  - DDS
  - Data Distribution Service
title: DDS
description: DDS middleware — real-time pub/sub for robotics and distributed systems with QoS policies and ROS2 integration.
---

# dds

DDS (Data Distribution Service) is a middleware standard for real-time, data-centric publish-subscribe communication. Published by OMG (Object Management Group) in 2004, it targets systems where data must flow reliably between many participants with strict timing requirements.

Unlike message-oriented middleware (MQTT, AMQP), DDS is data-centric. You don't just send messages — you publish data samples with types, keys, and QoS policies. The middleware understands your data model and can filter, persist, and deliver based on content, not just topics.

DDS excels in distributed systems: autonomous vehicles, industrial automation, aerospace, defense, and robotics. ROS2 chose DDS as its communication backbone specifically for these properties.

## DDS vs MQTT

| Aspect | DDS | MQTT |
|--------|-----|------|
| Architecture | Peer-to-peer (brokerless) | Client-broker |
| Discovery | Automatic | Manual (broker address) |
| Data model | Typed, keyed data | Opaque byte payloads |
| QoS policies | 22+ configurable policies | 3 levels (0, 1, 2) |
| Filtering | Content-based | Topic-based only |
| Scalability | Designed for 1000s of nodes | Broker bottleneck |
| Latency | Microseconds | Milliseconds |
| Complexity | High | Low |

MQTT is simpler and fits IoT sensors well. DDS handles complex distributed systems where you need fine-grained control over data flow.

## Core concepts

**Domain** isolates communication. Participants in Domain 0 can't see Domain 1. Think of it as a namespace or network partition. ROS2 uses `ROS_DOMAIN_ID` environment variable.

**Participant** represents an application in a domain. Each participant discovers others automatically through the RTPS protocol. No central registry needed.

**Topic** names a data stream with an associated type. Unlike MQTT's arbitrary strings, DDS topics have schema: `sensor_msgs/msg/Image`, `geometry_msgs/msg/Twist`. Publisher and subscriber must agree on the type.

**DataWriter** publishes data samples to a topic. It's the "publisher" in pub-sub terminology but with richer semantics — history depth, lifespan, ownership.

**DataReader** subscribes to a topic and receives samples. It can filter by content, request specific history, and get notified of lifecycle events.

**QoS (Quality of Service)** policies control every aspect of data flow. This is where DDS differs fundamentally from simpler protocols.

## QoS policies

DDS defines 22+ QoS policies. Key ones:

**Reliability:**

- `RELIABLE` — guarantees delivery, retransmits lost samples
- `BEST_EFFORT` — fire and forget, lowest latency

**Durability:**

- `VOLATILE` — only delivers to currently connected readers
- `TRANSIENT_LOCAL` — late joiners get historical data from writer
- `TRANSIENT` — data persists beyond writer lifetime (needs service)
- `PERSISTENT` — survives system restart (needs service)

**History:**

- `KEEP_LAST(n)` — buffer last n samples
- `KEEP_ALL` — buffer everything (memory risk)

**Deadline:** Maximum time between samples. Missed deadlines trigger callbacks.

**Lifespan:** Sample expiration. Old data auto-discards.

**Ownership:**

- `SHARED` — multiple writers, readers get all
- `EXCLUSIVE` — highest-strength writer wins

**Liveliness:** Detect dead writers. Manual or automatic heartbeat.

QoS must be compatible between writer and reader. Mismatched QoS (e.g., reliable writer, best-effort reader) prevents communication — the middleware refuses the connection.

## RTPS wire protocol

DDS implementations communicate via RTPS (Real-Time Publish-Subscribe), the interoperability protocol. It defines:

- **Discovery:** SPDP (Simple Participant Discovery Protocol) finds participants. SEDP (Simple Endpoint Discovery Protocol) matches writers/readers.
- **Data exchange:** Submessages carry data, heartbeats, acknowledgments.
- **Ports:** Default ports based on domain ID and participant ID.

```text
Discovery multicast:  239.255.0.1:7400 + domainId * 250
User multicast:       239.255.0.1:7401 + domainId * 250
Unicast:              Calculated per participant
```

Wireshark decodes RTPS natively — useful for debugging.

## ROS2 and DDS

### Architecture

ROS2 abstracts DDS through the rmw (ROS middleware) layer:

```text
┌─────────────────────────────────────────┐
│           ROS 2 Application             │
├─────────────────────────────────────────┤
│              rclcpp / rclpy             │
├─────────────────────────────────────────┤
│                  rcl                    │
├─────────────────────────────────────────┤
│                  rmw                    │
├─────────────┬─────────────┬─────────────┤
│ rmw_fastrtps│rmw_cyclonedds│ rmw_connext│
├─────────────┼─────────────┼─────────────┤
│  Fast DDS   │ Cyclone DDS │RTI Connext  │
└─────────────┴─────────────┴─────────────┘
```

You write ROS2 code once; swap DDS implementations via environment variable:

```bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
```

### ROS2 concepts mapped to DDS

| ROS2 | DDS |
|------|-----|
| Node | Participant (often) |
| Publisher | DataWriter |
| Subscriber | DataReader |
| Topic | Topic |
| Service | Request/Reply pattern |
| Action | Complex state machine over topics |
| Parameter | Separate topic + service |

### QoS in ROS2

ROS2 exposes simplified QoS profiles:

```python
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy

qos = QoSProfile(
    reliability=ReliabilityPolicy.RELIABLE,
    durability=DurabilityPolicy.TRANSIENT_LOCAL,
    depth=10
)

publisher = node.create_publisher(String, 'topic', qos)
```

Predefined profiles:

- `qos_profile_sensor_data` — best effort, volatile (high frequency sensors)
- `qos_profile_parameters` — reliable, volatile
- `qos_profile_services_default` — reliable, volatile
- `qos_profile_system_default` — reliable, volatile, depth 10

### Discovery and domain ID

ROS2 nodes discover each other automatically within the same domain:

```bash
# Terminal 1
export ROS_DOMAIN_ID=42
ros2 run demo_nodes_cpp talker

# Terminal 2
export ROS_DOMAIN_ID=42
ros2 run demo_nodes_cpp listener
```

Different domain IDs isolate communication completely. Default is 0. Valid range: 0-232.

## DDS configuration

Fine-tune DDS via XML profiles. For Fast DDS, create `fastdds.xml`:

```xml
<?xml version="1.0" encoding="UTF-8" ?>
<profiles xmlns="http://www.eprosima.com/XMLSchemas/fastRTPS_Profiles">
    <participant profile_name="participant_profile" is_default_profile="true">
        <rtps>
            <builtin>
                <discovery_config>
                    <discoveryProtocol>SIMPLE</discoveryProtocol>
                    <leaseDuration>
                        <sec>10</sec>
                    </leaseDuration>
                </discovery_config>
            </builtin>
        </rtps>
    </participant>

    <data_writer profile_name="default_writer" is_default_profile="true">
        <qos>
            <reliability>
                <kind>RELIABLE</kind>
            </reliability>
            <durability>
                <kind>TRANSIENT_LOCAL</kind>
            </durability>
        </qos>
    </data_writer>
</profiles>
```

Load with:

```bash
export FASTRTPS_DEFAULT_PROFILES_FILE=/path/to/fastdds.xml
```

### Network configuration

DDS uses multicast by default. In environments where multicast is blocked (cloud, some containers):

```xml
<!-- Disable multicast, use unicast peer list -->
<participant profile_name="no_multicast">
    <rtps>
        <builtin>
            <metatrafficUnicastLocatorList>
                <locator>
                    <udpv4>
                        <address>192.168.1.10</address>
                    </udpv4>
                </locator>
            </metatrafficUnicastLocatorList>
            <initialPeersList>
                <locator>
                    <udpv4>
                        <address>192.168.1.20</address>
                    </udpv4>
                </locator>
            </initialPeersList>
        </builtin>
    </rtps>
</participant>
```

For Kubernetes, use Cyclone DDS with shared memory disabled and explicit peer discovery.

## DDS in Kubernetes

### Challenges

DDS assumes:

- Multicast works (often blocked in K8s)
- Participants discover each other (pods have dynamic IPs)
- Low latency (network hops add delay)

Solutions:

1. **Host networking** — pods share host network, multicast works
2. **DDS Discovery Server** — central discovery point
3. **ROS 2 Discovery Server** — lightweight alternative
4. **Zenoh** — protocol bridge designed for cloud

### Fast DDS discovery server

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fastdds-discovery
spec:
  replicas: 1
  selector:
    matchLabels:
      app: fastdds-discovery
  template:
    metadata:
      labels:
        app: fastdds-discovery
    spec:
      containers:
        - name: discovery
          image: eprosima/fastdds:latest
          command: ["fast-discovery-server", "-i", "0"]
          ports:
            - containerPort: 11811
---
apiVersion: v1
kind: Service
metadata:
  name: fastdds-discovery
spec:
  selector:
    app: fastdds-discovery
  ports:
    - port: 11811
```

Configure clients:

```bash
export ROS_DISCOVERY_SERVER=fastdds-discovery:11811
```

## Performance

### Latency

DDS achieves microsecond latency with:

- Shared memory transport (same host)
- Zero-copy data paths
- Preallocated buffers

### Throughput

For high-bandwidth data (images, point clouds):

- Use `BEST_EFFORT` reliability
- Tune history depth carefully
- Consider `KEEP_LAST(1)` for latest-only semantics
- Enable shared memory when possible

## See also

- [[mqtt]]
- [[tcp_ip_model]]

## References

- [OMG DDS Specification](https://www.omg.org/spec/DDS/)
- [DDS-RTPS Wire Protocol](https://www.omg.org/spec/DDSI-RTPS/)
- [ROS 2 Documentation](https://docs.ros.org/en/rolling/)
- [Fast DDS](https://www.eprosima.com/index.php/products-all/eprosima-fast-dds)
- [Cyclone DDS](https://cyclonedds.io/)
