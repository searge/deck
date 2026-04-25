#!/usr/bin/env bash
# Parallel runner health-check.
#
# Same fan-out pattern as check-runners.py, using bash primitives:
#
#   Named pipe (FIFO)          ≡  asyncio.Queue
#   printf '…' > "$pipe"      ≡  await queue.put(metrics)
#   while read -r line; do …  ≡  m = await queue.get()
#   collect "$host" &          ≡  asyncio.create_task(collect(host, queue))
#   wait "${pids[@]}"          ≡  await asyncio.gather(*collectors)

set -euo pipefail

SERVERS=(
    server01
    server02
    server03
    server04
    server05
)

SSH_USER=${SSH_USER:-}
SSH_KEY=${SSH_KEY:-}

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
    local util
    util=$(awk "BEGIN { printf \"%d\", ($la1 / $nproc) * 100 }")
    if   (( util <  70 )); then echo "ok"
    elif (( util <= 100 )); then echo "saturated"
    else                         echo "OVERLOADED"
    fi
}

# collect — SSH into host, format one result row, write it to the pipe.
# Mirrors: async def collect(host, queue) in Python.
# Writing to the named pipe ≡ await queue.put(metrics)
collect() {
    local host=$1 pipe=$2
    local -a cmd; ssh_cmd cmd "$host"
    local out

    if ! out=$("${cmd[@]}" bash -s <<< "$REMOTE" 2>/dev/null); then
        printf '%-16s  UNREACHABLE\n' "$host" > "$pipe"
        return
    fi

    read -r nproc la1 la5 la15 cpu iowait r b <<< "$out"
    local s; s=$(state "$la1" "$nproc")

    # one formatted line per host — ≡ await queue.put(metrics)
    printf '%-16s  %s%%   %-5s  %-5s/%-5s/%-6s  %s%%    %-4s  %-4s  [%s]\n' \
        "$host" "$cpu" "$nproc" "$la1" "$la5" "$la15" "$iowait" "$r" "$b" "$s" \
        > "$pipe"
}

# display — print header then stream rows from the pipe as they arrive.
# Mirrors: async def display(queue, total) in Python.
# Each read blocks until a collector writes — ≡ m = await queue.get()
display() {
    local pipe=$1

    printf '%-16s  %-5s  %-5s  %-18s  %-7s  %-4s  %-4s  %s\n' \
        "host" "cpu" "nproc" "la1/la5/la15" "iowait" "r" "b" "state"
    printf '%0.s─' {1..82}; printf '\n'

    # blocks on each read until a producer writes; exits when all writers close
    # ≡ m = await queue.get()  (repeated until queue is drained)
    while IFS= read -r line; do
        printf '%s\n' "$line"
    done < "$pipe"
}

# main — fan-out: one collector per server, shared named pipe, one display consumer.
# Mirrors: async def main() in Python.
main() {
    local tmpdir pipe
    tmpdir=$(mktemp -d)
    pipe="$tmpdir/results"
    trap "rm -rf '$tmpdir'" EXIT
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
    for host in "${SERVERS[@]}"; do
        collect "$host" "$pipe" &
        pids+=($!)
    done

    # Wait for all collectors — ≡ await asyncio.gather(*collectors)
    wait "${pids[@]}"

    # Close parent's write-end — no writers left → display reads EOF and exits
    exec 3>&-

    # Wait for display to finish printing — ≡ await consumer
    wait "$display_pid"
}

main
