import os, random
from dataclasses import dataclass
from .cards_data import CARD_NAMES
from .cards_meanings import CARDS_MEANINGS

@dataclass
class Card:
    id: int
    name: str
    image_path: str  # путь к картинке или ""
    meanings: dict   # {"upright": "...", "reversed": "..."}

def _guess_image_path(card_id: int) -> str:
    bases = [f"{card_id}", f"{card_id:02d}", f"{card_id:03d}"]
    exts = ["png", "jpg", "jpeg"]
    for base in bases:
        for ext in exts:
            p = os.path.join("media", "cards", f"{base}.{ext}")
            if os.path.exists(p):
                return p
    return ""

DECK = []
for i, name in enumerate(CARD_NAMES, 1):
    meanings = CARDS_MEANINGS.get(name, {"upright": "", "reversed": ""})
    DECK.append(Card(i, name, _guess_image_path(i), meanings))

def draw_cards(k: int, reversed_enabled: bool = True):
    chosen = random.sample(DECK, k)
    result = []
    for c in chosen:
        is_rev = reversed_enabled and (random.random() < 0.5)
        result.append((c, is_rev))
    return result
