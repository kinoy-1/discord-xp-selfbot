#!/bin/bash
# Update the self-bot code from GitHub and restart the bot.
# Works on the VPS (systemd service) and on Termux (nohup bot).
# Run from this repo directory:  ./update.sh
#
# This only updates CODE files from origin/main. Your local settings are
# never touched: config.json and .env are not in the checkout list, so a
# local config edited with menu.py survives every update.
set -e
cd "$(dirname "$0")"
if [ ! -d .git ]; then
  echo "ERROR: this is not a git checkout. Clone the repo first:"
  echo "  git clone https://github.com/kinoy-1/discord-xp-selfbot.git"
  exit 1
fi
git fetch origin
git checkout origin/main -- bot.py config.py messages.py ai_reply.py menu.py \
  run.sh update.sh ctl.sh pasang.sh setup.sh requirements.txt tests \
  discord-xp-selfbot.service README.md .env.example .gitignore
chmod +x run.sh update.sh ctl.sh pasang.sh setup.sh 2>/dev/null || true
echo "Code updated from origin/main."
if systemctl is-active --quiet discord-xp-selfbot 2>/dev/null; then
  sudo systemctl restart discord-xp-selfbot
  echo "Service restarted."
elif pgrep -f '(^|/)python[0-9.]* bot\.py$' >/dev/null 2>&1; then
  ./ctl.sh restart
else
  echo "Bot tidak jalan. Jalankan dengan:"
  echo "  bot jalan"
fi
