#!/bin/bash
# Start the self-bot. Run from this directory.
# First time:  python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
set -e
cd "$(dirname "$0")"
if [ ! -f .env ]; then
  echo "ERROR: .env not found. Copy .env.example to .env and fill it in."
  exit 1
fi
if [ -f .venv/bin/python ]; then
  .venv/bin/python bot.py
else
  python3 bot.py
fi
