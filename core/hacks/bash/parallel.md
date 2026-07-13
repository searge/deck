---
tags:
  - bash
  - linux
  - parallel
aliases:
  - Bash Parallel
title: Bash Parallel
description: Running multiple commands in parallel from bash — jobs, parallel, coproc.
---
# bash parallel

Run multiple commands simultaneously from bash. No external orchestration — just shell primitives.

## & + wait

Background each job, prefix output with label, wait for all:

```bash
MODELS=(gemma4:31b gemma4:e4b gemma4:e2b)

for m in "${MODELS[@]}"; do
    ollama pull "$m" 2>&1 | sed "s/^/[$m] /" &
done
wait
```

Same pattern for ssh:

```bash
SERVERS=(web1 web2 web3)
CMD="apt update && apt upgrade -y"

for host in "${SERVERS[@]}"; do
    ssh "$host" "$CMD" 2>&1 | sed "s/^/[$host] /" &
done
wait
```

## bounded parallelism

Don't spawn unlimited jobs — cap with `wait -n` (bash 4.3+):

```bash
N=3
for m in "${MODELS[@]}"; do
    ollama pull "$m" &
    (( $(jobs -r | wc -l) >= N )) && wait -n
done
wait
```

## GNU parallel

Cleaner syntax, same result:

```bash
parallel ollama pull ::: gemma4:31b gemma4:e4b gemma4:e2b
```

With real-time output and labels:

```bash
MODELS=(gemma4:31b gemma4:e4b gemma4:e2b)
parallel --tag --line-buffer ollama pull ::: "${MODELS[@]}"
```

`--line-buffer` — streams output line by line instead of buffering until job completion.  
`--tag` — prefixes each line with the job argument.

## named pipes (fan-out + sync)

Use FIFOs as signals between parallel processes. Three phases — create, fan out, sync:

```bash
IMAGE="myapp:1.0"
REGISTRIES=(registry1.io registry2.io)

# 1. create signal pipes
for reg in "${REGISTRIES[@]}"; do
    mkfifo "/tmp/${reg}.fifo"
done

# 2. fan out — each job signals done via its pipe
for reg in "${REGISTRIES[@]}"; do
    (docker push "${reg}/${IMAGE}" && echo done > "/tmp/${reg}.fifo") &
done

# 3. sync — block until each pipe signals
for reg in "${REGISTRIES[@]}"; do
    cat "/tmp/${reg}.fifo" > /dev/null
    rm "/tmp/${reg}.fifo"
done

trigger_webhook "$IMAGE"
```

Collapsed into one loop — each iteration owns its pipe lifecycle (create → use → cleanup):

```bash
for reg in "${REGISTRIES[@]}"; do
    mkfifo "/tmp/${reg}.fifo"
    (docker push "${reg}/${IMAGE}" && echo done > "/tmp/${reg}.fifo") &
    (cat "/tmp/${reg}.fifo" > /dev/null && rm "/tmp/${reg}.fifo") &
done
wait

trigger_webhook "$IMAGE"
```

## coproc

Bidirectional channel to a persistent background process:

```bash
coproc PROC { python3 -u -c "
import sys
for line in sys.stdin:
    print(line.strip().upper())
    sys.stdout.flush()
"; }

echo "hello" >&"${PROC[1]}"
read result <&"${PROC[0]}"
echo "$result"  # HELLO
```

Use when you need to keep a long-running process alive and pass data back and forth — interactive CLI, database, language server.

## Practical example

[`scripts/unix/la_iowait.sh`](https://github.com/searge/deck/blob/main/scripts/unix/la_iowait.sh)
uses background SSH collectors and one shared FIFO to build a sorted fleet
health table. See [Load Average](unix/load_average.md) for the metrics,
input format, and the equivalent `asyncio` implementation.

## See also

- [bash](bash.md)
