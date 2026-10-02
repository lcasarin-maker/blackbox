#!/bin/bash
if journalctl -k --since "-6min" --no-pager 2>/dev/null | grep -Eq 'NVRM:.*(Out of memory|NV_ERR_NO_MEMORY)'; then
    logger -p daemon.warning -t nvrm-watch "NVRM allocation error observed — evidence only; not a sufficient freeze predictor"
    echo "$(date -Is) NVRM allocation error observed (evidence only)" >> /var/log/nvrm-watch.log
fi
