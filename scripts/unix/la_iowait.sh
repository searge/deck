#!/usr/bin/env bash
# Parallel host load and I/O-wait health-check.
#
# Companion note: core/unix/load_average.md
# Python counterpart: scripts/unix/la_iowait.py
#
# Same fan-out pattern as the Python version, using Bash primitives:
#
#   Named pipe (FIFO)          ≡  asyncio.Queue
#   printf '…' > "$pipe"      ≡  await queue.put(metrics)
#   while read -r line; do …  ≡  m = await queue.get()
#   collect "$host" &          ≡  asyncio.create_task(collect(host, queue))
#   wait "${pids[@]}"          ≡  await asyncio.gather(*collectors)

set -euo pipefail

SSH_USER=${SSH_USER:-}
SSH_KEY=${SSH_KEY:-}
tmpdir=

cleanup() {
    [[ -z "$tmpdir" ]] || rm -rf -- "$tmpdir"
}

trap cleanup EXIT

# Script executed on the remote host — matches fields of Metrics dataclass in Python.
# Single-quoted heredoc: no local expansion; variables expand on the remote side.
REMOTE=$(cat <<'EOF'
nproc=$(nproc)
read la1 la5 la15 _ < /proc/loadavg
vmstat=$(vmstat 1 2 | tail -1)
cpu=$(( 100 - $(echo "$vmstat" | awk '{print $15}') ))
iowait=$(echo "$vmstat" | awk '{print $16}')
r=$(echo "$vmstat" | awk '{print $1}')
b=$(echo "$vmstat" | awk '{print $2}')
printf '%s %s %s %s %s %s %s %s\n' \
    "$nproc" "$la1" "$la5" "$la15" "$cpu" "$iowait" "$r" "$b"
EOF
)

# ssh_cmd — populate an array with the SSH argv for a given host.
# Mirrors: def ssh_cmd(host) -> list[str] in Python.
# Uses a nameref (bash 4.3+) since bash functions cannot return arrays.
ssh_cmd() {
    local -n _cmd=$1  # nameref: caller passes the name of their local array
    local host=$2
    _cmd=(ssh)
    [[ -n "$SSH_USER" ]] && _cmd+=(-l "$SSH_USER")
    [[ -n "$SSH_KEY"  ]] && _cmd+=(-i "$SSH_KEY")
    _cmd+=("$host")
}

# state — classify load from LA/nCPU ratio.
# Mirrors: Metrics.state property in Python.
state() {
    local la1=$1 nproc=$2
    awk -v la1="$la1" -v nproc="$nproc" 'BEGIN {
        util = (la1 / nproc) * 100
        if (util < 70) print "ok"
        else if (util <= 100) print "saturated"
        else print "OVERLOADED"
    }'
}

# collect — SSH into host, write tab-separated raw fields to the pipe.
# Mirrors: async def collect(host, queue) in Python.
# Writes raw data so display() can sort and format with dynamic column widths.
# Error rows use la5=-1 so sort puts them last in descending order.
collect() {
    local host=$1 pipe=$2
    local -a cmd; ssh_cmd cmd "$host"
    local out

    if ! out=$("${cmd[@]}" bash -s <<< "$REMOTE" 2>/dev/null) || [[ -z "$out" ]]; then
        printf '%s\t0\t-1\t-1\t-1\t0\t0\t0\t0\tUNREACHABLE\n' \
            "$host" > "$pipe"
        return
    fi

    local nproc la1 la5 la15 cpu iowait r b extra
    read -r nproc la1 la5 la15 cpu iowait r b extra <<< "$out"
    if [[ -n "$extra" || ! "$nproc" =~ ^[1-9][0-9]*$ ||
          ! "$la1" =~ ^[0-9]+([.][0-9]+)?$ ||
          ! "$la5" =~ ^[0-9]+([.][0-9]+)?$ ||
          ! "$la15" =~ ^[0-9]+([.][0-9]+)?$ ||
          ! "$cpu" =~ ^[0-9]+$ || ! "$iowait" =~ ^[0-9]+$ ||
          ! "$r" =~ ^[0-9]+$ || ! "$b" =~ ^[0-9]+$ ]]; then
        printf '%s\t0\t-1\t-1\t-1\t0\t0\t0\t0\tINVALID_METRICS\n' \
            "$host" > "$pipe"
        return
    fi

    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t\n' \
        "$host" "$nproc" "$la1" "$la5" "$la15" "$cpu" "$iowait" "$r" "$b" \
        > "$pipe"
}

