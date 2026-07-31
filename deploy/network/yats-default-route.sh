#!/bin/sh
# Hetzner private networks do not push a default route, and the interface IP is a
# /32 — so the default route can only be installed AFTER DHCP has added the
# on-link route to the gateway. Retry until that succeeds (handles boot timing;
# avoids the "Nexthop has invalid gateway" failure when run too early).
#
# Installed as /usr/local/sbin/yats-default-route.sh, run by yats-default-route.service.
GW="${YATS_GATEWAY:-10.150.20.1}"
for i in $(seq 1 60); do
    if ip route replace default via "$GW" 2>/dev/null; then
        exit 0
    fi
    sleep 2
done
echo "could not set default route via $GW after 120s" >&2
exit 1
