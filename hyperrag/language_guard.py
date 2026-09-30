# -*- coding: utf-8 -*-
"""
Deterministic Output-Language Safety Guard
Ensures user-facing responses conform strictly to English-only output requirements.
No second LLM calls. No external language-model translation. 100% deterministic.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple


# Regex patterns for non-English script detection
_CJK_PATTERN = re.compile(
    r"[\u3040-\u30ff"   # Hiragana & Katakana
    r"\u3400-\u4dbf"   # CJK Unified Ideographs Extension A
    r"\u4e00-\u9fff"   # CJK Unified Ideographs
    r"\uf900-\ufaff"   # CJK Compatibility Ideographs
    r"\uac00-\ud7af"   # Hangul Syllables
    r"\u3000-\u303f"   # CJK Symbols and Punctuation
    r"\uff00-\uffef]"  # Halfwidth and Fullwidth Forms (CJK punctuation)
)

_CYRILLIC_PATTERN = re.compile(r"[\u0400-\u04ff]")
_ARABIC_PATTERN = re.compile(r"[\u0600-\u06ff\u0750-\u077f]")
_DEVANAGARI_PATTERN = re.compile(r"[\u0900-\u097f]")
_LATIN_PATTERN = re.compile(r"[A-Za-z]")


@dataclass
class LanguageGuardResult:
    """Structured result from deterministic language guard."""
    is_english: bool
    detected_languages: List[str] = field(default_factory=list)
    cjk_count: int = 0
    cjk_ratio: float = 0.0
    non_latin_count: int = 0
    latin_count: int = 0
    violating_snippets: List[str] = field(default_factory=list)
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_english": self.is_english,
            "detected_languages": self.detected_languages,
            "cjk_count": self.cjk_count,
            "cjk_ratio": round(self.cjk_ratio, 4),
            "non_latin_count": self.non_latin_count,
            "latin_count": self.latin_count,
            "violating_snippets": self.violating_snippets[:5],
            "reason": self.reason,
        }


class LanguageGuard:
    """
    Deterministic language safety guard.
    Detects CJK characters, Arabic, Cyrillic, Devanagari, and non-Latin script dominance.
    """

    def __init__(self, max_cjk_allowed: int = 0, cjk_threshold_ratio: float = 0.001):
        self.max_cjk_allowed = max_cjk_allowed
        self.cjk_threshold_ratio = cjk_threshold_ratio

    def check(self, text: str) -> LanguageGuardResult:
        if not text or not text.strip():
            return LanguageGuardResult(is_english=True, detected_languages=["English"])

        cleaned = text.strip()
        total_chars = len(cleaned)

        # CJK checks
        cjk_matches = _CJK_PATTERN.findall(cleaned)
        cjk_count = len(cjk_matches)
        cjk_ratio = cjk_count / max(1, total_chars)

        # Other script counts
        cyrillic_count = len(_CYRILLIC_PATTERN.findall(cleaned))
        arabic_count = len(_ARABIC_PATTERN.findall(cleaned))
        devanagari_count = len(_DEVANAGARI_PATTERN.findall(cleaned))
        latin_count = len(_LATIN_PATTERN.findall(cleaned))

        non_latin_count = cjk_count + cyrillic_count + arabic_count + devanagari_count
        detected_languages: List[str] = []

        if latin_count > 0:
            detected_languages.append("English")
        if cjk_count > 0:
            detected_languages.append("CJK/Chinese")
        if cyrillic_count > 0:
            detected_languages.append("Cyrillic")
        if arabic_count > 0:
            detected_languages.append("Arabic")
        if devanagari_count > 0:
            detected_languages.append("Devanagari")

        violating_snippets: List[str] = []
        if cjk_count > self.max_cjk_allowed:
            # Extract consecutive CJK runs as snippets
            cjk_runs = re.findall(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uac00-\ud7af\u3000-\u303f\uff00-\uffef]+", cleaned)
            violating_snippets.extend(cjk_runs[:5])

            return LanguageGuardResult(
                is_english=False,
                detected_languages=detected_languages,
                cjk_count=cjk_count,
                cjk_ratio=cjk_ratio,
                non_latin_count=non_latin_count,
                latin_count=latin_count,
                violating_snippets=violating_snippets,
                reason=f"Detected {cjk_count} CJK/Chinese character(s) (ratio: {cjk_ratio:.3%})",
            )

        # Non-Latin dominance check (excluding punctuation/numbers)
        alphabetic_count = latin_count + non_latin_count
        if alphabetic_count > 10 and (non_latin_count / alphabetic_count) > 0.3:
            return LanguageGuardResult(
                is_english=False,
                detected_languages=detected_languages,
                cjk_count=cjk_count,
                cjk_ratio=cjk_ratio,
                non_latin_count=non_latin_count,
                latin_count=latin_count,
                violating_snippets=violating_snippets,
                reason=f"Non-Latin script dominance detected ({non_latin_count}/{alphabetic_count})",
            )

        return LanguageGuardResult(
            is_english=True,
            detected_languages=detected_languages or ["English"],
            cjk_count=0,
            cjk_ratio=0.0,
            non_latin_count=non_latin_count,
            latin_count=latin_count,
            violating_snippets=[],
            reason="Output conforms to English language requirements",
        )