# display — collect all raw lines, sort by la5 descending, format with dynamic widths.
# Mirrors: def display(results, sort_by) in Python.
# Reads raw TSV from the pipe (blocks until all collectors write + parent closes fd 3).
display() {
    local pipe=$1
    local -a raw=()

    # collect all raw TSV lines — ≡ results = [queue.get_nowait() for _ in servers]
    while IFS= read -r line; do
        raw+=("$line")
    done < "$pipe"

    # sort by la5 (field 4, tab-separated) descending; errors (la5=-1) go last
    local sorted
    sorted=$(printf '%s\n' "${raw[@]}" | LC_ALL=C sort -t$'\t' -k4,4gr)

    # compute max width for each column (header lengths are the minimums)
    local w_host=4 w_cpu=3 w_nproc=5 w_la=13 w_iowait=6 w_r=1 w_b=1
    while IFS=$'\t' read -r host nproc la1 la5 la15 cpu iowait r b status; do
        [[ -z "$host" ]] && continue
        local la="${la1}/${la5}/${la15}"
        local cpu_s="${cpu}%" iowait_s="${iowait}%"
        (( ${#host}     > w_host   )) && w_host=${#host}
        (( ${#cpu_s}    > w_cpu    )) && w_cpu=${#cpu_s}
        (( ${#nproc}    > w_nproc  )) && w_nproc=${#nproc}
        (( ${#la}       > w_la     )) && w_la=${#la}
        (( ${#iowait_s} > w_iowait )) && w_iowait=${#iowait_s}
        (( ${#r}        > w_r      )) && w_r=${#r}
        (( ${#b}        > w_b      )) && w_b=${#b}
    done <<< "$sorted"

    local total=$(( w_host + 2 + w_cpu + 2 + w_nproc + 2 + w_la + 2 + w_iowait + 2 + w_r + 2 + w_b + 2 + 5 ))

    printf "%-${w_host}s  %-${w_cpu}s  %-${w_nproc}s  %-${w_la}s  %-${w_iowait}s  %-${w_r}s  %-${w_b}s  %s\n" \
        "host" "cpu" "nproc" "la1/la5↓/la15" "iowait" "r" "b" "state"
    printf '%.0s─' $(seq 1 "$total"); printf '\n'

    while IFS=$'\t' read -r host nproc la1 la5 la15 cpu iowait r b status; do
        [[ -z "$host" ]] && continue
        if [[ -n "$status" ]]; then
            printf "%-${w_host}s  %s\n" "$host" "${status//_/ }"
            continue
        fi
        local s; s=$(state "$la1" "$nproc")
        local la="${la1}/${la5}/${la15}"
        printf "%-${w_host}s  %-${w_cpu}s  %-${w_nproc}s  %-${w_la}s  %-${w_iowait}s  %-${w_r}s  %-${w_b}s  [%s]\n" \
            "$host" "${cpu}%" "$nproc" "$la" "${iowait}%" "$r" "$b" "$s"
    done <<< "$sorted"
}

# main — fan-out: one collector per server, shared named pipe, one display consumer.
# Mirrors: async def main() in Python.
main() {
    local servers_file=${1:?usage: $0 <servers-file>}
    local -a servers=()
    local line
    while IFS= read -r line || [[ -n "$line" ]]; do
        line=${line#"${line%%[![:space:]]*}"}
        line=${line%"${line##*[![:space:]]}"}
        [[ -z "$line" || "$line" == \#* ]] && continue
        servers+=("$line")
    done < "$servers_file"

    if (( ${#servers[@]} == 0 )); then
        printf 'no servers found in %s\n' "$servers_file" >&2
        return 1
    fi

    local pipe
    tmpdir=$(mktemp -d)
    pipe="$tmpdir/results"
    mkfifo "$pipe"

    # Start display first — opens the read end of the pipe
    # ≡ asyncio.create_task(display(queue, len(SERVERS)))
    display "$pipe" &
    local display_pid=$!

    # Keep one write-end open in the parent so display does not get a premature EOF
    # before collectors have started. Closed explicitly after all collectors finish.
    # ≡ queue = asyncio.Queue()
    exec 3>"$pipe"

    # Spawn one collector per server — ≡ asyncio.create_task(collect(host, queue))
    local pids=()
    for host in "${servers[@]}"; do
        collect "$host" "$pipe" &
        pids+=("$!")
    done

    # Wait for all collectors — ≡ await asyncio.gather(*collectors)
    wait "${pids[@]}"

    # Close parent's write-end — no writers left → display reads EOF and exits
    exec 3>&-

    # Wait for display to finish printing — ≡ await consumer
    wait "$display_pid"
}

main "$@"
