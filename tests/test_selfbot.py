"""Unit tests for the Discord XP self-bot.

Run from the project root with the project venv:
    .venv/bin/python -m unittest discover -s tests -v

No network access is needed except test_ai_live.py (separate file, run
manually). Discord objects are faked with SimpleNamespace.
"""
import asyncio
import inspect
import io
import json
import os
import random
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import discord

from ai_reply import build_messages, detect_language, generate_reply
from bot import (
    SelfBot,
    choose_next_action,
    is_reply_to_us,
    should_reply,
    typing_delay,
)
from config import active_now, load_config, save_config, validate_config
from menu import edit_loop
from messages import MessageBank


def _msg(author_id=111, author_bot=False, content="hello", mentions=None,
         reference=None):
    return SimpleNamespace(
        author=SimpleNamespace(id=author_id, bot=author_bot),
        content=content,
        mentions=mentions or [],
        reference=reference,
    )


class TestConfig(unittest.TestCase):
    def test_defaults_load_when_file_missing(self):
        cfg = load_config("/nonexistent/config.json")
        self.assertEqual(cfg["xp_interval_min"], 90)
        self.assertTrue(cfg["dry_run"])
        self.assertEqual(cfg["ai_model"], "inclusionai/ling-3.2-flash:free")

    def test_save_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "config.json")
            cfg = load_config(path)
            cfg["xp_interval_min"] = 123
            cfg["targets"] = [{"guild_id": 1, "channel_id": 999, "language": "en"}]
            save_config(cfg, path)
            reloaded = load_config(path)
            self.assertEqual(reloaded["xp_interval_min"], 123)
            self.assertEqual(reloaded["targets"][0]["channel_id"], 999)
            # Unset keys fall back to defaults.
            self.assertEqual(reloaded["reply_chance"], 0.75)

    def test_validate_ok(self):
        cfg = load_config("/nonexistent/config.json")
        cfg["targets"] = [{"guild_id": 1, "channel_id": 999, "language": "id"}]
        self.assertEqual(validate_config(cfg), [])

    def test_validate_catches_problems(self):
        cfg = load_config("/nonexistent/config.json")
        cfg["targets"] = [{"guild_id": 1, "channel_id": 0, "language": "xx"}]
        cfg["xp_interval_min"] = 500
        cfg["xp_interval_max"] = 10
        problems = validate_config(cfg)
        self.assertTrue(any("channel_id" in p for p in problems))
        self.assertTrue(any("language" in p for p in problems))
        self.assertTrue(any("xp_interval" in p for p in problems))

    def test_active_now(self):
        from datetime import datetime
        cfg = {"active_hours": {"start": 8, "end": 23}}
        self.assertTrue(active_now(cfg, datetime(2026, 11, 18, 12, 0)))
        self.assertFalse(active_now(cfg, datetime(2026, 11, 18, 2, 0)))
        self.assertFalse(active_now(cfg, datetime(2026, 11, 18, 23, 0)))
        overnight = {"active_hours": {"start": 20, "end": 2}}
        self.assertTrue(active_now(overnight, datetime(2026, 11, 18, 22, 0)))
        self.assertTrue(active_now(overnight, datetime(2026, 11, 18, 1, 0)))
        self.assertFalse(active_now(overnight, datetime(2026, 11, 18, 12, 0)))


class TestMessageBank(unittest.TestCase):
    def test_no_repeat_within_history(self):
        bank = MessageBank("id", history=10, rng=random.Random(42))
        seen = [bank.pick() for _ in range(10)]
        self.assertEqual(len(set(seen)), 10)

    def test_both_languages_have_messages(self):
        for lang in ("id", "en"):
            bank = MessageBank(lang, rng=random.Random(1))
            self.assertTrue(len(bank.pick()) > 0)

    def test_unknown_language_rejected(self):
        with self.assertRaises(ValueError):
            MessageBank("xx")


