"""Classroom of the Elite character slots.

Single source of truth for the 8 voice-casting slots. Consumed by
routes/casting.py and templates. `portrait_key` is separate from `slot`
because kushida_public and kushida_private share one illustration.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Character:
    slot: str
    label: str
    portrait_key: str
    variant: str | None = None  # e.g. "public" / "private" for Kushida's split


CHARACTERS: list[Character] = [
    Character("ayanokoji",       "Ayanokōji Kiyotaka",       "ayanokoji"),
    Character("horikita",        "Horikita Suzune",          "horikita"),
    Character("kushida_public",  "Kushida Kikyō",            "kushida", "public"),
    Character("kushida_private", "Kushida Kikyō",            "kushida", "private"),
    Character("karuizawa",       "Karuizawa Kei",            "karuizawa"),
    Character("ichinose",        "Ichinose Honami",          "ichinose"),
    Character("sakayanagi",      "Sakayanagi Arisu",         "sakayanagi"),
    Character("ryuen",           "Ryūen Kakeru",             "ryuen"),
]

SLOTS: list[str] = [c.slot for c in CHARACTERS]
BY_SLOT: dict[str, Character] = {c.slot: c for c in CHARACTERS}


def is_valid_slot(slot: str) -> bool:
    return slot in BY_SLOT


def as_dicts() -> list[dict]:
    """Serializable form for API responses and template JSON bootstrap."""
    return [
        {
            "slot": c.slot,
            "label": c.label,
            "portrait_key": c.portrait_key,
            "variant": c.variant,
        }
        for c in CHARACTERS
    ]
