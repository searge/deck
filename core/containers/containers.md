---
tags:
  - containers
  - linux
aliases:
  - Containers
  - Linux Containers
title: Containers
description: Linux containers from first principles — namespaces, cgroups, chroot, unshare, systemd-nspawn, and runc.
---

# containers

Linux containers are not a single technology — they're a combination of kernel features that isolate processes. Understanding what happens under the hood makes you better at debugging, securing, and operating containerized workloads.

## Foundation

### RootFS

A root filesystem is a self-contained directory tree with everything needed to run a Linux userland: binaries, libraries, configuration files, and the standard Unix hierarchy. The container shares the host kernel but brings its own `/bin`, `/lib`, `/etc`, and so on.

This decoupling means you can run Alpine on an Ubuntu host, or Ubuntu on Fedora, or any combination — as long as the architecture matches. An x86_64 Alpine RootFS works on any x86_64 kernel. An ARM64 Debian RootFS works on any ARM64 kernel.

You typically get a RootFS in one of three ways:

- **LXC templates** — compressed tarballs (`.tar.gz`, `.tar.zst`) containing distribution-specific filesystems
- **Bootstrap tools** — `debootstrap` or `dnf --installroot` build fresh filesystems from package repositories
- **Docker images** — exported with `docker export`, produce tarballs that work with any OCI-compatible runtime

Each method gives you the same thing: a directory that becomes `/` inside the container.

### Namespaces

Namespaces provide isolation by giving each container its own view of system resources. The kernel maintains separate instances of global resources — process trees, network stacks, mount tables — and each namespace sees only its own instance.

| Namespace | Flag | Isolates |
|-----------|------|----------|
| Mount (mnt) | `--mount` | Filesystem mount table |
| Process (pid) | `--pid` | Process IDs, PID 1 |
| Network (net) | `--net` | Interfaces, routing, firewall |
| UTS | `--uts` | Hostname, domain name |
| User | `--user` | UIDs/GIDs mapping |
| IPC | `--ipc` | System V IPC, POSIX message queues |
| Cgroup | `--cgroup` | Cgroup hierarchy visibility |

The **user namespace** deserves special attention: a process running as root (UID 0) inside the container maps to an unprivileged UID on the host. This turns privileged containers into unprivileged processes from the host's perspective, reducing the attack surface significantly.

### Execution layers

Different tools provide different levels of container abstraction:

| Tool | What it does | Use case |
|------|-------------|----------|
| `chroot` | Changes root directory | Rescue systems, package builds |
| `unshare` | Creates new namespaces manually | Learning, custom isolation |
| `systemd-nspawn` | Automated namespace management | Development, testing |
| `runc` | OCI-compliant runtime with config.json | Production containers |

Each layer builds on the previous one. `chroot` provides filesystem jail. `unshare` adds namespace isolation. `systemd-nspawn` automates the setup. `runc` standardizes the configuration and lifecycle.

## Obtaining a base RootFS

Download pre-built LXC templates:

```bash
wget https://images.linuxcontainers.org/images/debian/bookworm/amd64/default/20240101_05:24/rootfs.tar.xz
tar xf rootfs.tar.xz
```

Build minimal Debian/Ubuntu with `debootstrap`:

```bash
debootstrap bookworm ./rootfs http://deb.debian.org/debian/
```

Build Fedora/RHEL with `dnf`:

```bash
dnf --installroot=./rootfs --releasever=39 install -y @core
```

Export existing Docker container:

```bash
docker export container_name > rootfs.tar
mkdir rootfs && tar xf rootfs.tar -C ./rootfs
```

## The manual way (chroot + unshare)

Start by creating fresh namespaces. The `--fork` flag is essential for PID namespace — without it, the current shell tries to become PID 1 in the new namespace, which fails.

```bash
unshare --uts --ipc --pid --mount --fork bash
```

Prepare virtual filesystems:

```bash
mount --bind /proc ./rootfs/proc
mount --bind /sys ./rootfs/sys
mount --bind /dev ./rootfs/dev
mount --bind /dev/pts ./rootfs/dev/pts
```

