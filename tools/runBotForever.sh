#!/bin/sh
while true; do
    python ./vmbot/vmbot.py > ./out.vmbot.log 2> ./err.vmbot.log
    echo "$(date "+%b %d %H:%M:%S"): \"vmbot.py\" exited with code $?. Restarting in 5 seconds..." >&2
    sleep 5
done
