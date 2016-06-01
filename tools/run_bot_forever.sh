#!/bin/sh
while :
do
    python -m vmbot
    echo "$(date "+%b %d %H:%M:%S"): VMBot exited with code $?. Restarting in 3 seconds..." >&2
    sleep 3
done
