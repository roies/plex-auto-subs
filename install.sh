#!/usr/bin/env bash
# One-command installer for plex-subtitle-sync
# Usage: curl -fsSL https://raw.githubusercontent.com/roies/plex-subtitle-sync/master/install.sh | bash

set -e

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()  { echo -e "${GREEN}[+]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
die()   { echo -e "${RED}[x]${NC} $1"; exit 1; }

# ── 1. python ────────────────────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    info "Installing python3..."
    sudo apt-get install -y python3 python3-pip 2>/dev/null || \
    sudo yum install -y python3 python3-pip 2>/dev/null || \
    die "Could not install Python. Install it manually and re-run."
fi
PYTHON=$(command -v python3)
info "Python: $($PYTHON --version)"

# ── 2. ffmpeg ─────────────────────────────────────────────────────────────────
if ! command -v ffmpeg &>/dev/null; then
    info "Installing ffmpeg..."
    sudo apt-get install -y ffmpeg 2>/dev/null || \
    sudo yum install -y ffmpeg 2>/dev/null || \
    warn "Could not auto-install ffmpeg. Install it manually: https://ffmpeg.org/download.html"
fi

# ── 3. pip install ────────────────────────────────────────────────────────────
info "Installing plex-subtitle-sync..."
$PYTHON -m pip install --quiet --upgrade \
    "git+https://github.com/roies/plex-subtitle-sync" \
    ffsubsync argostranslate

DAEMON=$(python3 -c "import sysconfig; print(sysconfig.get_path('scripts'))")/plex-subtitle-sync
[ -f "$DAEMON" ] || DAEMON=$($PYTHON -m site --user-base)/bin/plex-subtitle-sync

# ── 4. Plex token ─────────────────────────────────────────────────────────────
echo ""
echo "Find your Plex token at:"
echo "  Plex Web → Settings → Account → (scroll down) 'Get your Plex token'"
echo "  Or: https://support.plex.tv/articles/204059436"
echo ""
read -rp "Enter your Plex token (leave blank for local no-auth): " PLEX_TOKEN
read -rp "Plex URL [http://localhost:32400]: " PLEX_URL
PLEX_URL="${PLEX_URL:-http://localhost:32400}"

# ── 5. systemd service ────────────────────────────────────────────────────────
SERVICE=/etc/systemd/system/plex-subtitle-sync.service
CURRENT_USER=$(whoami)

info "Writing systemd service to $SERVICE..."
sudo tee "$SERVICE" > /dev/null <<EOF
[Unit]
Description=Plex Subtitle Auto Sync (sync + translate to Hebrew)
After=network.target

[Service]
Type=simple
User=$CURRENT_USER
ExecStart=$DAEMON --url $PLEX_URL --token $PLEX_TOKEN
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now plex-subtitle-sync

echo ""
info "Done! Service is running."
echo ""
echo "  Status : sudo systemctl status plex-subtitle-sync"
echo "  Logs   : sudo journalctl -u plex-subtitle-sync -f"
echo "  Stop   : sudo systemctl stop plex-subtitle-sync"
echo ""
warn "First subtitle detected will download the en→he model (~100MB, one-time)."
