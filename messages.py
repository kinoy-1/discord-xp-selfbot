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
    "selamat pagi semuanya, semangat hari ini",
    "ada yang udah sarapan belum",
    "lagi hujan di tempat kalian gak",
    "wih rame juga server ini ya",
    "btw game apa yang lagi rame sekarang",
    "ada yang tau cara cepet naik rank gak",
    "baru selesai nugas, akhirnya bisa santai",
    "siapa yang udah nonton film itu",
    "lagi nyari lagu baru, ada rekomendasi gak",
    "aduh ngantuk banget padahal baru jam segini",
    "ada yang main valorant gak",
    "info dong server ini ada event apa aja",
    "wah makasih infonya",
    "lagi scroll-scroll nemu ini, lucu banget",
    "ada yang dari bandung di sini",
    "baru pulang kerja, capek pol",
    "siapa yang suka kopi item di sini",
    "lagi pengen makan mie ayam wkwk",
    "btw hp kalian udah update belum",
    "ada yang nonton bola semalem, gila sih",
    "seru banget ngobrol di sini, betah",
    "lagi belajar hal baru nih, susah juga ya",
    "ada yang bisa rekomendasiin anime bagus",
    "wih udah level segitu aja, cepet banget",
    "lagi iseng buka discord, ternyata rame",
    "siapa yang masih kerja lembur jam segini",
    "baru denger kabar ini, beneran gak sih",
    "ada yang punya playlist spotify enak",
    "lagi mikir mau liburan kemana",
    "wah ini meme-nya lucu banget",
    "ada yang tau jam bukanya kapan",
    "baru nyoba fitur barunya, lumayan juga",
    "lagi nungguin gajian wkwk",
    "siapa di sini yang suka nonton drakor",
    "aduh sinyal lagi jelek banget",
    "ada yang mau tukeran rekomendasi buku gak",
    "baru bangun tidur, masih ngantuk",
    "lagi di jalan, macet parah",
    "wah selamat ya buat yang menang tadi",
    "ada yang ngerti ini maksudnya apa",
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
    "good morning everyone, hope today goes well",
    "did anyone have breakfast yet",
    "is it raining where you guys are",
    "this server is pretty lively huh",
    "btw what game is popular right now",
    "anyone know how to rank up fast",
    "just finished my homework, finally free",
    "has anyone watched that movie yet",
    "looking for new music, any recommendations",
    "so sleepy even though it's still early",
    "anyone playing valorant tonight",
    "what events does this server have",
    "thanks for the info, really helpful",
    "was just scrolling and found this, so funny",
    "anyone from around here",
    "just got home from work, totally exhausted",
    "who else likes black coffee here",
    "craving some noodles right now lol",
    "did you guys update your phones yet",
    "did anyone watch the game last night, insane",
    "chatting here is really fun, I could stay all day",
    "learning something new, harder than I thought",
    "any good anime recommendations",
    "wow you leveled up so fast",
    "just opened discord for fun, it's busy in here",
    "who else is working overtime right now",
    "just heard this news, is it true",
    "anyone got a good spotify playlist",
    "thinking about where to go on holiday",
    "this meme is so funny",
    "does anyone know when it opens",
    "just tried the new feature, pretty decent",
    "waiting for payday lol",
    "who here likes watching dramas",
    "my signal is so bad right now",
    "anyone want to swap book recommendations",
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
