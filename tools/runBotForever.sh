#!/bin/sh
while true; do
    python vmbot/vmbot.py > /dev/null 2> err.vmbot.log
    echo "'vmbot.py' exited with code $?. Restarting..." >&2
    sleep 3
done
