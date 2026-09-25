#!/bin/bash
if journalctl -k --since "-6min" --no-pager 2>/dev/null | grep -q "NVRM:.*Out of memory"; then
    logger -p daemon.warning -t nvrm-watch "NVRM Out-of-memory detectado — posible precursor de freeze de GPU"
    echo "$(date -Is) NVRM OOM detectado" >> /var/log/nvrm-watch.log
fi
