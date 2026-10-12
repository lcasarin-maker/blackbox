#!/bin/bash
journalctl -kf -n 0 --no-pager | while IFS= read -r line; do
    echo "$line" > /dev/udp/<REDACTADO-IP-LAN>/6666 2>/dev/null
done