class TestAiReply(unittest.TestCase):
    def test_detect_language(self):
        self.assertEqual(detect_language("wkwk gila sih ini"), "id")
        self.assertEqual(detect_language("lagi pada ngapain guys"), "id")
        self.assertEqual(detect_language("that's so cool, let's go"), "en")
        self.assertEqual(detect_language("hello world"), "en")

    def test_build_messages_keeps_persona_first(self):
        msgs = build_messages("PERSONA", [{"role": "user", "content": "hi"}],
                              "hello there")
        self.assertEqual(msgs[0], {"role": "system", "content": "PERSONA"})
        self.assertEqual(msgs[-1], {"role": "user", "content": "hello there"})

    def _fake_urlopen(self, payload):
        class FakeResp:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return json.dumps(payload).encode()

        return FakeResp()

    def test_generate_reply_success(self):
        payload = {"choices": [{"message": {"content": "  hai juga wkwk  "}}]}
        with patch("ai_reply.urllib.request.build_opener") as opener_mock:
            opener_mock.return_value.open.return_value = self._fake_urlopen(payload)
            text = generate_reply(api_key="test-key", persona="P",
                                  user_message="hai")
        self.assertEqual(text, "hai juga wkwk")

    def test_generate_reply_http_error_returns_none(self):
        import urllib.error
        with patch("ai_reply.urllib.request.build_opener") as opener_mock:
            opener_mock.return_value.open.side_effect = urllib.error.HTTPError(
                "https://x", 429, "too many", {}, None)
            text = generate_reply(api_key="test-key", persona="P",
                                  user_message="hai")
        self.assertIsNone(text)

    def test_generate_reply_malformed_returns_none(self):
        with patch("ai_reply.urllib.request.build_opener") as opener_mock:
            opener_mock.return_value.open.return_value = self._fake_urlopen({})
            text = generate_reply(api_key="test-key", persona="P",
                                  user_message="hai")
        self.assertIsNone(text)

    def test_generate_reply_no_key_returns_none(self):
        self.assertIsNone(generate_reply(api_key="", persona="P",
                                         user_message="hai"))

    def test_generate_reply_custom_base_url(self):
        payload = {"choices": [{"message": {"content": "ok"}}]}
        captured = {}

        class FakeOpener:
            def open(self, req, timeout=None):
                captured["url"] = req.full_url
                return self._resp

        fake = FakeOpener()
        fake._resp = self._fake_urlopen(payload)
        with patch("ai_reply.urllib.request.build_opener", return_value=fake):
            text = generate_reply(
                api_key="k", persona="P", user_message="hai",
                base_url="https://xingchiapi.com/v1/",
            )
        self.assertEqual(text, "ok")
        self.assertEqual(captured["url"],
                         "https://xingchiapi.com/v1/chat/completions")


class TestReplyLogic(unittest.TestCase):
    def test_is_reply_to_us_reference(self):
        ref = SimpleNamespace(
            resolved=SimpleNamespace(author=SimpleNamespace(id=999)))
        self.assertTrue(is_reply_to_us(_msg(reference=ref), 999, "kinoy"))

    def test_is_reply_to_us_mention(self):
        mentions = [SimpleNamespace(id=999)]
        self.assertTrue(is_reply_to_us(_msg(mentions=mentions), 999, "kinoy"))

    def test_is_reply_to_us_name(self):
        self.assertTrue(is_reply_to_us(_msg(content="kinoy lagi apa"), 999, "kinoy"))

    def test_is_reply_to_us_no_match(self):
        self.assertFalse(is_reply_to_us(_msg(content="hello all"), 999, "kinoy"))

    def test_is_reply_to_us_ignores_bots(self):
        ref = SimpleNamespace(
            resolved=SimpleNamespace(author=SimpleNamespace(id=999)))
        self.assertFalse(is_reply_to_us(_msg(author_bot=True, reference=ref),
                                        999, "kinoy"))

    def test_should_reply(self):
        cfg = {"reply_enabled": True, "reply_chance": 1.0,
               "reply_cooldown_seconds": 120}
        rng = random.Random(0)
        self.assertTrue(should_reply(cfg, rng, None, 1000.0))
        self.assertFalse(should_reply(cfg, rng, 950.0, 1000.0))  # cooldown
        self.assertTrue(should_reply(cfg, rng, 800.0, 1000.0))   # cooldown over
        cfg["reply_enabled"] = False
        self.assertFalse(should_reply(cfg, rng, None, 1000.0))
        cfg["reply_enabled"] = True
        cfg["reply_chance"] = 0.0
        self.assertFalse(should_reply(cfg, rng, None, 1000.0))

    def test_typing_delay_bounds(self):
        rng = random.Random(0)
        for text in ("hi", "x" * 500):
            delay = typing_delay(text, rng)
            self.assertGreaterEqual(delay, 1.0)
            self.assertLessEqual(delay, 12.0)


