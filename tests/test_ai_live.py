"""Live test: one real AI reply through OpenRouter.

Run manually from the project root:
    .venv/bin/python tests/test_ai_live.py

Uses the registered OpenRouter connection via its credential surrogate, so
the real API key is never printed or stored. The reply must be a non-empty
string in the same language as the prompt. This test is NOT run by the
automatic test suite (it needs network + the stored credential).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, "/opt/muse/skills/custom-connector-setup/bin")

from dynamic_credentials import dynamic_credential_entry

from ai_reply import generate_reply

PERSONA = (
    "Kamu Kinoy, cowok Indonesia yang santai dan ramah di Discord. "
    "Balas dengan singkat (1-3 kalimat), gaya obrolan biasa. "
    "Jawab SELALU dalam bahasa yang sama dengan pesan yang kamu balas."
)


def main() -> int:
    entry = dynamic_credential_entry("custom.openrouter")
    api_key = entry["surrogate"]  # hsurr:... -- swapped for the real key in transit
    assert api_key.startswith("hsurr:"), "expected a surrogate, got something else"
    reply = generate_reply(
        api_key=api_key,
        model="inclusionai/ling-3.2-flash:free",
        persona=PERSONA,
        history=[{"role": "user", "content": "lagi pada ngapain guys"}],
        user_message="wkwk rame banget hari ini, kamu lagi apa?",
        max_tokens=120,
        timeout=60,
    )
    print("REPLY:", reply)
    if not reply or not isinstance(reply, str):
        print("LIVE AI TEST: FAILED (empty reply)")
        return 1
    print("LIVE AI TEST: PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
