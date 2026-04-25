#!/usr/bin/env python3
"""Parallel runner health-check.

Pattern from the article on named pipes:
  - producers (SSH collectors) write results into a queue
  - consumer (display) blocks on queue.get() until data arrives
  - N tasks run concurrently, one per server

asyncio.Queue  ≡  named pipe (FIFO)
queue.put()    ≡  echo ${i} >&3          (producer writes to pipe)
queue.get()    ≡  xargs -n1 -I{} …      (consumer reads from pipe)
task per host  ≡  background worker (&)
"""

import asyncio
import os
from dataclasses import dataclass

SERVERS = [
    "server01",
    "server02",
    "server03",
    "server04",
    "server05",
]

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
    r: int   # runnable processes (R state)
    b: int   # blocked processes  (D state — uninterruptible I/O wait)
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
    key  = os.environ.get("SSH_KEY")
    if user:
        args += ["-l", user]
    if key:
        args += ["-i", key]
    args.append(host)
    args.append(REMOTE)
    return args


async def collect(host: str, queue: asyncio.Queue) -> None:
    """SSH into host, gather metrics, push one Metrics object into the queue.

    Mirrors the bash build-worker that runs in the background (&) and
    writes each result to a named pipe. The queue never fills up here
    because the consumer drains it concurrently on the other side.
    """
    proc = await asyncio.create_subprocess_exec(
        *ssh_cmd(host),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    stdout, _ = await proc.communicate()

    if proc.returncode != 0 or not stdout.strip():
        await queue.put(Metrics(host=host, nproc=1, la1=0, la5=0, la15=0,
                                cpu=0, iowait=0, r=0, b=0, error="UNREACHABLE"))
        return

    nproc, la1, la5, la15, cpu, iowait, r, b = stdout.decode().split()
    await queue.put(Metrics(
        host=host,
        nproc=int(nproc),
        la1=float(la1), la5=float(la5), la15=float(la15),
        cpu=int(cpu), iowait=int(iowait),
        r=int(r), b=int(b),
    ))


async def display(queue: asyncio.Queue, total: int) -> None:
    """Print a result row each time one arrives from the queue.

    Mirrors the xargs consumer reading from a named pipe: blocks on
    queue.get() until a producer writes, then processes and loops.
    Exits after receiving exactly `total` items — no sentinel needed
    because we know the producer count up front.

    Column `b` (blocked) is the D-state count — the key to diagnosing
    high LA with low CPU: processes stuck in I/O, not doing CPU work.
    """
    print(f"{'host':<16}  {'cpu':<5}  {'nproc':<5}  {'la1/la5/la15':<18}  "
          f"{'iowait':<7}  {'r':<4}  {'b':<4}  state")
    print("─" * 82)

    for _ in range(total):
        m = await queue.get()

        if m.error:
            print(f"{m.host:<16}  {m.error}")
            continue

        print(
            f"{m.host:<16}  {m.cpu}%{'':<2}  {m.nproc:<5}  "
            f"{m.la1:<5}/{m.la5:<5}/{m.la15:<6}  "
            f"{m.iowait}%{'':<4}  {m.r:<4}  {m.b:<4}  [{m.state}]"
        )


async def main() -> None:
    """Fan-out: spawn one SSH collector per server, drain results through a shared queue.

    All collectors run concurrently (asyncio.gather equivalent of bash `&`).
    The display consumer runs alongside them, printing rows as they arrive.
    Total wall time ≈ slowest single SSH call, not sum of all calls.
    """
    queue: asyncio.Queue[Metrics] = asyncio.Queue()

    # one task per server — equivalent to launching background workers with &
    collectors = [
        asyncio.create_task(collect(host, queue))
        for host in SERVERS
    ]

    # consumer runs concurrently with collectors
    consumer = asyncio.create_task(display(queue, len(SERVERS)))

    await asyncio.gather(*collectors)
    await consumer


if __name__ == "__main__":
    asyncio.run(main())