class TestChooseNextAction(unittest.TestCase):
    def _cfg(self, **over):
        cfg = load_config("/nonexistent/config.json")
        cfg["targets"] = [{"guild_id": 1, "channel_id": 999, "language": "id"}]
        cfg.update(over)
        return cfg

    def test_outside_active_hours_idles(self):
        from datetime import datetime
        cfg = self._cfg()
        action, _ = choose_next_action(cfg, {"sent_today": 0}, random.Random(0),
                                       datetime(2026, 11, 18, 3, 0))
        self.assertEqual(action, "idle")

    def test_daily_cap_idles(self):
        from datetime import datetime
        cfg = self._cfg(daily_message_cap=5)
        action, _ = choose_next_action(cfg, {"sent_today": 5}, random.Random(0),
                                       datetime(2026, 11, 18, 12, 0))
        self.assertEqual(action, "idle")

    def test_forced_break(self):
        from datetime import datetime
        cfg = self._cfg(break_chance=1.0)
        action, secs = choose_next_action(cfg, {"sent_today": 0}, random.Random(0),
                                          datetime(2026, 11, 18, 12, 0))
        self.assertEqual(action, "break")
        self.assertGreaterEqual(secs, 600)

    def test_forced_react(self):
        from datetime import datetime
        cfg = self._cfg(break_chance=0.0, react_chance=1.0)
        action, target = choose_next_action(cfg, {"sent_today": 0}, random.Random(0),
                                            datetime(2026, 11, 18, 12, 0))
        self.assertEqual(action, "react")
        self.assertEqual(target["channel_id"], 999)

    def test_default_is_send(self):
        from datetime import datetime
        cfg = self._cfg(break_chance=0.0, react_chance=0.0)
        action, target = choose_next_action(cfg, {"sent_today": 0}, random.Random(0),
                                            datetime(2026, 11, 18, 12, 0))
        self.assertEqual(action, "send")
        self.assertEqual(target["channel_id"], 999)


class TestSelfBotDryRun(unittest.TestCase):
    def _bot(self):
        cfg = load_config("/nonexistent/config.json")
        cfg["targets"] = [{"guild_id": 1, "channel_id": 999, "language": "id"}]
        return SelfBot(cfg)

    def test_user_token_login_path(self):
        # discord.py-self logs in with a plain user token: login(token)
        # takes only the token (no bot flag, no Intents system).
        login_params = inspect.signature(discord.Client.login).parameters
        self.assertIn("token", login_params)
        self.assertFalse(hasattr(discord, "Intents"))
        # The client must construct with no arguments.
        bot = self._bot()
        self.assertIsNotNone(bot)

    def test_send_dry_run_does_not_call_discord(self):
        bot = self._bot()
        channel = SimpleNamespace(id=999, name="general", send=AsyncMock())
        result = asyncio.run(bot._send(channel, "hello"))
        self.assertTrue(result)
        channel.send.assert_not_called()
        self.assertEqual(bot.sent_today, 0)

    def test_send_real_calls_discord_and_counts(self):
        bot = self._bot()
        bot.cfg["dry_run"] = False
        bot.cfg["typing_enabled"] = False
        channel = SimpleNamespace(id=999, name="general", send=AsyncMock())
        result = asyncio.run(bot._send(channel, "hello"))
        self.assertTrue(result)
        channel.send.assert_called_once_with("hello")
        self.assertEqual(bot.sent_today, 1)

    def test_send_respects_daily_cap(self):
        bot = self._bot()
        bot.cfg["dry_run"] = False
        bot.cfg["typing_enabled"] = False
        bot.cfg["daily_message_cap"] = 1
        bot.sent_today = 1
        channel = SimpleNamespace(id=999, name="general", send=AsyncMock())
        result = asyncio.run(bot._send(channel, "hello"))
        self.assertFalse(result)
        channel.send.assert_not_called()


class TestMenu(unittest.TestCase):
    def test_edit_interval_and_quit(self):
        cfg = load_config("/nonexistent/config.json")
        inputs = iter(["2", "100", "300", "0"])
        out = io.StringIO()
        result = edit_loop(cfg, input_fn=lambda _: next(inputs),
                           print_fn=lambda *a, **k: print(*a, file=out, **k))
        self.assertEqual(result["xp_interval_min"], 100)
        self.assertEqual(result["xp_interval_max"], 300)

    def test_menu_rejects_bad_choice(self):
        cfg = load_config("/nonexistent/config.json")
        inputs = iter(["99", "0"])
        out = io.StringIO()
        result = edit_loop(cfg, input_fn=lambda _: next(inputs),
                           print_fn=lambda *a, **k: print(*a, file=out, **k))
        self.assertIn("tidak dikenal", out.getvalue())
        self.assertEqual(result["xp_interval_min"], 90)


if __name__ == "__main__":
    unittest.main()
