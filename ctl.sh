#!/usr/bin/env bash
# Perintah gampang buat bot — tidak perlu hafal nohup/pkill/tail lagi.
# Dipakai dari folder repo:  ./ctl.sh jalan | berhenti | restart | log | status
# Dipasang sekali:          ./pasang.sh   -> lalu ketik 'bot' dari mana saja.
cd "$(dirname "$0")" || exit 1

tampil_menu() {
  echo "Bot Discord XP — pilih:"
  echo "  1. Jalankan bot"
  echo "  2. Berhenti"
  echo "  3. Lihat log"
  echo "  4. Cek status"
  echo "  5. Restart"
  echo "  0. Keluar"
  printf "Pilih [0-5]: "
  read -r pilihan || exit 0
  case "$pilihan" in
    1) jalankan ;;
    2) hentikan ;;
    3) lihat_log ;;
    4) cek_status ;;
    5) mulai_ulang ;;
    0|"") exit 0 ;;
    *) echo "Pilihan tidak dikenal."; exit 1 ;;
  esac
}

jalankan() {
  termux-wake-lock 2>/dev/null || true
  rm -f STOP
  nohup .venv/bin/python bot.py > selfbot.log 2>&1 &
  echo "Bot jalan (PID $!)."
}

hentikan() {
  if pkill -f '(^|/)python[0-9.]* bot\.py$' 2>/dev/null; then
    echo "Bot berhenti."
  else
    echo "Bot sudah tidak jalan."
  fi
}

mulai_ulang() {
  pkill -f '(^|/)python[0-9.]* bot\.py$' 2>/dev/null || true
  sleep 2
  rm -f STOP
  termux-wake-lock 2>/dev/null || true
  nohup .venv/bin/python bot.py > selfbot.log 2>&1 &
  echo "Bot di-restart (PID $!)."
}

lihat_log() {
  tail -f selfbot.log
}

cek_status() {
  if pgrep -f '(^|/)python[0-9.]* bot\.py$' >/dev/null 2>&1; then
    pgrep -af '(^|/)python[0-9.]* bot\.py$'
    echo "--- log terakhir ---"
    tail -3 selfbot.log
  else
    echo "Bot tidak jalan."
  fi
}

case "${1:-}" in
  jalan|start) jalankan ;;
  berhenti|stop) hentikan ;;
  restart|mulai-ulang) mulai_ulang ;;
  log) lihat_log ;;
  status) cek_status ;;
  bantuan|help|-h|--help)
    echo "Pakai: bot jalan | berhenti | restart | log | status"
    echo "Atau ketik 'bot' saja untuk menu."
    ;;
  "") tampil_menu ;;
  *)
    echo "Perintah tidak dikenal: $1"
    echo "Pakai: bot jalan | berhenti | restart | log | status"
    exit 1
    ;;
esac
