---
tags:
  - network
  - linux
  - diagnostics

---

# net_info

Network diagnostics and information gathering.

## Open ports

### lsof

```bash
lsof -i -P -n | grep LISTEN
```

Specific port:

```bash
lsof -i:22
```

### netstat

```bash
netstat -tulpn | grep LISTEN
```

### ss

```bash
ss -tulpn | grep LISTEN
```

## IP geolocation

Specific IP:

```bash
curl 'https://ipapi.co/8.8.8.8/json/'
```

Your own IP:

```bash
curl 'https://ipapi.co/json/'
```

## Routing

```bash
ip link
ip addr
ip route
route
```

Add address and routes:

```bash
ip addr add 192.168.1.10/24 dev eth0
ip route add 192.168.1.0/24 via 192.168.2.1
ip route add default via 192.168.2.1
```

Check IP forwarding:

```bash
cat /proc/sys/net/ipv4/ip_forward
```
