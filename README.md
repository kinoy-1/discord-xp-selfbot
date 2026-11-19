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

## Panduan lengkap (dari nol)

1. **Clone repo ini:**
   ```bash
   git clone https://github.com/kinoy-1/discord-xp-selfbot.git
   cd discord-xp-selfbot
   ```
2. **Pasang Python + dependensi:**
   ```bash
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   ```
   (Termux: `pkg install python`, lalu `pip install -r requirements.txt`.)
3. **Isi token dan key AI:**
   ```bash
   ./setup.sh
   ```
   Jawab dua pertanyaan (ketikan disembunyikan). Token Discord didapat
   dari browser (lihat bawah) atau lewat curl (HP, lihat bawah); key AI
   dari https://openrouter.ai/keys (gratis, model `:free` biaya 0).
4. **Isi channel target:** `python menu.py` > pilihan 1, isi
   `channel_id,bahasa` — contoh `1530597622245621921,id`. ID channel
   didapat dari Discord: Settings > Advanced > nyalakan Developer Mode,
   lalu klik kanan channel > Copy Channel ID.
5. **Pasang perintah gampang (sekali saja):**
   ```bash
   ./pasang.sh
   source ~/.bashrc   # atau tutup lalu buka lagi Termux-nya
   ```
6. **Jalankan bot:**
   ```bash
   bot jalan
   ```
   Bot jalan pertama kali dalam mode dry-run (hanya mencatat, tidak
   mengirim). Periksa `bot log`, kalau sudah yakin matikan dry-run dari
   menu (`python menu.py` > pilihan 8).

Perintah sehari-hari: `bot jalan | berhenti | restart | log | status`,
atau ketik `bot` saja untuk menu bernomor.

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

Kalau cara di atas tidak jalan (misal di browser HP, Local Storage-nya
kosong), ambil token lewat login API dari Termux:

```bash
curl -s -X POST https://discord.com/api/v9/auth/login \
  -H "Content-Type: application/json" \
  -d '{"login":"EMAIL_KAMU","password":"PASSWORD_KAMU"}'
```

Jawabannya berisi `"token": "..."` — salin nilainya ke `.env`. Ketik
email/password langsung di Termux saja, jangan pernah kirim lewat chat.

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

Perintah gampang (tidak perlu hafal nohup/pkill/tail). Pasang sekali saja:

```bash
./pasang.sh
source ~/.bashrc   # atau tutup lalu buka lagi Termux-nya
```

Sesudah itu, dari folder mana saja:

```bash
bot jalan      # jalankan bot
bot berhenti   # hentikan bot
bot restart    # berhenti lalu jalan lagi
bot log        # lihat log live (Ctrl+C untuk keluar, bot tetap jalan)
bot status     # cek bot jalan atau tidak + 3 baris log terakhir
```

Atau ketik `bot` saja untuk menu bernomor. Perintah Inggris lama
(`start`, `stop`) tetap jalan. Tanpa dipasang, perintah yang sama
tetap bisa dipakai dari folder repo sebagai `./ctl.sh jalan`, dst.

### VPS (disarankan, Ubuntu)

```bash
sudo apt update && sudo apt install -y python3-venv
# clone repo ini, lalu ikuti instalasi di atas
# jalankan sebagai service agar hidup terus dan restart otomatis:
sudo cp discord-xp-selfbot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now discord-xp-selfbot
```

Service memakai `Restart=always`, jadi bot hidup lagi sendiri kalau prosesnya
mati atau VPS reboot. Cek status dan log:

```bash
sudo systemctl status discord-xp-selfbot
journalctl -u discord-xp-selfbot -f
```

Kalau kamu clone repo di tempat lain atau pakai user lain, ubah `User=` dan
path di `discord-xp-selfbot.service` sebelum install. Untuk berhenti darurat,
buat file `STOP` di folder repo (`touch STOP`) atau `sudo systemctl stop
discord-xp-selfbot`.

**Kalau kena rate-limit (429):** bot membaca header `Retry-After` dari
Discord, berhenti kirim selama waktu itu (+5 detik buffer), lalu lanjut
sendiri. Tidak ada pesan yang dipaksa terkirim saat sedang di-limit.

**Ringkasan harian:** tiap ganti hari bot menulis satu baris ke log:

```
Daily summary 2026-11-18: 187 messages sent, 23 replies, 1 rate limits, 2 level-ups detected.
```

Cek cepat dengan `grep "Daily summary" selfbot.log`. Kalau ada baris itu,
bot hidup dan bekerja; kalau tidak ada, bot mati atau tidak ada aktivitas.

**Channel mati:** channel yang gagal kirim/ambil 3 kali berturut-turut
di-skip selama 1 jam (misal channel dihapus atau akun di-kick dari server).
Satu kiriman yang berhasil menghapus hitungan gagalnya. Rate-limit (429)
tidak dihitung sebagai kegagalan channel.

### Update dari GitHub

```bash
./update.sh
```

Menarik kode terbaru dari GitHub lalu restart bot (service di VPS, proses
nohup di Termux). Hanya file kode yang diperbarui; `config.json` dan `.env`
tidak pernah disentuh, jadi pengaturan lokalmu aman.

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
| `bot.py` | Bot utama (login, XP loop, auto-reply, penanganan 429) |
| `config.py` | Load/validasi `config.json` |
| `config.json` | Semua pengaturan (tanpa rahasia) |
| `messages.py` | Bank pesan XP (80 ID + 72 EN) |
| `ai_reply.py` | Klien OpenRouter + deteksi bahasa |
| `menu.py` | Menu pengaturan interaktif |
| `setup.sh` | Setup awal: isi token + key AI ke `.env` |
| `pasang.sh` | Pasang perintah `bot` ke `~/bin` (sekali saja) |
| `ctl.sh` | Perintah `bot` (jalan/berhenti/restart/log/status + menu) |
| `run.sh` | Script jalan |
| `update.sh` | Tarik kode terbaru dari GitHub + restart service |
| `discord-xp-selfbot.service` | Service systemd (auto-start + auto-restart) |
| `tests/` | Unit test + tes live AI |

### Pesan XP dari AI (opsional)

Secara default pesan XP diambil dari bank pesan (`messages.py`, 80 ID + 72
EN, tidak pernah mengulang dari 10 pesan terakhir). Kalau mau variasinya
tidak terbatas, nyalakan `ai_xp_messages` di `config.json` (atau menu pilihan
12): tiap pesan XP digenerate AI dari persona kamu. Gagal API apa pun
langsung jatuh kembali ke bank pesan, jadi XP tidak pernah berhenti.
