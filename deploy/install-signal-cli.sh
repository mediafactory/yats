#!/usr/bin/env bash
#
# Install / update signal-cli on mf-yats-1 and create per-web config dirs.
# signal-cli needs Java 21+ (provided via openjdk-21-jre-headless in cloud-init).
#
# Usage:  sudo ./install-signal-cli.sh
# Env:    SIGNAL_CLI_VERSION (default below), SITES, YATS_USER
set -euo pipefail

SIGNAL_CLI_VERSION="${SIGNAL_CLI_VERSION:-0.13.18}"
SITES="${SITES:-mf bagarino schiwago}"
YATS_USER="${YATS_USER:-yats}"
ARCH="$(uname -m)"   # x86_64 on Hetzner cloud
TARBALL="signal-cli-${SIGNAL_CLI_VERSION}-Linux-${ARCH}.tar.gz"
URL="https://github.com/AsamK/signal-cli/releases/download/v${SIGNAL_CLI_VERSION}/${TARBALL}"

if [[ $EUID -ne 0 ]]; then echo "run as root" >&2; exit 1; fi

# 1) Java present?
if ! java -version >/dev/null 2>&1; then
    echo "ERROR: Java not found. Install openjdk-21-jre-headless first (cloud-init does this)." >&2
    exit 1
fi

# 2) Download + unpack (idempotent: skip if this version already installed).
DEST="/opt/signal-cli-${SIGNAL_CLI_VERSION}"
if [[ ! -d "$DEST" ]]; then
    echo "Downloading signal-cli ${SIGNAL_CLI_VERSION} ..."
    tmp="$(mktemp -d)"
    curl -fsSL "$URL" -o "${tmp}/${TARBALL}"
    mkdir -p "$DEST"
    tar -xzf "${tmp}/${TARBALL}" -C "$DEST" --strip-components=1
    rm -rf "$tmp"
fi

# 3) Stable symlinks.
ln -sfn "$DEST" /opt/signal-cli
ln -sfn /opt/signal-cli/bin/signal-cli /usr/local/bin/signal-cli
echo "signal-cli -> $(/usr/local/bin/signal-cli --version || true)"

# 4) Per-web config dirs (owned by the service user; signal-cli runs via sudo
#    but reads/writes its account state here).
install -d -m 0700 -o "$YATS_USER" -g "$YATS_USER" /var/lib/signal-cli
for site in $SITES; do
    install -d -m 0700 -o "$YATS_USER" -g "$YATS_USER" "/var/lib/signal-cli/${site}"
done

echo "Done. Register each web's number — see deploy/signal/register.md"
