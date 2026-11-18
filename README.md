# Discord XP Self-Bot

Self-bot Discord yang push XP di server orang lain sambil bertingkah seperti
manusia biasa: kirim pesan berkala dari bank variasi, istirahat acak, jam
aktif seperti manusia, dan membalas reply/mention dengan balasan AI
(OpenRouter) dalam bahasa yang sama dengan lawan bicara.

> **Peringatan:** self-bot melanggar Terms of Service Discord. Akun yang
> ketahuan memakai self-bot bisa kena ban permanen. Tool ini mengurangi risiko
> (jeda acak, batas harian, dry-run, tombol darurat) tapi tidak bisa
> menghilangkannya. Pakai dengan sadar, dan jangan pernah membagikan tokenmu.

## Cara kerja

- **XP farming:** kirim pesan acak dari bank pesan (Indonesia/Inggris) ke
  channel target tiap 90–240 detik (acak), di dalam jam aktif. Kebanyakan bot
  XP (MEE6, Arcane) hanya kasih XP sekali per ~60 detik cooldown, jadi
  interval ini sudah cukup.
- **Istirahat acak:** tiap ronde ada peluang 8% bot diam 10–30 menit, seperti
  orang yang lagi tidak buka Discord.
- **Auto-reply:** kalau ada yang reply pesanmu atau mention kamu, bot balas
  pakai AI (OpenRouter). Balasan singkat, santai, dan dalam bahasa yang sama
  dengan lawan bicara. Bot tidak membalas semuanya (peluang 75%) supaya
  terlihat natural.
- **Anti-ketahuan:** kalau ada yang menuduh kamu bot, AI diperintah menyangkal
  dengan santai. Bot tidak pernah mengaku sebagai bot atau AI.
- **Dry-run:** mode default. Bot hanya mencatat apa yang *akan* dikirim,
  tanpa mengirim apa-apa. Matikan dry-run kalau sudah yakin.
- **Tombol darurat:** buat file kosong bernama `STOP` di folder ini, bot
  berhenti dengan rapi. Rate limit Discord (429) juga membuat bot jeda
  otomatis.

## Instalasi

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env   # lalu isi DISCORD_TOKEN dan OPENROUTER_API_KEY
```

## Pengaturan

```bash
python menu.py     # menu interaktif: target, interval, jam aktif, dsb.
```

Atau edit `config.json` langsung. Token dan API key **hanya** di `.env`,
tidak pernah di `config.json` dan tidak pernah di chat.

### Mendapatkan token Discord (akun sendiri)

Buka Discord di browser (bukan aplikasi) > tekan F12 > tab Application >
Local Storage > `https://discord.com` > cari `token`. Salin nilainya ke
`.env`. Kalau token bocor, reset lewat Settings > Authorized Apps atau ganti
password Discord.

### Mendapatkan API key OpenRouter

Daftar di https://openrouter.ai/keys. Model default
`inclusionai/ling-3.2-flash:free` gratis (biaya 0).

### Pakai AI selain OpenRouter

Bisa. Bot ini memakai endpoint yang kompatibel dengan OpenAI
(`/chat/completions`), jadi provider lain tinggal diganti lewat `config.json`
(`ai_base_url` + `ai_model`) dan key-nya di `.env` sebagai `AI_API_KEY`:

| Provider | `ai_base_url` | Contoh `ai_model` | Status (dites 18 Nov 2026) |
|---|---|---|---|
| OpenRouter (default) | `https://openrouter.ai/api/v1` | `inclusionai/ling-3.2-flash:free` | Jalan |
| Verboo | `https://code.verboo.ai/router/v1` | `deepseek-v4.1-flash` | Jalan |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` | Seharusnya jalan (belum dites) |
| XingchiAPI | `https://xingchiapi.com/v1` | `gpt-6-astra` | **Diblokir provider** (403 `client_not_allowed`: hanya untuk coding client, script langsung ditolak) |

Atau ubah lewat menu: `python menu.py` > pilihan 7. Provider yang tidak
mendukung format chat-completions OpenAI tidak akan jalan.

## Menjalankan

```bash
./run.sh           # atau: python bot.py
```

Jalankan pertama kali dalam mode dry-run, periksa `selfbot.log`, baru
matikan dry-run dari menu.

### VPS (disarankan, Ubuntu)

```bash
sudo apt update && sudo apt install -y python3-venv
# clone repo ini, lalu ikuti instalasi di atas
# jalankan sebagai service agar hidup terus:
cat > /etc/systemd/system/discord-xp-selfbot.service <<'EOF'
[Unit]
Description=Discord XP self-bot
After=network-online.target
[Service]
WorkingDirectory=/home/ubuntu/discord-xp-selfbot
ExecStart=/home/ubuntu/discord-xp-selfbot/.venv/bin/python bot.py
Restart=on-failure
RestartSec=30
[Install]
WantedBy=multi-user.target
EOF
sudo systemctl enable --now discord-xp-selfbot
```

### Termux (HP Android)

Bisa, tapi bot mati kalau HP mati, kehabisan baterai, atau Android mematikan
Termux di background. Matikan optimasi baterai untuk Termux dan biarkan HP
menyala. VPS lebih stabil untuk jalan 24/7.

```bash
pkg install python
pip install -r requirements.txt
python bot.py
```

## Tes

```bash
.venv/bin/python -m unittest discover -s tests -v
```

Tes mencakup config, bank pesan, deteksi bahasa, AI reply (mock), logika
balasan, dan simulasi menu. Tes live AI (`tests/test_ai_live.py`) memakai
kunci OpenRouter sendiri dan tidak dijalankan otomatis.

## File

| File | Fungsi |
|---|---|
| `bot.py` | Bot utama (login, XP loop, auto-reply) |
| `config.py` | Load/validasi `config.json` |
| `config.json` | Semua pengaturan (tanpa rahasia) |
| `messages.py` | Bank pesan XP (ID + EN) |
| `ai_reply.py` | Klien OpenRouter + deteksi bahasa |
| `menu.py` | Menu pengaturan interaktif |
| `run.sh` | Script jalan |
| `tests/` | Unit test + tes live AI |
