#!/usr/bin/env bash
# Pasang perintah 'bot' supaya bisa diketik dari mana saja (sekali saja).
# Sesudah ini:  bot jalan | bot berhenti | bot restart | bot log | bot status
# Atau ketik 'bot' saja untuk menu.
set -e
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$HOME/bin"
cat > "$HOME/bin/bot" <<EOF
#!/usr/bin/env bash
exec "$REPO_DIR/ctl.sh" "\$@"
EOF
chmod +x "$HOME/bin/bot"
if [[ ":$PATH:" != *":$HOME/bin:"* ]] && ! grep -qs 'HOME/bin' "$HOME/.bashrc" 2>/dev/null; then
  printf '\nexport PATH="$HOME/bin:$PATH"\n' >> "$HOME/.bashrc"
  echo "PATH diperbarui di .bashrc."
fi
echo "Selesai. Tutup Termux lalu buka lagi, atau jalankan: source ~/.bashrc"
echo "Sesudah itu ketik: bot"
