#!/usr/bin/env bash
#
# Install / update signal-cli on mf-yats-1 and create per-web config dirs.
# signal-cli needs Java 21+ (provided via openjdk-21-jre-headless in cloud-init).
#
# Usage:  sudo ./install-signal-cli.sh
# Env:    SIGNAL_CLI_VERSION (default below), SITES, YATS_USER
set -euo pipefail

SIGNAL_CLI_VERSION="${SIGNAL_CLI_VERSION:-0.14.5}"
SITES="${SITES:-mf bagarino schiwago}"
YATS_USER="${YATS_USER:-yats}"
# GraalVM native build — a single self-contained binary, NO Java needed (avoids
# signal-cli's fast-moving JRE requirement, e.g. 0.14.x needs Java 25). Asset is
# signal-cli-<version>-Linux-native.tar.gz and unpacks to a single ./signal-cli.
TARBALL="signal-cli-${SIGNAL_CLI_VERSION}-Linux-native.tar.gz"
URL="https://github.com/AsamK/signal-cli/releases/download/v${SIGNAL_CLI_VERSION}/${TARBALL}"

if [[ $EUID -ne 0 ]]; then echo "run as root" >&2; exit 1; fi

# 1) Download + unpack (idempotent: skip if this version already installed).
DEST="/opt/signal-cli-${SIGNAL_CLI_VERSION}"
if [[ ! -d "$DEST" ]]; then
    echo "Downloading signal-cli ${SIGNAL_CLI_VERSION} (native) ..."
    tmp="$(mktemp -d)"
    curl -fsSL "$URL" -o "${tmp}/${TARBALL}"
    mkdir -p "$DEST"
    tar -xzf "${tmp}/${TARBALL}" -C "$DEST"
    rm -rf "$tmp"
fi

# 2) Stable symlinks. Native build => ./signal-cli; Java build => ./bin/signal-cli.
ln -sfn "$DEST" /opt/signal-cli
if [[ -x /opt/signal-cli/bin/signal-cli ]]; then
    BIN=/opt/signal-cli/bin/signal-cli
else
    BIN=/opt/signal-cli/signal-cli
fi
chmod +x "$BIN" 2>/dev/null || true
ln -sfn "$BIN" /usr/local/bin/signal-cli
echo "signal-cli -> $(/usr/local/bin/signal-cli --version 2>&1 | head -1 || true)"

# 4) Per-web config dirs (owned by the service user; signal-cli runs via sudo
#    but reads/writes its account state here).
install -d -m 0700 -o "$YATS_USER" -g "$YATS_USER" /var/lib/signal-cli
for site in $SITES; do
    install -d -m 0700 -o "$YATS_USER" -g "$YATS_USER" "/var/lib/signal-cli/${site}"
done

echo "Done. Register each web's number — see deploy/signal/register.md"
