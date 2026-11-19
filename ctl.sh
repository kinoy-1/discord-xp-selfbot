#!/usr/bin/env bash
# Perintah gampang buat bot — tidak perlu hafal nohup/pkill/tail lagi.
# Pakai: ./ctl.sh start | stop | restart | log | status
cd "$(dirname "$0")" || exit 1

case "${1:-}" in
  start)
    termux-wake-lock 2>/dev/null || true
    rm -f STOP
    nohup .venv/bin/python bot.py > selfbot.log 2>&1 &
    echo "Bot jalan (PID $!)."
    ;;
  stop)
    if pkill -f bot.py 2>/dev/null; then
      echo "Bot berhenti."
    else
      echo "Bot sudah tidak jalan."
    fi
    ;;
  restart)
    pkill -f bot.py 2>/dev/null || true
    sleep 2
    rm -f STOP
    termux-wake-lock 2>/dev/null || true
    nohup .venv/bin/python bot.py > selfbot.log 2>&1 &
    echo "Bot di-restart (PID $!)."
    ;;
  log)
    tail -f selfbot.log
    ;;
  status)
    if pgrep -f bot.py >/dev/null 2>&1; then
      pgrep -af bot.py
      echo "--- log terakhir ---"
      tail -3 selfbot.log
    else
      echo "Bot tidak jalan."
    fi
    ;;
  *)
    echo "Pakai: ./ctl.sh start | stop | restart | log | status"
    ;;
esac
