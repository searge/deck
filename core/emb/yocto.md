---
tags:
  - embedded
  - linux
  - build-systems
aliases:
  - Yocto
  - Yocto Project
title: Yocto Project
description: Yocto build framework for custom embedded Linux — BitBake, layers, recipes, and CI/CD integration.
---

# yocto

Yocto Project is a build framework for creating custom Linux distributions for embedded devices. It's not a distribution itself — it's a set of tools and metadata that lets you build exactly the Linux system you need, with only the components you need.

The project emerged from OpenEmbedded in 2010, backed by the Linux Foundation. It's used in automotive (AGL), robotics, industrial IoT, and consumer electronics. When you see "powered by Yocto" on a device, it means someone built a custom Linux for that specific hardware.

Why not just use Debian or Ubuntu? Embedded systems have constraints: limited storage (maybe 64MB flash), specific hardware (custom SoCs, FPGAs), real-time requirements, and long-term maintenance (10+ year product lifecycles). Yocto gives you control over every package, kernel config, and init system.

## Core concepts

**Poky** is the reference distribution — a working example you clone and customize. It includes:

- BitBake (build engine)
- OpenEmbedded-Core (core recipes)
- meta-poky (distribution policy)
- meta-yocto-bsp (reference BSPs)

**BitBake** is the build engine. Think of it as make on steroids — it parses recipes, resolves dependencies, fetches sources, and orchestrates builds across many packages. It handles parallel builds and caching.

**Recipes** (`.bb` files) describe how to build a single component:

```bitbake
SUMMARY = "Hello World application"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=..."

SRC_URI = "git://github.com/example/hello.git;branch=main"
SRCREV = "abc123..."

S = "${WORKDIR}/git"

do_compile() {
    ${CC} ${CFLAGS} -o hello hello.c
}

do_install() {
    install -d ${D}${bindir}
    install -m 0755 hello ${D}${bindir}
}
```

**Layers** organize recipes by function or hardware. Layer names start with `meta-`:

```text
meta-poky/           # Distribution policy
meta-openembedded/   # Community packages
meta-raspberrypi/    # RPi BSP
meta-ros/            # ROS/ROS2 integration
meta-custom/         # Your project-specific recipes
```

**Machine** defines target hardware — CPU architecture, kernel config, bootloader. `MACHINE = "raspberrypi4-64"` tells BitBake to build for that board.

**Distro** defines distribution policy — init system, package format, default features. `DISTRO = "poky"` uses the reference; you'd create your own for production.

**Image** is the final output — a root filesystem with selected packages. `core-image-minimal` gives you a bootable system with shell. `core-image-full-cmdline` adds common CLI tools.

## Build directory structure

After sourcing the environment:

```text
build/
├── conf/
│   ├── local.conf      # Build configuration
│   └── bblayers.conf   # Layer configuration
├── tmp/
│   ├── deploy/
│   │   └── images/     # Output images
│   ├── work/           # Package build directories
│   └── sysroots/       # Cross-compilation sysroots
└── downloads/          # Cached source tarballs
```

## The build process

1. **Parse** — BitBake reads all recipes, resolves dependencies
2. **Fetch** — downloads sources (git, http, local files)
3. **Unpack** — extracts sources to work directory
4. **Patch** — applies patches from recipe
5. **Configure** — runs autoconf, cmake, etc.
6. **Compile** — cross-compiles for target
7. **Install** — installs to staging directory
8. **Package** — creates rpm/deb/ipk packages
9. **Image** — assembles packages into rootfs

Each step is a "task" you can run individually: `bitbake -c compile recipe-name`.

## Setting up

On Ubuntu/Debian:

```bash
# Dependencies
apt install gawk wget git diffstat unzip texinfo gcc build-essential \
    chrpath socat cpio python3 python3-pip python3-pexpect xz-utils \
    debianutils iputils-ping python3-git python3-jinja2 python3-subunit \
    zstd liblz4-tool file locales libacl1

# Clone Poky (kirkstone is current LTS)
git clone -b kirkstone git://git.yoctoproject.org/poky
cd poky

# Initialize build environment
source oe-init-build-env build
```

## Configuration

Edit `conf/local.conf`:

```bash
# Target machine
MACHINE = "qemux86-64"

# Parallel builds (adjust to your CPU)
BB_NUMBER_THREADS = "8"
PARALLEL_MAKE = "-j 8"

# Package format
PACKAGE_CLASSES = "package_rpm"

# Extra image features
EXTRA_IMAGE_FEATURES += "debug-tweaks ssh-server-openssh"

# Keep downloads and sstate between builds
DL_DIR = "${TOPDIR}/../downloads"
SSTATE_DIR = "${TOPDIR}/../sstate-cache"
```

Edit `conf/bblayers.conf` to add layers:

```bash
BBLAYERS ?= " \
  /path/to/poky/meta \
  /path/to/poky/meta-poky \
  /path/to/poky/meta-yocto-bsp \
  /path/to/meta-openembedded/meta-oe \
  /path/to/meta-custom \
"
```

## Building an image

```bash
# Minimal image (boots to shell)
bitbake core-image-minimal

# With more tools
bitbake core-image-full-cmdline

# Build specific package
bitbake busybox

# Run specific task
bitbake -c compile linux-yocto
```

First build takes hours — it's building toolchain, kernel, and hundreds of packages from source. Subsequent builds use cached artifacts (sstate).

## Testing with QEMU

```bash
# After building core-image-minimal
runqemu qemux86-64

# Without graphics
runqemu qemux86-64 nographic

# With network
runqemu qemux86-64 slirp
```

## Creating a custom layer

```bash
# Create layer structure
bitbake-layers create-layer meta-myproject

# Add to build
bitbake-layers add-layer meta-myproject
```

Layer structure:

