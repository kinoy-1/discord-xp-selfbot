#!/usr/bin/env bash
# Setup awal: isi token Discord dan API key AI ke .env (sekali saja).
# Ketikan disembunyikan di layar dan tidak tersimpan di riwayat perintah.
# Kalau .env sudah ada, tekan Enter saja pada pertanyaan untuk memakai
# nilai lama.
set -e
cd "$(dirname "$0")" || exit 1

[ -f .env.example ] || { echo ".env.example tidak ketemu."; exit 1; }

baca_lama() {
  grep "^$1=" .env 2>/dev/null | cut -d= -f2- | head -n 1
}

echo "Setup bot — isi token Discord dan API key AI."
echo "(Tekan Enter saja untuk memakai nilai yang sudah ada.)"
printf "Token Discord: "
read -rs TOKEN_BARU; echo
printf "API key OpenRouter (boleh kosong bila tidak pakai AI): "
read -rs KEY_BARU; echo

TOKEN_LAMA="$(baca_lama DISCORD_TOKEN)"
KEY_LAMA="$(baca_lama AI_API_KEY)"
TOKEN="${TOKEN_BARU:-$TOKEN_LAMA}"
KEY="${KEY_BARU:-$KEY_LAMA}"

if [ -z "$TOKEN" ]; then
  echo "Token Discord wajib diisi — setup dibatalkan, .env tidak diubah."
  exit 1
fi

tmp="$(mktemp)"
if [ -f .env ]; then
  grep -v '^DISCORD_TOKEN=' .env 2>/dev/null | grep -v '^AI_API_KEY=' > "$tmp" || true
else
  grep -v '^DISCORD_TOKEN=' .env.example | grep -v '^AI_API_KEY=' > "$tmp" || true
fi
printf 'DISCORD_TOKEN=%s\nAI_API_KEY=%s\n' "$TOKEN" "$KEY" >> "$tmp"
mv "$tmp" .env
chmod 600 .env
echo "Selesai — .env sudah terisi."
if [ -z "$KEY" ]; then
  echo "Catatan: tanpa API key, balasan AI tidak jalan (XP tetap jalan)."
fi
echo "Lanjut: python menu.py (isi channel target, pilihan 1), lalu: bot jalan"
