#!/usr/bin/env bash
set -euo pipefail

SERVERS=(
    node-01.example.internal
    node-02.example.internal
    node-03.example.internal
    node-04.example.internal
    node-05.example.internal
)

SSH_USER=${SSH_USER:-}
SSH_KEY=${SSH_KEY:-}

ssh_cmd() {
    local args=()
    [[ -n "$SSH_KEY" ]] && args+=(-i "$SSH_KEY")
    [[ -n "$SSH_USER" ]] && args+=(-l "$SSH_USER")
    ssh "${args[@]}" "$@"
}

REMOTE='
    nproc=$(nproc)
    read la1 la5 la15 _ < /proc/loadavg
    vmstat=$(vmstat 1 2 | tail -1)
    cpu=$(( 100 - $(echo "$vmstat" | awk "{print \$15}") ))
    iowait=$(echo "$vmstat" | awk "{print \$16}")
    r=$(echo "$vmstat" | awk "{print \$1}")
    b=$(echo "$vmstat" | awk "{print \$2}")
    echo "$nproc $la1 $la5 $la15 $cpu $iowait $r $b"
'

check() {
    local host=$1
    local out

    if ! out=$(ssh_cmd "$host" "$REMOTE" 2>/dev/null); then
        printf "%-36s  UNREACHABLE\n" "$host"
        return
    fi

    read -r nproc la1 la5 la15 cpu iowait r b <<< "$out"

    local util state
    util=$(awk "BEGIN { printf \"%d\", ($la1 / $nproc) * 100 }")
    if   (( util <  70 )); then state="ok"
    elif (( util <= 100 )); then state="saturated"
    else                         state="OVERLOADED"
    fi

    printf "%-36s  cpu=%-4s  nproc=%-3s  la=%-5s/%-5s/%-5s  iowait=%-4s  r=%-3s  b=%-3s  [%s]\n" \
        "$host" "${cpu}%" "$nproc" "$la1" "$la5" "$la15" "${iowait}%" "$r" "$b" "$state"
}

printf "%-36s  %-7s  %-7s  %-19s  %-8s  %-5s  %-5s  %s\n" \
    "host" "cpu" "nproc" "la 1/5/15" "iowait" "r" "b" "state"
printf '%0.s─' {1..103}; echo

tmpdir=$(mktemp -d)
trap 'rm -rf "$tmpdir"' EXIT

for host in "${SERVERS[@]}"; do
    check "$host" > "${tmpdir}/${host}" &
done

wait

for host in "${SERVERS[@]}"; do
    cat "${tmpdir}/${host}"
done
