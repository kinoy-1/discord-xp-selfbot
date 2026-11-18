"""Interactive settings menu for the Discord XP self-bot.

Run:  python menu.py

Shows the current settings, lets you change them one by one, and saves to
config.json. Secrets are never handled here -- they live in .env.
"""
from __future__ import annotations

import sys

from config import CONFIG_PATH, load_config, save_config, validate_config


def _ask_int(prompt: str, current: int, input_fn=input, print_fn=print) -> int:
    raw = input_fn(f"{prompt} [{current}]: ").strip()
    if raw == "":
        return current
    try:
        return int(raw)
    except ValueError:
        print_fn("Bukan angka, nilai tidak diubah.")
        return current


def _ask_float(prompt: str, current: float, input_fn=input, print_fn=print) -> float:
    raw = input_fn(f"{prompt} [{current}]: ").strip()
    if raw == "":
        return current
    try:
        return float(raw)
    except ValueError:
        print_fn("Bukan angka, nilai tidak diubah.")
        return current


def _ask_text(prompt: str, current: str, input_fn=input, print_fn=print) -> str:
    raw = input_fn(f"{prompt} [{current}]: ").strip()
    return raw if raw else current


def _ask_yes_no(prompt: str, current: bool, input_fn=input, print_fn=print) -> bool:
    raw = input_fn(f"{prompt} (y/n) [{'y' if current else 'n'}]: ").strip().lower()
    if raw == "":
        return current
    if raw in ("y", "yes", "ya"):
        return True
    if raw in ("n", "no", "tidak"):
        return False
    print_fn("Jawaban tidak dikenal, nilai tidak diubah.")
    return current


def _edit_targets(cfg: dict, input_fn=input, print_fn=print) -> None:
    print_fn("\nTarget saat ini:")
    for i, t in enumerate(cfg["targets"], 1):
        print_fn(f"  {i}. guild={t.get('guild_id')} channel={t.get('channel_id')} lang={t.get('language')}")
    print_fn("Masukkan target baru sebagai: channel_id,language  (contoh: 123456789012345678,id)")
    print_fn("Kosongkan untuk selesai. Ketik 'hapus' untuk menghapus semua target.")
    new_targets = []
    while True:
        raw = input_fn("target> ").strip()
        if raw == "":
            break
        if raw.lower() == "hapus":
            new_targets = []
            break
        parts = [p.strip() for p in raw.split(",")]
        try:
            channel_id = int(parts[0])
            language = parts[1] if len(parts) > 1 else "id"
        except (ValueError, IndexError):
            print_fn("Format salah, contoh: 123456789012345678,id")
            continue
        if language not in ("id", "en"):
            print_fn("Bahasa harus 'id' atau 'en'.")
            continue
        new_targets.append({"guild_id": 0, "channel_id": channel_id, "language": language})
    if new_targets:
        cfg["targets"] = new_targets
        print_fn(f"{len(new_targets)} target disimpan.")


def show_summary(cfg: dict, print_fn=print) -> None:
    print_fn("\n===== Pengaturan Self-Bot =====")
    print_fn(f"1. Target XP        : {len(cfg['targets'])} channel")
    for t in cfg["targets"]:
        print_fn(f"     - channel {t.get('channel_id')} ({t.get('language')})")
    print_fn(f"2. Interval pesan   : {cfg['xp_interval_min']}-{cfg['xp_interval_max']} detik")
    print_fn(f"3. Jam aktif        : {cfg['active_hours']['start']:02d}:00-{cfg['active_hours']['end']:02d}:00")
    print_fn(f"4. Batas/hari       : {cfg['daily_message_cap']} pesan (0 = tanpa batas)")
    print_fn(f"5. Istirahat acak   : {cfg['break_chance']*100:.0f}% tiap ronde, {cfg['break_min']}-{cfg['break_max']} dtk")
    print_fn(f"6. Auto-reply       : {'ON' if cfg['reply_enabled'] else 'OFF'}, peluang {cfg['reply_chance']*100:.0f}%, cooldown {cfg['reply_cooldown_seconds']} dtk")
    print_fn(f"7. Model AI         : {cfg['ai_model']}")
    print_fn(f"   Base URL AI      : {cfg['ai_base_url']}")
    print_fn(f"8. Dry-run          : {'ON (tidak kirim apa-apa)' if cfg['dry_run'] else 'OFF (KIRIM BENARAN)'}")
    print_fn(f"9. Balas DM         : {'ON' if cfg['dm_reply'] else 'OFF'}")
    print_fn(f"10. Reaksi emoji    : {cfg['react_chance']*100:.0f}%")
    print_fn(f"11. Persona         : {cfg['persona'][:80]}...")
    print_fn("0. Simpan & keluar")
    print_fn("===============================")


