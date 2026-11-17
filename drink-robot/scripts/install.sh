#!/usr/bin/env bash
# Run ON THE RASPBERRY PI from inside the drink-robot folder:  bash scripts/install.sh
set -euo pipefail
cd "$(dirname "$0")/.."
DIR="$(pwd)"
USER_NAME="$(whoami)"

sudo apt-get update
sudo apt-get install -y python3-venv python3-gpiozero python3-lgpio avahi-daemon

python3 -m venv --system-site-packages .venv
.venv/bin/pip install -r requirements.txt

sed -e "s#/home/pi/drink-robot#${DIR}#g" -e "s#^User=pi#User=${USER_NAME}#" \
    scripts/drinkbot.service | sudo tee /etc/systemd/system/drinkbot.service >/dev/null
sudo systemctl daemon-reload
sudo systemctl enable --now drinkbot

echo
echo "DrinkBot is running. Open:  http://$(hostname).local:8080   (bartender: /bar)"
echo "Logs:  journalctl -u drinkbot -f"
