"""AI replies through OpenRouter (or any OpenAI-compatible endpoint).

The reply is generated in the same language as the message being answered,
following the persona from the config. On any failure (no key, timeout, API
error) this returns None -- the caller then stays silent instead of sending
a broken reply. Every failure is logged with its concrete reason (missing
key, HTTP status + provider message, timeout, or empty content), so the
log tells you what went wrong instead of just "AI failed".
"""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

log = logging.getLogger("xp-selfbot.ai")

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
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


def _call_chat(
    *,
    api_key: str,
    model: str,
    base_url: str,
    messages: list[dict],
    max_tokens: int,
    temperature: float,
    timeout: int,
) -> str | None:
    """One chat-completions call. Returns the reply text, None on failure.

    Every failure is logged with its concrete reason, so a failed reply
    tells you what went wrong (no key, HTTP status, timeout, empty
    content) instead of failing silently.
    """
    if not api_key:
        log.warning("AI call skipped: no API key set (AI_API_KEY in .env).")
        return None
    url = base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    req = urllib.request.Request(
        url,
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
    except urllib.error.HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8", "replace")[:200]
        except Exception:
            detail = ""
        log.warning("AI call failed: HTTP %s from %s: %s",
                    exc.code, base_url, detail or exc.msg)
        return None
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        log.warning("AI call failed: network/timeout (%s).", exc)
        return None
    except (RuntimeError, ValueError, KeyError) as exc:
        log.warning("AI call failed: %s.", exc)
        return None
    try:
        choice = data["choices"][0]
        text = choice["message"]["content"]
    except (KeyError, IndexError, TypeError):
        log.warning("AI call failed: unexpected response shape from %s.",
                    base_url)
        return None
    if not isinstance(text, str) or not text.strip():
        reason = choice.get("finish_reason") if isinstance(choice, dict) else None
        log.warning(
            "AI returned no text (model=%s, finish_reason=%s). A reasoning "
            "model may have spent its token budget thinking; try a "
            "non-reasoning model or raise ai_max_tokens.",
            model, reason)
        return None
    return text.strip()


def generate_reply(
    *,
    api_key: str,
    model: str = DEFAULT_MODEL,
    base_url: str = DEFAULT_BASE_URL,
    persona: str,
    history: list[dict] | None = None,
    user_message: str,
    max_tokens: int = 120,
    timeout: int = 30,
) -> str | None:
    """Ask the model for a reply. Returns the reply text, or None on failure.

    Any provider with an OpenAI-compatible ``/chat/completions`` endpoint
    works: pass its base URL (without a trailing slash) and its key.
    """
    return _call_chat(
        api_key=api_key,
        model=model,
        base_url=base_url,
        messages=build_messages(persona, history or [], user_message),
        max_tokens=max_tokens,
        temperature=0.9,
        timeout=timeout,
    )


def generate_xp_message(
    *,
    api_key: str,
    model: str = DEFAULT_MODEL,
    base_url: str = DEFAULT_BASE_URL,
    language: str = "id",
    persona: str = "",
    max_tokens: int = 60,
    timeout: int = 30,
) -> str | None:
    """Generate one short, casual chat message for XP farming.

    Returns None on any failure -- the caller falls back to the message
    bank. The result is a single line, never a greeting with a name.
    """
    lang = "Bahasa Indonesia santai" if language == "id" else "casual English"
    system = (
        (persona + " " if persona else "")
        + f"Tulis SATU pesan chat Discord singkat (satu kalimat, maksimal 15 kata) "
        f"yang natural untuk grup, dalam {lang}. Boleh sapaan umum, reaksi, "
        f"atau pertanyaan ringan. Jangan sebut nama orang. Jangan mengaku bot."
    )
    text = _call_chat(
        api_key=api_key,
        model=model,
        base_url=base_url,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": "Tulis satu pesan chat santai."},
        ],
        max_tokens=max_tokens,
        temperature=1.0,
        timeout=timeout,
    )
    if text is None:
        return None
    # Keep it to one line; drop any accidental multi-line output.
    first = text.splitlines()[0].strip().strip('"')
    return first or None
