#!/bin/sh
while true; do
    python -m vmbot
    echo "$(date "+%b %d %H:%M:%S"): VMBot exited with code $?. Restarting in 5 seconds..." >&2
    sleep 5
done
