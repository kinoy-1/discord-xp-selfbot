"""Varied chat messages for XP farming.

The bot picks at random and never repeats one of the last N messages, so the
channel never sees the same line twice in a row. Keep the lines generic and
human: greetings, reactions, small talk, questions. Nothing spammy, nothing
that looks copy-pasted.
"""
from __future__ import annotations

import random
from collections import deque

XP_MESSAGES_ID = [
    "pagi semua, ada yang udah ngopi belum wkwk",
    "anjir rame banget hari ini",
    "lagi pada ngapain guys",
    "wah infonya menarik tuh",
    "setuju sih sama yang di atas",
    "baru bangun, ketinggalan info apa aja nih",
    "ada yang main nanti malem gak",
    "cuaca hari ini panas banget ya",
    "wkwk ngakak liat ini",
    "btw ada yang tau update terbarunya?",
    "lagi gabut banget, ada rekomendasi tontonan gak",
    "akhirnya kelar juga kerjaan hari ini",
    "siapa yang masih begadang jam segini",
    "info dong, eventnya sampai kapan",
    "gila sih ini keren banget",
    "baru coba, ternyata seru juga ya",
    "ada yang mau mabar nanti?",
    "lagi nungguin update nih, penasaran",
    "wih selamat buat yang udah naik level",
    "hari ini capek banget, butuh rebahan",
    "btw kalian tim pagi atau tim malem",
    "ada yang punya tips biar cepet naik level",
    "lagi dengerin lagu enak banget nih",
    "kok sepi ya, pada kemana semua",
    "baru selesai makan, lanjut lagi",
    "ada yang nonton match tadi malem gak",
    "seru juga ya obrolan di sini",
    "lagi nyari temen ngobrol, ada yang online?",
    "wah udah jam segini aja",
    "info harganya dong kalau ada yang tau",
    "baru join, salam kenal semua",
    "ada yang bisa bantu jawab pertanyaan gue gak",
    "hari ini vibesnya enak banget",
    "lagi mikir mau ngapain abis ini",
    "siapa di sini yang dari jakarta",
    "wkwk ini lucu banget sih",
    "lagi nungguin temen, lama banget",
    "ada rekomendasi game santai gak",
    "baru liat pengumumannya, menarik tuh",
    "udah pada makan siang belum",
]

XP_MESSAGES_EN = [
    "morning everyone, anyone had coffee yet lol",
    "wow it's really active in here today",
    "what's everyone up to",
    "that's actually interesting info",
    "yeah I agree with the message above",
    "just woke up, what did I miss",
    "anyone playing later tonight?",
    "it's so hot today huh",
    "lol this is hilarious",
    "btw does anyone know the latest update?",
    "so bored right now, any show recommendations?",
    "finally done with work for today",
    "who else is still up at this hour",
    "how long does the event last?",
    "that's actually insane, so cool",
    "just tried it, turns out it's pretty fun",
    "anyone up for a game later?",
    "waiting for the update, curious how it goes",
    "grats to everyone who just leveled up",
    "today was exhausting, I need to lie down",
    "btw are you a morning person or night person",
    "any tips for leveling up faster?",
    "listening to such a good song right now",
    "why is it so quiet, where is everyone",
    "just finished eating, back again",
    "did anyone watch the match last night?",
    "the chat here is pretty fun",
    "looking for someone to talk to, anyone online?",
    "wow it's already this late",
    "does anyone know the price?",
    "just joined, nice to meet you all",
    "can someone help me with a question?",
    "the vibes today are really nice",
    "thinking about what to do next",
    "anyone here into casual games?",
    "lol that's so funny",
]

MESSAGES = {"id": XP_MESSAGES_ID, "en": XP_MESSAGES_EN}


class MessageBank:
    """Picks a random XP message, avoiding recent repeats."""

    def __init__(self, language: str = "id", history: int = 10,
                 rng: random.Random | None = None):
        if language not in MESSAGES:
            raise ValueError(f"unknown language: {language!r}")
        self.language = language
        self.pool = list(MESSAGES[language])
        if len(self.pool) < 5:
            raise ValueError("message pool too small")
        self.recent: deque[str] = deque(maxlen=history)
        self.rng = rng or random.Random()

    def pick(self) -> str:
        """Return a random message that was not used recently."""
        candidates = [m for m in self.pool if m not in self.recent]
        if not candidates:  # pool exhausted (tiny pool) -- reset history
            candidates = list(self.pool)
            self.recent.clear()
        choice = self.rng.choice(candidates)
        self.recent.append(choice)
        return choice