Configure networking:

```bash
cp /etc/resolv.conf ./rootfs/etc/resolv.conf

# Prevent services from starting during package install
cat > ./rootfs/usr/sbin/policy-rc.d << 'EOF'
#!/bin/sh
exit 101
EOF
chmod +x ./rootfs/usr/sbin/policy-rc.d
```

Enter the container:

```bash
chroot ./rootfs /bin/bash
```

When done, unmount in reverse order:

```bash
umount ./rootfs/dev/pts
umount ./rootfs/dev
umount ./rootfs/sys
umount ./rootfs/proc
```

## The systemd way (systemd-nspawn)

Point it at a RootFS and it handles namespaces, mounts, and networking automatically:

```bash
# Interactive shell
systemd-nspawn -D ./rootfs

# Ephemeral (changes discarded on exit)
systemd-nspawn -D ./rootfs --ephemeral

# Full boot (starts init as PID 1)
systemd-nspawn -D ./rootfs --boot
```

Shutting down:

- Regular shell: just type `exit`
- Booted container: `machinectl poweroff <container-name>` from host
- Emergency: `machinectl terminate <container-name>`

## The runc way (OCI runtime)

Generate default config:

```bash
runc spec
```

Edit `config.json` for resource limits:

```json
"resources": {
  "memory": {
    "limit": 536870912
  },
  "cpu": {
    "quota": 50000,
    "period": 100000
  }
}
```

This caps memory at 512MB and CPU at 50% of one core.

Run the container:

```bash
runc run mycontainer
```

Lifecycle commands:

```bash
runc list              # Show running containers
runc kill mycontainer  # Send SIGTERM
runc delete mycontainer # Remove container state
```

## Preparing for distribution

### Sanitization

Before distributing a RootFS, clean up build artifacts:

```bash
# Clear package caches
apt-get clean
rm -rf /var/lib/apt/lists/*

# Reset machine-id (each container generates its own)
truncate -s 0 /etc/machine-id

# Remove policy-rc.d if present
rm -f /usr/sbin/policy-rc.d

# Clear history and temp files
rm -f /root/.bash_history
rm -rf /tmp/* /var/tmp/*
```

### Distribution formats

**Generic tarball** — works everywhere:

```bash
tar --xattrs --numeric-owner -czf rootfs.tar.gz -C ./rootfs .
```

`--numeric-owner` prevents UID/GID mapping issues across systems.

**LXC template** — for Proxmox and LXC:

```bash
tar --xattrs --numeric-owner -I 'zstd -9' -cf rootfs.tar.zst -C ./rootfs .
```

Place in `/var/lib/vz/template/cache/` on Proxmox.

**Docker image** — import into Docker:

```bash
tar --xattrs --numeric-owner -cf rootfs.tar -C ./rootfs .
cat rootfs.tar | docker import - myimage:latest
```

## Historical context

| Year | Event |
|------|-------|
| 1979 | `chroot` jail (Unix v7) |
| 2000 | FreeBSD jails |
| 2005 | OpenVZ (Linux kernel patch) |
| 2006 | Google cgroups |
| 2008 | LXC (first Docker versions used lxc) |
| 2013 | Docker, Google LMCTFY |
| 2015 | Kubernetes |

## See also

- [osi_model](../net/osi_model.md)
- [tcp_ip_model](../net/tcp_ip_model.md)

## References

- [Linux Namespaces Overview](https://man7.org/linux/man-pages/man7/namespaces.7.html)
- [Control Group v2](https://www.kernel.org/doc/html/latest/admin-guide/cgroup-v2.html)
- [OCI Runtime Specification](https://github.com/opencontainers/runtime-spec)
- [systemd-nspawn](https://www.freedesktop.org/software/systemd/man/latest/systemd-nspawn.html)
- [runc](https://github.com/opencontainers/runc)
- [Avoiding CPU Throttling in a Containerized Environment](https://www.uber.com/en-GB/blog/avoiding-cpu-throttling-in-a-containerized-environment/)