def edit_loop(cfg: dict, input_fn=input, print_fn=print) -> dict:
    """Run the menu until the user quits. Returns the (possibly) edited config."""
    while True:
        show_summary(cfg, print_fn)
        choice = input_fn("Pilih nomor> ").strip()
        if choice == "0":
            return cfg
        elif choice == "1":
            _edit_targets(cfg, input_fn, print_fn)
        elif choice == "2":
            cfg["xp_interval_min"] = _ask_int("Interval minimum (detik)", cfg["xp_interval_min"], input_fn, print_fn)
            cfg["xp_interval_max"] = _ask_int("Interval maksimum (detik)", cfg["xp_interval_max"], input_fn, print_fn)
        elif choice == "3":
            cfg["active_hours"]["start"] = _ask_int("Jam mulai aktif (0-23)", cfg["active_hours"]["start"], input_fn, print_fn)
            cfg["active_hours"]["end"] = _ask_int("Jam berhenti aktif (0-23)", cfg["active_hours"]["end"], input_fn, print_fn)
        elif choice == "4":
            cfg["daily_message_cap"] = _ask_int("Batas pesan per hari (0 = tanpa batas)", cfg["daily_message_cap"], input_fn, print_fn)
        elif choice == "5":
            pct = _ask_float("Peluang istirahat per ronde (0-1)", cfg["break_chance"], input_fn, print_fn)
            cfg["break_chance"] = max(0.0, min(1.0, pct))
            cfg["break_min"] = _ask_int("Istirahat minimum (detik)", cfg["break_min"], input_fn, print_fn)
            cfg["break_max"] = _ask_int("Istirahat maksimum (detik)", cfg["break_max"], input_fn, print_fn)
        elif choice == "6":
            cfg["reply_enabled"] = _ask_yes_no("Auto-reply aktif?", cfg["reply_enabled"], input_fn, print_fn)
            pct = _ask_float("Peluang membalas (0-1)", cfg["reply_chance"], input_fn, print_fn)
            cfg["reply_chance"] = max(0.0, min(1.0, pct))
            cfg["reply_cooldown_seconds"] = _ask_int("Cooldown balasan (detik)", cfg["reply_cooldown_seconds"], input_fn, print_fn)
        elif choice == "7":
            cfg["ai_base_url"] = _ask_text("Base URL AI", cfg["ai_base_url"], input_fn, print_fn)
            cfg["ai_model"] = _ask_text("Model AI", cfg["ai_model"], input_fn, print_fn)
        elif choice == "8":
            cfg["dry_run"] = _ask_yes_no("Dry-run (tidak kirim apa-apa)?", cfg["dry_run"], input_fn, print_fn)
        elif choice == "9":
            cfg["dm_reply"] = _ask_yes_no("Balas DM juga?", cfg["dm_reply"], input_fn, print_fn)
        elif choice == "10":
            pct = _ask_float("Peluang reaksi emoji (0-1)", cfg["react_chance"], input_fn, print_fn)
            cfg["react_chance"] = max(0.0, min(1.0, pct))
        elif choice == "11":
            print_fn("Persona saat ini:")
            print_fn(cfg["persona"])
            new = input_fn("Persona baru (kosongkan bila tidak diubah): ").strip()
            if new:
                cfg["persona"] = new
        else:
            print_fn("Pilihan tidak dikenal.")
        problems = validate_config(cfg)
        if problems:
            print_fn("PERINGATAN konfigurasi belum valid:")
            for problem in problems:
                print_fn(f"  - {problem}")


def main() -> int:
    cfg = load_config()
    cfg = edit_loop(cfg)
    save_config(cfg)
    problems = validate_config(cfg)
    if problems:
        print("Disimpan ke", CONFIG_PATH, "tapi masih ada masalah:")
        for problem in problems:
            print(" -", problem)
        return 1
    print("Tersimpan di", CONFIG_PATH, "-- konfigurasi valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
