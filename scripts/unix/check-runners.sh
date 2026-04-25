#!/usr/bin/env bash
set -euo pipefail

SERVERS=(
    runner-01-adyax.galaxy.intranet
    runner-02-adyax.galaxy.intranet
    runner-03-adyax.galaxy.intranet
    runner-04-adyax.galaxy.intranet
    runner-05-adyax.galaxy.intranet
)

SSH_USER=${SSH_USER:-ubuntu}
SSH_OPTS="-o ConnectTimeout=5 -o StrictHostKeyChecking=no -o BatchMode=yes"

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

    if ! out=$(ssh $SSH_OPTS "${SSH_USER}@${host}" "$REMOTE" 2>/dev/null); then
        printf "%-38s  UNREACHABLE\n" "$host"
        return
    fi

    read -r nproc la1 la5 la15 cpu iowait r b <<< "$out"

    local util state
    util=$(awk "BEGIN { printf \"%d\", ($la1 / $nproc) * 100 }")
    if   (( util <  70 )); then state="ok"
    elif (( util <= 100 )); then state="saturated"
    else                         state="OVERLOADED"
    fi

    printf "%-38s  cpu=%-3s  nproc=%-3s  la=%-5s/%-5s/%-5s  iowait=%-3s  r=%-3s  b=%-3s  [%s]\n" \
        "$host" "${cpu}%" "$nproc" "$la1" "$la5" "$la15" "${iowait}%" "$r" "$b" "$state"
}

printf "%-38s  %-7s  %-7s  %-19s  %-8s  %-5s  %-5s  %s\n" \
    "host" "cpu" "nproc" "la 1/5/15" "iowait" "r" "b" "state"
printf '%0.s─' {1..105}; echo

tmpdir=$(mktemp -d)
trap 'rm -rf "$tmpdir"' EXIT

for host in "${SERVERS[@]}"; do
    check "$host" > "${tmpdir}/${host}" &
done

wait

for host in "${SERVERS[@]}"; do
    cat "${tmpdir}/${host}"
done
