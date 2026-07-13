#!/usr/bin/env python3
"""Parallel host load and I/O-wait health-check.

Companion note: core/unix/load_average.md
Bash counterpart: scripts/unix/la_iowait.sh

The collectors run concurrently, one per host, and put their results into an
unbounded asyncio.Queue. After all collectors finish, main drains and sorts the
queue. The Bash version carries the same records through a named pipe (FIFO).
"""

import argparse
import asyncio
import os
from dataclasses import dataclass

SORT_FIELDS = ("la1", "la5", "la15", "cpu", "iowait", "r", "b")


def load_servers(path: str) -> list[str]:
    """Load SSH hosts or aliases, ignoring blank lines and comments."""
    with open(path, encoding="utf-8") as file:
        lines = (line.strip() for line in file)
        return [line for line in lines if line and not line.startswith("#")]


# Collected on the remote host via a single SSH call.
# vmstat 1 2 | tail -1 gives a 1-second CPU sample rather than a snapshot.
REMOTE = """\
nproc=$(nproc)
read la1 la5 la15 _ < /proc/loadavg
vmstat=$(vmstat 1 2 | tail -1)
cpu=$(( 100 - $(echo "$vmstat" | awk '{print $15}') ))
iowait=$(echo "$vmstat" | awk '{print $16}')
r=$(echo "$vmstat" | awk '{print $1}')
b=$(echo "$vmstat" | awk '{print $2}')
printf '%s %s %s %s %s %s %s %s\n' "$nproc" "$la1" "$la5" "$la15" "$cpu" "$iowait" "$r" "$b"
"""


@dataclass
class Metrics:
    host: str
    nproc: int
    la1: float
    la5: float
    la15: float
    cpu: int
    iowait: int
    r: int  # runnable processes (R state)
    b: int  # blocked processes  (D state — uninterruptible I/O wait)
    error: str | None = None

    @property
    def state(self) -> str:
        """Classify load state by LA/nCPU ratio, same thresholds as uptime(1) intuition."""
        util = self.la1 / self.nproc * 100
        if util < 70:
            return "ok"
        if util <= 100:
            return "saturated"
        return "OVERLOADED"


def ssh_cmd(host: str) -> list[str]:
    """Build the SSH argv for a given host.

    Picks up SSH_USER and SSH_KEY from the environment; falls back to
    whatever ssh would use by default (~/.ssh/config, agent, etc.).
    """
    args = ["ssh"]
    user = os.environ.get("SSH_USER")
    key = os.environ.get("SSH_KEY")
    if user:
        args += ["-l", user]
    if key:
        args += ["-i", key]
    args.append(host)
    args.append(REMOTE)
    return args


async def collect(host: str, queue: asyncio.Queue[Metrics]) -> None:
    """SSH into host, gather metrics, push one Metrics object into the queue.

    Mirrors the bash build-worker that runs in the background (&) and
    writes each result to a named pipe. The queue is unbounded; main drains it
    after all collectors finish.
    """
    proc = await asyncio.create_subprocess_exec(
        *ssh_cmd(host),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    stdout, _ = await proc.communicate()

    if proc.returncode != 0 or not stdout.strip():
        await queue.put(
            Metrics(
                host=host,
                nproc=1,
                la1=0,
                la5=0,
                la15=0,
                cpu=0,
                iowait=0,
                r=0,
                b=0,
                error="UNREACHABLE",
            )
        )
        return

    try:
        nproc, la1, la5, la15, cpu, iowait, r, b = stdout.decode().split()
        metrics = Metrics(
            host=host,
            nproc=int(nproc),
            la1=float(la1),
            la5=float(la5),
            la15=float(la15),
            cpu=int(cpu),
            iowait=int(iowait),
            r=int(r),
            b=int(b),
        )
    except (UnicodeDecodeError, ValueError):
        metrics = Metrics(
            host=host,
            nproc=1,
            la1=0,
            la5=0,
            la15=0,
            cpu=0,
            iowait=0,
            r=0,
            b=0,
            error="INVALID METRICS",
        )

    await queue.put(metrics)


def _fmt(m: Metrics) -> tuple[str, ...]:
    return (
        m.host,
        f"{m.cpu}%",
        str(m.nproc),
        f"{m.la1:.2f}/{m.la5:.2f}/{m.la15:.2f}",
        f"{m.iowait}%",
        str(m.r),
        str(m.b),
        f"[{m.state}]",
    )


def display(results: list[Metrics], sort_by: str = "la1") -> None:
    """Sort results, compute column widths, print aligned table.

    Column `b` (blocked) is the D-state count — the key to diagnosing
    high LA with low CPU: processes stuck in I/O, not doing CPU work.
    """
    ok = sorted(
        (m for m in results if not m.error),
        key=lambda m: getattr(m, sort_by),
        reverse=True,
    )
    errors = [m for m in results if m.error]

    la_col = {
        "la1": "la1↓/la5/la15",
        "la5": "la1/la5↓/la15",
        "la15": "la1/la5/la15↓",
    }.get(sort_by, "la1/la5/la15")
    headers = (
        "host",
        "cpu↓" if sort_by == "cpu" else "cpu",
        "nproc",
        la_col,
        "iowait↓" if sort_by == "iowait" else "iowait",
        "r↓" if sort_by == "r" else "r",
        "b↓" if sort_by == "b" else "b",
        "state",
    )
    rows = [_fmt(m) for m in ok]

    widths = [
        max(len(h), max((len(r[i]) for r in rows), default=0))
        for i, h in enumerate(headers)
    ]
    widths[0] = max(widths[0], max((len(m.host) for m in errors), default=0))

    sep = "─" * (sum(widths) + 2 * (len(widths) - 1))
    fmt = "  ".join(f"{{:<{w}}}" for w in widths)

    print(fmt.format(*headers))
    print(sep)
    for row in rows:
        print(fmt.format(*row))
    for m in errors:
        print(f"{m.host:<{widths[0]}}  {m.error}")


async def main() -> None:
    """Fan-out: spawn one SSH collector per server, drain results through a shared queue.

    All collectors run concurrently (asyncio.gather equivalent of bash `&`).
    Results are collected, sorted, then displayed with dynamic column widths.
    Total wall time ≈ slowest single SSH call, not sum of all calls.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("servers_file", help="one SSH host or alias per line")
    parser.add_argument(
        "sort_by",
        choices=SORT_FIELDS,
        default="la5",
        nargs="?",
        help="metric to sort descending (default: la5)",
    )
    args = parser.parse_args()

    servers = load_servers(args.servers_file)
    if not servers:
        parser.error(f"no servers found in {args.servers_file}")

    queue: asyncio.Queue[Metrics] = asyncio.Queue()

    # one task per server — equivalent to launching background workers with &
    collectors = [
        asyncio.create_task(collect(host, queue)) for host in servers
    ]

    # wait for all collectors, then drain the queue synchronously
    await asyncio.gather(*collectors)
    results = [queue.get_nowait() for _ in servers]
    display(results, args.sort_by)


if __name__ == "__main__":
    asyncio.run(main())
