"""Politesses reconnues en dur, avec une réponse fixe.

Seul un message composé uniquement de ces formules reçoit une réponse fixe : « bonjour, je
cherche un studio à Douala » contient une demande et part vers la recherche.
"""

import re

from app.engines.scout.registry import normalize_prompt

HOW_ARE_YOU_REPLY = (
    "Je vais bien, merci ! Je peux vous aider à trouver un logement à louer au Cameroun. "
    "Dites-moi la ville, le quartier, votre budget ou le nombre de chambres."
)
GREETING_REPLY = (
    "Bonjour ! Je vous aide à trouver un logement à louer au Cameroun. "
    "Dites-moi la ville, le quartier, votre budget ou le nombre de chambres."
)
THANKS_REPLY = "Avec plaisir ! N'hésitez pas si vous voulez affiner la recherche."
GOODBYE_REPLY = "Au revoir et bonne recherche !"
ABOUT_REPLY = (
    "Je suis Kwatsur, un assistant de recherche de logements à louer au Cameroun. "
    "Décrivez ce que vous cherchez (ville, quartier, budget, chambres), même en plusieurs messages : "
    "je garde le fil de la conversation."
)

# Ordre = priorité de la réponse quand plusieurs formules sont combinées.
SMALL_TALK: tuple[tuple[str, tuple[str, ...]], ...] = (
    (ABOUT_REPLY, (
        "qui es tu", "qui etes vous", "que sais tu faire", "que peux tu faire",
        "tu fais quoi", "comment ca marche", "comment tu marches",
    )),
    (HOW_ARE_YOU_REPLY, (
        "comment ca va", "comment vas tu", "comment allez vous", "ca va", "ca va bien",
        "tu vas bien", "vous allez bien", "la forme", "quoi de neuf",
    )),
    (GOODBYE_REPLY, (
        "au revoir", "bye", "bye bye", "a plus", "a bientot", "bonne journee", "bonne soiree", "bonne nuit",
    )),
    (THANKS_REPLY, ("merci", "merci beaucoup", "merci bien", "ok merci", "super merci")),
    (GREETING_REPLY, (
        "bonjour", "bonsoir", "salut", "hello", "hi", "coucou", "bjr", "slt", "yo", "hey", "bonjour a vous",
    )),
)
ALL_PHRASES = sorted(
    {phrase for _, phrases in SMALL_TALK for phrase in phrases}, key=len, reverse=True
)
PHRASE_PATTERN = re.compile(r"\b(" + "|".join(re.escape(phrase) for phrase in ALL_PHRASES) + r")\b")


def small_talk_reply(message: str) -> str | None:
    """Réponse fixe si le message n'est fait que de politesses, sinon `None`."""
    text = re.sub(r"[^a-z0-9 ]", " ", normalize_prompt(message))
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return None
    found = set(PHRASE_PATTERN.findall(text))
    if not found or PHRASE_PATTERN.sub(" ", text).strip():
        return None
    for reply, phrases in SMALL_TALK:
        if found.intersection(phrases):
            return reply
    return None
