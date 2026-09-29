from __future__ import annotations

import re

from .models import Notice


def normalize(value: str) -> str:
    return re.sub(r"\s+", "", value).casefold()


def match_notice(
    notice: Notice,
    keywords: list[str],
    mode: str,
    exclusions: list[str],
) -> Notice | None:
    haystack = normalize(f"{notice.title} {notice.organization}")
    wanted = [(keyword, normalize(keyword)) for keyword in keywords if normalize(keyword)]
    blocked = [normalize(word) for word in exclusions if normalize(word)]
    if any(word in haystack for word in blocked):
        return None
    hits = [original for original, term in wanted if term in haystack]
    if not wanted:
        return None
    matched = len(hits) == len(wanted) if mode.upper() == "AND" else bool(hits)
    if not matched:
        return None
    notice.matched_keywords = hits
    return notice
