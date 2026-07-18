"""Shared adult (18+) policy helpers for NSFW factory tools."""

from __future__ import annotations

# Light string guard — not a full classifier. Agents must still use judgment.
BANNED_AGE_TERMS: tuple[str, ...] = (
    "child",
    "kid",
    "loli",
    "shota",
    "underage",
    "teen boy",
    "teen girl",
    "schoolgirl",
    "schoolboy",
    "12 year",
    "14 year",
    "15 year",
    "16 year",
    "17 year",
)


def age_policy_hits(text: str) -> list[str]:
    low = (text or "").lower()
    return [b for b in BANNED_AGE_TERMS if b in low]


def check_adult_prompt(text: str) -> tuple[bool, list[str]]:
    """Return (ok, hits). ok=False → refuse (exit 11 convention)."""
    hits = age_policy_hits(text)
    return (len(hits) == 0, hits)
