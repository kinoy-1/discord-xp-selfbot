"""Discord XP self-bot.

Logs in with a Discord *user* token, sends human-like chat messages on a
random schedule to farm XP in other people's servers, and answers messages
that reply to us or mention us with AI-generated replies (OpenRouter).

WARNING: self-bots violate Discord's Terms of Service. The account can be
banned. This tool reduces the risk (random delays, active hours, daily cap,
random breaks, dry-run mode) but cannot remove it. Never share your token.

Usage:
    cp .env.example .env   # then fill in DISCORD_TOKEN + OPENROUTER_API_KEY
    python menu.py         # edit settings (targets, intervals, persona, ...)
    python bot.py          # start the bot (dry-run first!)

Create an empty file named STOP in this directory to stop the bot cleanly.
"""
from __future__ import annotations

import asyncio
import logging
import os
import random
import signal
import sys
import time
from collections import deque
from datetime import date, datetime

import discord
from dotenv import load_dotenv

from ai_reply import detect_language, generate_reply, generate_xp_message
from config import CONFIG_PATH, active_now, load_config, validate_config
from messages import MessageBank

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("selfbot.log", encoding="utf-8"),
    ],
)
log = logging.getLogger("xp-selfbot")

STOP_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "STOP")
REACTION_EMOJIS = ["👍", "😂", "🔥", "❤️", "👀", "🙌", "😮", "👏"]
# A channel that fails this many times in a row is skipped for
# CHANNEL_BLOCK_SECONDS (it may have been deleted or the account kicked);
# a later success clears the count.
CHANNEL_FAIL_LIMIT = 3
CHANNEL_BLOCK_SECONDS = 3600


# ---------------------------------------------------------------------------
# Pure helpers (unit-tested without a Discord connection)
# ---------------------------------------------------------------------------

def is_reply_to_us(message, self_id: int, self_name: str) -> bool:
    """True when a message replies to us, mentions us, or says our name."""
    author = getattr(message, "author", None)
    if author is not None and getattr(author, "bot", False):
        return False
    ref = getattr(message, "reference", None)
    if ref is not None:
        resolved = getattr(ref, "resolved", None)
        if resolved is not None and getattr(resolved, "author", None) is not None:
            if getattr(resolved.author, "id", None) == self_id:
                return True
        # Unresolved reference: the caller may resolve it; fall through to
        # the mention/name checks below.
    mentions = getattr(message, "mentions", []) or []
    for user in mentions:
        if getattr(user, "id", None) == self_id:
            return True
    content = getattr(message, "content", "") or ""
    if self_name and self_name.lower() in content.lower():
        return True
    return False


def should_reply(cfg: dict, rng: random.Random, last_reply_at: float | None,
                 now: float) -> bool:
    """Decide whether to answer a reply/mention right now."""
    if not cfg.get("reply_enabled", True):
        return False
    if rng.random() > float(cfg.get("reply_chance", 0.75)):
        return False  # humans don't answer everything
    cooldown = float(cfg.get("reply_cooldown_seconds", 120))
    if last_reply_at is not None and (now - last_reply_at) < cooldown:
        return False
    return True


def typing_delay(text: str, rng: random.Random) -> float:
    """Seconds a person would take to type this reply (min 1s, max 12s)."""
    return max(1.0, min(12.0, len(text) / 14.0 + rng.uniform(0.5, 2.0)))


def daily_summary_line(day, sent: int, replies: int, rate_limits: int,
                       level_ups: int) -> str:
    """One-line daily summary for the log."""
    return (f"Daily summary {day}: {sent} messages sent, {replies} replies, "
            f"{rate_limits} rate limits, {level_ups} level-ups detected.")


def retry_after_seconds(exc, default: float = 60.0) -> float | None:
    """Seconds Discord asks us to wait after a 429, or None if not a 429.

    Reads the ``Retry-After`` response header; falls back to ``default``
    when the header is missing or unparsable (it can be an HTTP date).
    """
    if getattr(exc, "status", None) != 429:
        return None
    headers = getattr(getattr(exc, "response", None), "headers", None) or {}
    raw = headers.get("Retry-After") if hasattr(headers, "get") else None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return default
    return max(1.0, value)


