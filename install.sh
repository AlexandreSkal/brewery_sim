#!/usr/bin/env bash
# =============================================================================
# install.sh — Brewery Simulator setup for Oracle Cloud Linux ARM (aarch64)
# Tested on: Oracle Linux 8/9, Ubuntu 22.04/24.04 (ARM)
#
# Run as root:  sudo bash install.sh
# =============================================================================
set -euo pipefail

APP_USER="brewery"
APP_DIR="/opt/brewery-sim"
SERVICE_FILE="/etc/systemd/system/brewery-sim.service"
API_PORT=8000

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()    { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

[[ $EUID -ne 0 ]] && error "Run as root: sudo bash install.sh"
[[ "$(uname -m)" != "aarch64" ]] && warn "Not aarch64 — continuing anyway"

# ── 1. System deps ────────────────────────────────────────────────────────────
info "Installing system dependencies..."
if command -v apt-get &>/dev/null; then
    apt-get update -qq
    apt-get install -y -qq python3 python3-pip curl git
elif command -v dnf &>/dev/null; then
    dnf install -y -q python3 python3-pip curl git
else
    error "Unsupported package manager (expected apt or dnf)"
fi

# ── 2. Install uv (universal Python package manager) ──────────────────────────
info "Installing uv..."
if ! command -v uv &>/dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Make uv available system-wide
    cp ~/.local/bin/uv /usr/local/bin/uv 2>/dev/null || true
fi
uv --version

# ── 3. Create dedicated user ──────────────────────────────────────────────────
info "Creating system user '${APP_USER}'..."
if ! id "${APP_USER}" &>/dev/null; then
    useradd --system --create-home --shell /bin/bash "${APP_USER}"
fi

# ── 4. Deploy application ─────────────────────────────────────────────────────
info "Deploying to ${APP_DIR}..."
mkdir -p "${APP_DIR}"

# Copy project files (assumes install.sh is run from the project directory)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp -r "${SCRIPT_DIR}/." "${APP_DIR}/"
chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}"

# Install uv for the brewery user too
su -c 'curl -LsSf https://astral.sh/uv/install.sh | sh' "${APP_USER}" 2>/dev/null || true

# Install Python dependencies via uv
info "Installing Python dependencies..."
su -c "cd ${APP_DIR} && ~/.local/bin/uv sync" "${APP_USER}"

# ── 5. Open firewall port for API ─────────────────────────────────────────────
info "Opening firewall port ${API_PORT}/tcp for control API..."
if command -v firewall-cmd &>/dev/null; then
    # Oracle Linux / RHEL (firewalld)
    firewall-cmd --permanent --add-port="${API_PORT}/tcp" &>/dev/null || true
    firewall-cmd --reload &>/dev/null || true
    info "firewalld: port ${API_PORT} opened"
elif command -v ufw &>/dev/null; then
    # Ubuntu (ufw)
    ufw allow "${API_PORT}/tcp" &>/dev/null || true
    info "ufw: port ${API_PORT} opened"
else
    warn "No firewall manager found — open port ${API_PORT} manually if needed"
fi

# Oracle Cloud also has Security Lists / NSG — you must open port ${API_PORT}
# in the OCI console under: Networking → VCN → Security Lists → Ingress Rules

# ── 6. Install and enable systemd service ─────────────────────────────────────
info "Installing systemd service..."
cat > "${SERVICE_FILE}" << UNIT
[Unit]
Description=Industrial Brewery PLC/SCADA Simulator
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${APP_DIR}
ExecStart=/home/${APP_USER}/.local/bin/uv run brewery-sim --speed 60
ExecReload=/bin/kill -HUP \$MAINPID
Restart=always
RestartSec=10
StartLimitIntervalSec=120
StartLimitBurst=5
Environment=PYTHONUNBUFFERED=1
StandardOutput=journal
StandardError=journal
SyslogIdentifier=brewery-sim
MemoryMax=512M
CPUQuota=50%
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=${APP_DIR}

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable brewery-sim
systemctl start brewery-sim

# ── 7. Verify ─────────────────────────────────────────────────────────────────
sleep 3
if systemctl is-active --quiet brewery-sim; then
    info "✓ brewery-sim service is running"
else
    warn "Service may not have started yet — check: journalctl -u brewery-sim -f"
fi

# ── 8. Summary ────────────────────────────────────────────────────────────────
PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || echo "<your-server-ip>")
echo ""
echo -e "${GREEN}════════════════════════════════════════════${NC}"
echo -e "${GREEN} Brewery Simulator installed successfully!  ${NC}"
echo -e "${GREEN}════════════════════════════════════════════${NC}"
echo ""
echo "  Control API (Swagger):  http://${PUBLIC_IP}:${API_PORT}/docs"
echo "  MQTT topic root:        brewery/#"
echo ""
echo "  Useful commands:"
echo "    systemctl status brewery-sim      # check status"
echo "    systemctl restart brewery-sim     # restart"
echo "    journalctl -u brewery-sim -f      # live logs"
echo "    systemctl stop brewery-sim        # stop"
echo ""
echo "  Change speed live (no restart needed):"
echo "    curl -X POST http://localhost:${API_PORT}/speed/3600"
echo ""
echo -e "${YELLOW}  ⚠  Remember to open port ${API_PORT} in OCI Security Lists!${NC}"
echo "     OCI Console → Networking → VCN → Security Lists → Add Ingress Rule"
echo "     Source CIDR: 0.0.0.0/0  |  Protocol: TCP  |  Port: ${API_PORT}"
echo ""
