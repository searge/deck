#!/usr/bin/env bash
# Build two network namespaces connected through one Linux bridge.
# Dry-run by default. --apply requires root and removes all created state.

set -euo pipefail

mode=dry-run
subnet_cidr=198.18.42.0/24
subnet_set=false
while (( $# )); do
    case $1 in
        --apply)
            mode=apply
            shift
            ;;
        --subnet)
            (( $# >= 2 )) || {
                printf '%s\n' '--subnet requires an IPv4 /24' >&2
                exit 2
            }
            subnet_cidr=$2
            subnet_set=true
            shift 2
            ;;
        -h|--help)
            printf 'usage: %s [--apply --subnet IPV4/24]\n' "$0"
            exit 0
            ;;
        *)
            printf 'unknown argument: %s\n' "$1" >&2
            exit 2
            ;;
    esac
done

network=${subnet_cidr%/*}
prefix=${subnet_cidr#*/}
IFS=. read -r o1 o2 o3 o4 extra <<< "$network"
if [[ $prefix != 24 || -n ${extra:-} || ${o4:-} != 0 ]]; then
    printf 'subnet must be an IPv4 /24 network: %s\n' "$subnet_cidr" >&2
    exit 2
fi
for octet_value in "$o1" "$o2" "$o3" "$o4"; do
    if [[ ! $octet_value =~ ^[0-9]+$ ]] || (( octet_value > 255 )); then
        printf 'invalid IPv4 subnet: %s\n' "$subnet_cidr" >&2
        exit 2
    fi
done
subnet="${o1}.${o2}.${o3}"

suffix=$(( (RANDOM << 1 ^ RANDOM ^ $$) % 100000 ))
ns_a="kn-${suffix}-a"
ns_b="kn-${suffix}-b"
bridge="knbr${suffix}"
host_a="kn${suffix}a0"
peer_a="kn${suffix}a1"
host_b="kn${suffix}b0"
peer_b="kn${suffix}b1"

# Linux interface names are limited to 15 bytes.
bridge=${bridge:0:15}
host_a=${host_a:0:15}
peer_a=${peer_a:0:15}
host_b=${host_b:0:15}
peer_b=${peer_b:0:15}

created_ns_a=false
created_ns_b=false
created_bridge=false
created_veth_a=false
created_veth_b=false

cleanup() {
    [[ $created_ns_a == true ]] && ip netns del "$ns_a" 2>/dev/null || true
    [[ $created_ns_b == true ]] && ip netns del "$ns_b" 2>/dev/null || true
    [[ $created_veth_a == true ]] && ip link del "$host_a" 2>/dev/null || true
    [[ $created_veth_b == true ]] && ip link del "$host_b" 2>/dev/null || true
    [[ $created_bridge == true ]] && ip link del "$bridge" 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

run() {
    if [[ $mode == dry-run ]]; then
        printf '+'
        printf ' %q' "$@"
        printf '\n'
        return
    fi
    "$@"
}

if [[ $mode == apply ]]; then
    [[ $subnet_set == true ]] || {
        printf '%s\n' '--apply requires an explicitly selected --subnet' >&2
        exit 1
    }
    (( EUID == 0 )) || {
        printf '%s\n' '--apply requires root' >&2
        exit 1
    }
    for command in ip ping; do
        command -v "$command" >/dev/null || {
            printf 'missing command: %s\n' "$command" >&2
            exit 1
        }
    done
    if [[ -n $(ip route show "$subnet_cidr") ]]; then
        printf 'route already exists: %s\n' "$subnet_cidr" >&2
        exit 1
    fi
fi

printf 'mode=%s subnet=%s\n' "$mode" "$subnet_cidr"
if [[ $mode == apply ]]; then
    printf '%s\n' \
        'caller confirmed this subnet is unused on a disposable host'
fi

run ip netns add "$ns_a"
[[ $mode == apply ]] && created_ns_a=true
run ip netns add "$ns_b"
[[ $mode == apply ]] && created_ns_b=true
run ip link add "$bridge" type bridge
[[ $mode == apply ]] && created_bridge=true
run ip link set "$bridge" up
run ip address add "${subnet}.1/24" dev "$bridge"

run ip link add "$host_a" type veth peer name "$peer_a"
[[ $mode == apply ]] && created_veth_a=true
run ip link add "$host_b" type veth peer name "$peer_b"
[[ $mode == apply ]] && created_veth_b=true
run ip link set "$host_a" master "$bridge"
run ip link set "$host_b" master "$bridge"
run ip link set "$host_a" up
run ip link set "$host_b" up

run ip link set "$peer_a" netns "$ns_a"
run ip link set "$peer_b" netns "$ns_b"
run ip -n "$ns_a" link set lo up
run ip -n "$ns_b" link set lo up
run ip -n "$ns_a" link set "$peer_a" name eth0
run ip -n "$ns_b" link set "$peer_b" name eth0
run ip -n "$ns_a" address add "${subnet}.11/24" dev eth0
run ip -n "$ns_b" address add "${subnet}.12/24" dev eth0
run ip -n "$ns_a" link set eth0 up
run ip -n "$ns_b" link set eth0 up

run ip -n "$ns_a" -br address
run ip -n "$ns_a" route
run ip -n "$ns_b" -br address
run ip -n "$ns_b" route
run ip netns exec "$ns_a" ping -c 2 -W 1 "${subnet}.12"
run ip -n "$ns_a" neigh show

if [[ $mode == dry-run ]]; then
    printf '%s\n' 'dry-run only; use --apply as root to execute'
else
    printf '%s\n' 'connectivity passed; cleanup runs on exit'
fi
