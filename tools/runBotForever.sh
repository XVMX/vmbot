#!/bin/sh
while true; do
    python ./vmbot/vmbot.py > info.vmbot.log 2> err.vmbot.log
    echo "'vmbot.py' exited with code $?. Restarting in 5 seconds..." >&2
    sleep 5
done