def choose_next_action(cfg: dict, state: dict, rng: random.Random,
                       now: datetime) -> tuple[str, object]:
    """Decide the XP loop's next step. Returns (action, payload).

    Actions: "idle" (seconds to wait), "break" (seconds to rest),
    "send" (target dict), "react" (target dict).
    """
    if not active_now(cfg, now):
        return ("idle", 60.0)
    cap = int(cfg.get("daily_message_cap", 0))
    if cap > 0 and state.get("sent_today", 0) >= cap:
        return ("idle", 300.0)
    if rng.random() < float(cfg.get("break_chance", 0.08)):
        seconds = rng.uniform(
            float(cfg.get("break_min", 600)), float(cfg.get("break_max", 1800))
        )
        return ("break", seconds)
    blocked = state.get("blocked_channels", set())
    targets = [t for t in cfg.get("targets", [])
               if t.get("channel_id") not in cfg.get("avoid_channels", [])
               and t.get("channel_id") not in blocked]
    if not targets:
        return ("idle", 60.0)
    target = rng.choice(targets)
    if rng.random() < float(cfg.get("react_chance", 0.15)):
        return ("react", target)
    return ("send", target)


# ---------------------------------------------------------------------------
# Bot
# ---------------------------------------------------------------------------

class SelfBot(discord.Client):
    def __init__(self, cfg: dict):
        # discord.py-self has no Intents system: a user account receives
        # every event it can see. Plain Client() is the correct setup.
        super().__init__()
        self.cfg = cfg
        self.rng = random.Random()
        self.banks = {
            "id": MessageBank("id", rng=self.rng),
            "en": MessageBank("en", rng=self.rng),
        }
        self.sent_today = 0
        self.sent_date = date.today()
        self.replies_today = 0
        self.rate_limits_today = 0
        self.level_ups_today = 0
        self.last_reply_at: dict[int, float] = {}
        self.history: dict[int, deque] = {}
        # Monotonic timestamp until which all sends pause (set on 429).
        self.rate_limited_until: float = 0.0
        # Consecutive per-channel failures, and channels skipped until a
        # monotonic timestamp (dead-channel block).
        self.channel_failures: dict[int, int] = {}
        self.channel_blocked_until: dict[int, float] = {}
        self._xp_task: asyncio.Task | None = None

    # -- lifecycle ---------------------------------------------------------
    async def on_ready(self):
        log.info("Logged in as %s (%s)", self.user, self.user.id)
        log.info("Dry run: %s | targets: %s",
                 self.cfg.get("dry_run"),
                 [t.get("channel_id") for t in self.cfg.get("targets", [])])
        if self._xp_task is None:
            self._xp_task = asyncio.create_task(self.xp_loop())

    async def close(self):
        if self._xp_task is not None:
            self._xp_task.cancel()
        await super().close()

    def stop_requested(self) -> bool:
        return os.path.exists(STOP_FILE)

    # -- rate limiting -----------------------------------------------------
    def _note_rate_limit(self, exc) -> None:
        """Pause all sends after a Discord 429 (uses Retry-After + buffer)."""
        wait = retry_after_seconds(exc)
        if wait is None:
            return
        self.rate_limits_today += 1
        pause = wait + 5.0
        self.rate_limited_until = time.monotonic() + pause
        log.warning("Rate limited (429) by Discord, pausing sends for %.0f seconds.",
                    pause)

    def _rate_limited(self) -> bool:
        return time.monotonic() < self.rate_limited_until

    # -- dead channels -----------------------------------------------------
    def _blocked_channel_ids(self) -> set[int]:
        now = time.monotonic()
        return {cid for cid, until in self.channel_blocked_until.items()
                if until > now}

    def _channel_blocked(self, channel_id: int) -> bool:
        return channel_id in self._blocked_channel_ids()

    def _note_channel_failure(self, channel_id: int) -> None:
        """Count a failed send/fetch; block the channel after N in a row.

        A 429 is NOT a channel failure (Discord is limiting us, the channel
        is fine) -- callers must skip this for 429s.
        """
        count = self.channel_failures.get(channel_id, 0) + 1
        self.channel_failures[channel_id] = count
        if count >= CHANNEL_FAIL_LIMIT:
            self.channel_blocked_until[channel_id] = (
                time.monotonic() + CHANNEL_BLOCK_SECONDS)
            self.channel_failures[channel_id] = 0
            log.warning("Channel %s failed %d times, skipping it for %d seconds.",
                        channel_id, CHANNEL_FAIL_LIMIT, CHANNEL_BLOCK_SECONDS)

    def _note_channel_success(self, channel_id: int) -> None:
        self.channel_failures.pop(channel_id, None)
        self.channel_blocked_until.pop(channel_id, None)

    # -- helpers -----------------------------------------------------------
    def _reset_daily_counter(self):
        today = date.today()
        if today != self.sent_date:
            if (self.sent_today or self.replies_today
                    or self.rate_limits_today or self.level_ups_today):
                log.info(daily_summary_line(
                    self.sent_date, self.sent_today, self.replies_today,
                    self.rate_limits_today, self.level_ups_today))
            self.sent_date = today
            self.sent_today = 0
            self.replies_today = 0
            self.rate_limits_today = 0
            self.level_ups_today = 0

    def _record_history(self, channel_id: int, role: str, content: str):
        queue = self.history.setdefault(channel_id, deque(maxlen=8))
        queue.append({"role": role, "content": content})

    async def get_or_fetch_channel(self, channel_id: int):
        channel = self.get_channel(channel_id)
        if channel is None:
            try:
                channel = await self.fetch_channel(channel_id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException) as exc:
                self._note_rate_limit(exc)
                if retry_after_seconds(exc) is None:
                    self._note_channel_failure(channel_id)
                log.warning("Cannot access channel %s: %s", channel_id, exc)
                return None
        return channel

    async def _send(self, channel, text: str) -> bool:
        """Send a message (or log it in dry-run mode). Returns True if sent."""
        self._reset_daily_counter()
        cap = int(self.cfg.get("daily_message_cap", 0))
        if cap > 0 and self.sent_today >= cap:
            log.info("Daily cap reached (%d), not sending.", cap)
            return False
        if self.cfg.get("dry_run"):
            log.info("[DRY-RUN] #%s: %s", getattr(channel, "name", channel.id), text)
            return True
        try:
            if self.cfg.get("typing_enabled"):
                async with channel.typing():
                    await asyncio.sleep(typing_delay(text, self.rng))
            await channel.send(text)
        except discord.HTTPException as exc:
            self._note_rate_limit(exc)
            if retry_after_seconds(exc) is None:
                self._note_channel_failure(channel.id)
            log.warning("Cannot send to #%s: %s",
                        getattr(channel, "name", channel.id), exc)
            return False
        self.sent_today += 1
        self._note_channel_success(channel.id)
        log.info("Sent to #%s: %s", getattr(channel, "name", channel.id), text)
        return True

    async def _pick_xp_text(self, target: dict) -> str:
        """Pick the next XP message: AI-generated when enabled, else the bank.

        AI failure falls back to the bank, so a dead API never stops XP.
        """
        bank = self.banks[target.get("language", "id")]
        if not self.cfg.get("ai_xp_messages"):
            return bank.pick()
        api_key = os.environ.get("AI_API_KEY") or os.environ.get(
            "OPENROUTER_API_KEY", ""
        )
        text = generate_xp_message(
            api_key=api_key,
            model=self.cfg.get("ai_model", ""),
            base_url=self.cfg.get("ai_base_url", "https://openrouter.ai/api/v1"),
            language=target.get("language", "id"),
            persona=self.cfg.get("persona", ""),
        )
        if text:
            return text
        log.warning("AI XP message failed, falling back to the message bank.")
        return bank.pick()

    # -- XP farming loop ---------------------------------------------------
    async def xp_loop(self):
        await self.wait_until_ready()
        state = {"sent_today": 0}
        while not self.is_closed():
            if self.stop_requested():
                log.info("STOP file found, shutting down.")
                await self.close()
                return
            self._reset_daily_counter()
            if self._rate_limited():
                remaining = self.rate_limited_until - time.monotonic()
                log.info("Rate limited, waiting %.0f more seconds.", remaining)
                await asyncio.sleep(min(remaining, 30.0))
                continue
            state["sent_today"] = self.sent_today
            state["blocked_channels"] = self._blocked_channel_ids()
            action, payload = choose_next_action(
                self.cfg, state, self.rng, datetime.now()
            )
            if action == "idle":
                await asyncio.sleep(float(payload))
                continue
            if action == "break":
                log.info("Taking a break for %.0f seconds.", float(payload))
                await asyncio.sleep(float(payload))
                continue
            target = payload
            channel = await self.get_or_fetch_channel(int(target["channel_id"]))
            if channel is None:
                await asyncio.sleep(60)
                continue
            if action == "react":
                await self._maybe_react(channel)
            else:
                await self._send(channel, await self._pick_xp_text(target))
            wait = self.rng.uniform(
                float(self.cfg.get("xp_interval_min", 90)),
                float(self.cfg.get("xp_interval_max", 240)),
            )
            await asyncio.sleep(wait)

    async def _maybe_react(self, channel):
        try:
            messages = [m async for m in channel.history(limit=5)]
        except (discord.Forbidden, discord.HTTPException) as exc:
            self._note_rate_limit(exc)
            if retry_after_seconds(exc) is None:
                self._note_channel_failure(channel.id)
            log.warning("Cannot read history in #%s: %s",
                        getattr(channel, "name", channel.id), exc)
            return
        if not messages:
            return
        target = self.rng.choice(messages)
        if getattr(target.author, "id", None) == (self.user.id if self.user else -1):
            return
        emoji = self.rng.choice(REACTION_EMOJIS)
        if self.cfg.get("dry_run"):
            log.info("[DRY-RUN] React %s to message %s", emoji, target.id)
            return
        try:
            await target.add_reaction(emoji)
        except (discord.Forbidden, discord.HTTPException) as exc:
            self._note_rate_limit(exc)
            if retry_after_seconds(exc) is None:
                self._note_channel_failure(channel.id)
            log.warning("Cannot react: %s", exc)

    # -- incoming messages ---------------------------------------------------
    async def on_message(self, message: discord.Message):
        if self.user is not None and message.author.id == self.user.id:
            return
        if getattr(message.author, "bot", False):
            self._check_level_up(message)
            return
        channel_id = message.channel.id
        self._record_history(channel_id, "user", message.content or "")
        is_dm = isinstance(message.channel, discord.DMChannel)
        if is_dm and not self.cfg.get("dm_reply"):
            return
        if not is_reply_to_us(message, self.user.id, self.user.name):
            # Try resolving an uncached reply reference before giving up.
            ref = getattr(message, "reference", None)
            if ref is not None and getattr(ref, "resolved", None) is None:
                try:
                    resolved = await message.channel.fetch_message(ref.message_id)
                    if getattr(resolved.author, "id", None) == self.user.id:
                        await self._answer(message)
                except (discord.NotFound, discord.Forbidden, discord.HTTPException) as exc:
                    self._note_rate_limit(exc)
                    pass
            return
        await self._answer(message)

    def _check_level_up(self, message: discord.Message):
        content = (message.content or "").lower()
        if "level" not in content:
            return
        if self.user is None:
            return
        if str(self.user.id) in content or self.user.name.lower() in content:
            self.level_ups_today += 1
            log.info("LEVEL UP detected: %s", message.content)

    async def _answer(self, message: discord.Message):
        now = time.time()
        channel_id = message.channel.id
        if not should_reply(self.cfg, self.rng, self.last_reply_at.get(channel_id), now):
            return
        api_key = os.environ.get("AI_API_KEY") or os.environ.get(
            "OPENROUTER_API_KEY", ""
        )
        history = list(self.history.get(channel_id, []))
        lang = detect_language(message.content or "")
        reply = generate_reply(
            api_key=api_key,
            model=self.cfg.get("ai_model", ""),
            base_url=self.cfg.get("ai_base_url", "https://openrouter.ai/api/v1"),
            persona=self.cfg.get("persona", ""),
            history=history,
            user_message=message.content or "",
            max_tokens=int(self.cfg.get("ai_max_tokens", 120)),
            timeout=int(self.cfg.get("ai_timeout", 30)),
        )
        if reply is None:
            log.warning("AI reply failed, staying silent (reason logged above).")
            return
        log.info("Replying in %s to %s: %s", lang, message.author, reply)
        self.last_reply_at[channel_id] = now
        if self.cfg.get("dry_run"):
            log.info("[DRY-RUN] Reply to %s: %s", message.author, reply)
            return
        try:
            async with message.channel.typing():
                await asyncio.sleep(typing_delay(reply, self.rng))
            sent = await message.reply(reply)
            self._record_history(channel_id, "assistant", reply)
            self.sent_today += 1
            self.replies_today += 1
            log.info("Replied (msg %s).", sent.id)
        except (discord.Forbidden, discord.HTTPException) as exc:
            self._note_rate_limit(exc)
            log.warning("Cannot reply: %s", exc)

    async def on_error(self, event, *args, **kwargs):
        log.exception("Error in event %s", event)


def main() -> int:
    cfg = load_config()
    problems = validate_config(cfg)
    if problems:
        for problem in problems:
            log.error("Config problem: %s", problem)
        log.error("Fix config.json (or run: python menu.py).")
        return 2
    token = os.environ.get("DISCORD_TOKEN", "")
    if not token:
        log.error("DISCORD_TOKEN is not set. Copy .env.example to .env and fill it in.")
        return 2
    if cfg.get("dry_run"):
        log.info("Dry-run mode is ON: nothing will be sent. Turn it off in menu.py when ready.")
    bot = SelfBot(cfg)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, lambda: asyncio.create_task(bot.close()))
        except (NotImplementedError, RuntimeError):
            pass
    try:
        loop.run_until_complete(bot.start(token))
    except discord.LoginFailure:
        log.error("Login gagal: token Discord tidak valid atau akun terkunci.")
        return 3
    except discord.HTTPException as exc:
        log.error("Discord HTTP error saat login: %s", exc)
        return 3
    except KeyboardInterrupt:
        log.info("Interrupted, shutting down.")
    finally:
        try:
            loop.run_until_complete(bot.close())
        except Exception:
            pass
        loop.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
