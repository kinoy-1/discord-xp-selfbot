"""AI replies through OpenRouter (or any OpenAI-compatible endpoint).

The reply is generated in the same language as the message being answered,
following the persona from the config. On any failure (no key, timeout, API
error) this returns None -- the caller then stays silent instead of sending
a broken reply.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

API_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "inclusionai/ling-3.2-flash:free"

# Indonesian markers used for a fast language guess. The system prompt also
# tells the model to match the user's language, so this is a backup signal.
_ID_MARKERS = [
    " yang ", " aku ", " kamu ", " gak ", " nggak ", " sih ", " dong ",
    " lagi ", " udah ", " belum ", " banget ", " aja ", " yuk ", " wkwk",
    " bro", " gan ", " mas ", " kak ", " gua ", " gue ", " lu ", " lo ",
    " kenapa ", " gimana ", " kapan ", " dimana ", " siapa ", " tolong",
    " makasih ", " terima kasih", " selamat ", " pagi ", " malam ",
    " jangan ", " boleh ", " bisa ", " mau ", " ayo ", " sini ",
]


def detect_language(text: str) -> str:
    """Guess 'id' or 'en' from a short chat message."""
    lowered = f" {text.lower()} "
    hits = sum(1 for marker in _ID_MARKERS if marker in lowered)
    return "id" if hits >= 1 else "en"


def build_messages(persona: str, history: list[dict], user_message: str) -> list[dict]:
    """Build the chat-completion message list for the reply."""
    messages = [{"role": "system", "content": persona}]
    for item in history[-8:]:
        messages.append({"role": item["role"], "content": item["content"]})
    messages.append({"role": "user", "content": user_message})
    return messages


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):  # noqa: D102
        raise RuntimeError("redirect refused, verify the endpoint")


def generate_reply(
    *,
    api_key: str,
    model: str = DEFAULT_MODEL,
    persona: str,
    history: list[dict] | None = None,
    user_message: str,
    max_tokens: int = 120,
    timeout: int = 30,
) -> str | None:
    """Ask the model for a reply. Returns the reply text, or None on failure."""
    if not api_key:
        return None
    payload = {
        "model": model,
        "messages": build_messages(persona, history or [], user_message),
        "max_tokens": max_tokens,
        "temperature": 0.9,
    }
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
    )
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("HTTP-Referer", "https://github.com/kinoy-1/discord-xp-selfbot")
    req.add_header("X-Title", "discord-xp-selfbot")
    try:
        opener = urllib.request.build_opener(_NoRedirect())
        with opener.open(req, timeout=timeout) as resp:
            data = json.load(resp)
    except (urllib.error.HTTPError, urllib.error.URLError, RuntimeError,
            TimeoutError, OSError, ValueError, KeyError):
        return None
    try:
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return None
    if not isinstance(text, str):
        return None
    text = text.strip()
    return text or None
