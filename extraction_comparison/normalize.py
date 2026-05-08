import re
from typing import Optional

from .config import (
    NEGATION_TOKENS,
    NOT_REPORTED_SENTINEL,
    NOT_REPORTED_VARIANTS,
    PREDICTOR_ALIASES,
)


_DASH_CHARS = "‐‑‒–—―−"
_QUOTE_PAIRS = {
    "‘": "'",
    "’": "'",
    "“": '"',
    "”": '"',
    "´": "'",
    "`": "'",
}
_PUNCT_TO_STRIP_TRAILING = ".,;:"


def _replace_dashes(s: str) -> str:
    for ch in _DASH_CHARS:
        s = s.replace(ch, "-")
    return s


def _replace_quotes(s: str) -> str:
    for src, dst in _QUOTE_PAIRS.items():
        s = s.replace(src, dst)
    return s


def normalize_text(value: Optional[str]) -> str:
    """Lowercase, trim, collapse whitespace, normalize quotes/dashes."""
    if value is None:
        return NOT_REPORTED_SENTINEL
    s = str(value)
    s = _replace_dashes(s)
    s = _replace_quotes(s)
    s = s.strip().lower()
    s = re.sub(r"\s+", " ", s)
    s = s.rstrip(_PUNCT_TO_STRIP_TRAILING).strip()
    if s in NOT_REPORTED_VARIANTS:
        return NOT_REPORTED_SENTINEL
    return s


def is_not_reported(value: Optional[str]) -> bool:
    return normalize_text(value) == NOT_REPORTED_SENTINEL


def parse_sample_size(value: Optional[str]) -> Optional[int]:
    """Pull the first integer out of strings like 'N=72', 'n = 72', '72 patients'.

    Returns None when the field is not-reported. Returns the integer otherwise,
    or raises ValueError if there's text but no parseable integer.
    """
    if is_not_reported(value):
        return None
    s = normalize_text(value)
    match = re.search(r"-?\d[\d,]*", s)
    if not match:
        raise ValueError(f"could not parse sample size from {value!r}")
    digits = match.group(0).replace(",", "")
    return int(digits)


def normalize_predictor(value: Optional[str]) -> str:
    s = normalize_text(value)
    if s == NOT_REPORTED_SENTINEL:
        return s
    s = re.sub(r"\bscore\b", "", s).strip()
    s = re.sub(r"\s+", " ", s)
    return PREDICTOR_ALIASES.get(s, s)


def normalize_study_key(value: Optional[str]) -> str:
    """Reduce 'Gai et al. 2021', 'Gai et al., 2021', 'Gai 2021' to a stable key."""
    s = normalize_text(value)
    if s == NOT_REPORTED_SENTINEL:
        return s
    s = re.sub(r"\bet\s+al\b\.?", "", s)
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


_NEGATION_PATTERN = re.compile(
    r"(?:^|\s|-)(?:" + "|".join(re.escape(t) for t in NEGATION_TOKENS) + r")(?:\s|-|$)"
)


def has_negation(value: Optional[str]) -> bool:
    s = normalize_text(value)
    if s == NOT_REPORTED_SENTINEL:
        return False
    return bool(_NEGATION_PATTERN.search(" " + s + " "))