```text
meta-myproject/
├── conf/
│   └── layer.conf
├── recipes-core/
│   └── images/
│       └── myproject-image.bb
├── recipes-apps/
│   └── myapp/
│       ├── myapp_1.0.bb
│       └── files/
│           └── myapp.service
└── README
```

## Writing a recipe

Simple application recipe:

```bitbake
# recipes-apps/myapp/myapp_1.0.bb
SUMMARY = "My custom application"
DESCRIPTION = "Does something useful"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "file://myapp.c \
           file://myapp.service"

S = "${WORKDIR}"

do_compile() {
    ${CC} ${CFLAGS} ${LDFLAGS} -o myapp myapp.c
}

do_install() {
    install -d ${D}${bindir}
    install -m 0755 myapp ${D}${bindir}

    # Systemd service
    install -d ${D}${systemd_unitdir}/system
    install -m 0644 ${WORKDIR}/myapp.service ${D}${systemd_unitdir}/system/
}

inherit systemd
SYSTEMD_SERVICE:${PN} = "myapp.service"
```

## Custom image recipe

```bitbake
# recipes-core/images/myproject-image.bb
SUMMARY = "My Project Image"

IMAGE_INSTALL = " \
    packagegroup-core-boot \
    ${CORE_IMAGE_EXTRA_INSTALL} \
    myapp \
    openssh \
    python3 \
"

IMAGE_FEATURES += "ssh-server-openssh"

inherit core-image
```

Build with `bitbake myproject-image`.

## Yocto for robotics

### meta-ros layer

```bash
git clone -b kirkstone https://github.com/ros/meta-ros.git

# Add to bblayers.conf
BBLAYERS += " \
  /path/to/meta-ros/meta-ros-common \
  /path/to/meta-ros/meta-ros2 \
  /path/to/meta-ros/meta-ros2-humble \
"
```

In `local.conf`:

```bash
ROS_DISTRO = "humble"
```

### Real-time kernel

For robotics, you often need PREEMPT_RT:

```bitbake
# In local.conf or machine config
PREFERRED_PROVIDER_virtual/kernel = "linux-yocto-rt"
```

### Typical robotics image

```bitbake
SUMMARY = "Robot Base Image"

IMAGE_INSTALL = " \
    packagegroup-core-boot \
    ros-humble-ros-base \
    ros-humble-sensor-msgs \
    ros-humble-geometry-msgs \
    python3-numpy \
    can-utils \
    i2c-tools \
    openssh \
"

PREFERRED_PROVIDER_virtual/kernel = "linux-yocto-rt"
IMAGE_FEATURES += "read-only-rootfs"

inherit core-image
```

## CI/CD integration

Yocto builds are slow and resource-intensive. CI strategies:

**Shared sstate cache** — build artifacts are cached, share across CI runners:

```yaml
# GitLab CI example
variables:
  SSTATE_DIR: /mnt/yocto-cache/sstate
  DL_DIR: /mnt/yocto-cache/downloads

build:
  script:
    - source oe-init-build-env build
    - bitbake core-image-minimal
  cache:
    paths:
      - build/sstate-cache/
```

**Container builds** — use CROPS (Cross-platform Yocto Docker):

```bash
docker run --rm -it \
  -v $(pwd):/workdir \
  -v /mnt/cache/downloads:/downloads \
  -v /mnt/cache/sstate:/sstate \
  crops/poky:kirkstone \
  --workdir=/workdir
```

## Deployment

Output images in `tmp/deploy/images/MACHINE/`:

```text
core-image-minimal-qemux86-64.wic.gz   # Full disk image
core-image-minimal-qemux86-64.tar.bz2  # Root filesystem
bzImage                                  # Kernel
modules-*.tgz                           # Kernel modules
```

Flash to SD card:

```bash
zcat core-image-minimal-raspberrypi4-64.wic.gz | sudo dd of=/dev/sdX bs=4M
```

For OTA updates:

- [SWUpdate](https://sbabic.github.io/swupdate/) — A/B updates
- [Mender](https://mender.io/) — OTA platform
- [OSTree](https://ostreedev.github.io/ostree/) — atomic updates

## Common tasks

### Adding a package

```bash
# Search layers
bitbake-layers show-recipes | grep package-name
```

If exists, add to image:

```bitbake
IMAGE_INSTALL += "package-name"
```

### Modifying kernel config

```bash
# Open menuconfig
bitbake -c menuconfig virtual/kernel

# Save fragment
bitbake -c savedefconfig virtual/kernel
```

Or use a config fragment in your layer:

```bitbake
# recipes-kernel/linux/linux-yocto_%.bbappend
FILESEXTRAPATHS:prepend := "${THISDIR}/files:"
SRC_URI += "file://custom.cfg"
```

### Debugging build failures

```bash
# Opens shell in work directory
bitbake -c devshell recipe-name

# Check logs
cat tmp/work/*/recipe-name/*/temp/log.do_compile

# Rebuild from scratch
bitbake -c cleansstate recipe-name
bitbake recipe-name
```

### Checking dependencies

```bash
# Show recipe dependencies
bitbake -g recipe-name
cat pn-buildlist

# Visualize (needs graphviz)
bitbake -g recipe-name && dot -Tpng task-depends.dot -o depends.png
```

## See also

- [containers](../ct/ct.md)
- [dds](../net/dds.md)

## References

- [Yocto Project Documentation](https://docs.yoctoproject.org/)
- [Yocto Quick Build](https://docs.yoctoproject.org/brief-yoctoprojectqs/index.html)
- [BitBake User Manual](https://docs.yoctoproject.org/bitbake/index.html)
- [OpenEmbedded Layer Index](https://layers.openembedded.org/)
- [meta-raspberrypi](https://github.com/agherzan/meta-raspberrypi)
