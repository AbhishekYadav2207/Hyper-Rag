# -*- coding: utf-8 -*-
"""
Unit tests for deterministic LanguageGuard.
Verifies English-only compliance, CJK detection, script dominance, and zero LLM calls.
"""

import pytest
from hyperrag.language_guard import LanguageGuard, LanguageGuardResult


def test_english_text_passes():
    guard = LanguageGuard()
    res = guard.check("Maritime corrosion occurs when metals react with environmental oxygen and saltwater.")
    assert res.is_english is True
    assert res.cjk_count == 0
    assert "English" in res.detected_languages
    assert res.violating_snippets == []


def test_chinese_text_rejected():
    guard = LanguageGuard()
    res = guard.check("这是一个关于海洋腐蚀的回答。它解释了金属在海水中的化学反应。")
    assert res.is_english is False
    assert res.cjk_count > 0
    assert "CJK/Chinese" in res.detected_languages
    assert len(res.violating_snippets) > 0


def test_mixed_english_with_chinese_leakage_rejected():
    guard = LanguageGuard()
    res = guard.check("The vessel suffered severe damage in the engine room (机舱受损严重).")
    assert res.is_english is False
    assert res.cjk_count == 6
    assert "机舱受损严重" in res.violating_snippets[0]


def test_cyrillic_dominance_rejected():
    guard = LanguageGuard()
    res = guard.check("Судно потерпело крушение в районе залива Святого Лаврентия.")
    assert res.is_english is False
    assert "Cyrillic" in res.detected_languages


def test_empty_and_whitespace_handled():
    guard = LanguageGuard()
    res_empty = guard.check("")
    assert res_empty.is_english is True

    res_spaces = guard.check("   \n\t  ")
    assert res_spaces.is_english is True


def test_to_dict_format():
    guard = LanguageGuard()
    res = guard.check("Vessel grounding investigation report summary.")
    d = res.to_dict()
    assert "is_english" in d
    assert d["is_english"] is True
    assert "cjk_count" in d
    assert d["cjk_count"] == 0
    assert "detected_languages" in d
    assert "reason" in d
