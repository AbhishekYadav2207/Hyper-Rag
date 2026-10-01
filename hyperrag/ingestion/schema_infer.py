"""
Automatic schema and structure inference for arbitrary datasets.
Performs 100% deterministic local inspection without LLM or external API calls.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Set
from .models import InferredSchema


class AutomaticSchemaInferer:
    """Inspects arbitrary tabular or JSON records and infers structural semantics."""

    EXPLICIT_ID_KEYWORDS = ("id", "uuid", "key", "code", "sku", "pk")
    EXPLICIT_ID_SUFFIXES = ("_id", "_uuid", "_key", "_code", "_no", "_number", "_sku")
    EXPLICIT_ID_PREFIXES = ("id_", "uuid_", "key_")

    TITLE_KEYWORDS = ("name", "title", "label", "heading", "headline", "subject", "topic")
    NARRATIVE_KEYWORDS = (
        "summary", "description", "details", "text", "comment", "note",
        "abstract", "body", "overview", "narrative", "document", "content", "biography"
    )

    @classmethod
    def infer_schema(cls, records: List[Dict[str, Any]]) -> InferredSchema:
        if not records:
            return InferredSchema()

        total_records = len(records)
        all_keys: Set[str] = set()
        for r in records:
            all_keys.update(r.keys())

        field_types: Dict[str, str] = {}
        null_counts: Dict[str, int] = {k: 0 for k in all_keys}
        unique_values: Dict[str, Set[str]] = {k: set() for k in all_keys}
        string_lengths: Dict[str, List[int]] = {k: [] for k in all_keys}
        list_fields: Set[str] = set()
        dict_fields: Set[str] = set()
        numeric_fields: Set[str] = set()

        for r in records:
            for k in all_keys:
                val = r.get(k)
                if val is None or val == "" or val == [] or val == {}:
                    null_counts[k] += 1
                    continue

                if isinstance(val, bool):
                    field_types.setdefault(k, "bool")
                elif isinstance(val, (int, float)):
                    field_types.setdefault(k, "number")
                    numeric_fields.add(k)
                elif isinstance(val, dict):
                    field_types.setdefault(k, "dict")
                    dict_fields.add(k)
                elif isinstance(val, list):
                    field_types.setdefault(k, "list")
                    list_fields.add(k)
                elif isinstance(val, str):
                    field_types.setdefault(k, "str")
                    string_lengths[k].append(len(val))
                    if len(val) < 150:
                        unique_values[k].add(val.strip().lower())
                else:
                    field_types.setdefault(k, type(val).__name__)

        null_ratios = {k: null_counts[k] / total_records for k in all_keys}

        identifier_candidates = []
        title_candidates = []
        narrative_candidates = []
        categorical_candidates = []

        # 1. Detect explicit IDs first
        for k in sorted(list(all_keys)):
            lk = k.lower()
            is_explicit_id = (
                lk in cls.EXPLICIT_ID_KEYWORDS or
                any(lk.endswith(suf) for suf in cls.EXPLICIT_ID_SUFFIXES) or
                any(lk.startswith(pre) for pre in cls.EXPLICIT_ID_PREFIXES)
            )
            if is_explicit_id:
                identifier_candidates.append(k)

        # 2. Detect title / entity name fields
        for k in sorted(list(all_keys)):
            lk = k.lower()
            is_title = any(tk in lk for tk in cls.TITLE_KEYWORDS)
            # Make sure it's not purely an ID like "item_id" or "name_id"
            if is_title and not any(lk.endswith(suf) for suf in cls.EXPLICIT_ID_SUFFIXES):
                title_candidates.append(k)

        # 3. Detect narrative / prose fields
        for k in sorted(list(all_keys)):
            lk = k.lower()
            is_narrative_keyword = any(nk in lk for nk in cls.NARRATIVE_KEYWORDS)
            avg_len = (sum(string_lengths[k]) / len(string_lengths[k])) if string_lengths[k] else 0
            if is_narrative_keyword or avg_len > 70:
                narrative_candidates.append(k)

        # 4. If no explicit identifier found, check unique scalar fields
        if not identifier_candidates and total_records > 1:
            for k in sorted(list(all_keys)):
                if k not in title_candidates and k not in narrative_candidates:
                    if len(unique_values[k]) == total_records and field_types.get(k) in ("str", "number"):
                        identifier_candidates.append(k)
                        break

        # 5. Categorical candidates (non-narrative, non-ID, non-title strings)
        for k in sorted(list(all_keys)):
            if (
                field_types.get(k) == "str"
                and k not in narrative_candidates
                and k not in identifier_candidates
                and k not in title_candidates
            ):
                num_unique = len(unique_values[k])
                if 1 <= num_unique <= min(30, max(2, total_records)):
                    categorical_candidates.append(k)

        # Ensure title prioritization: if full_name, name, or title exists, place at head
        title_candidates.sort(key=lambda x: 0 if x.lower() in ("name", "full_name", "title") else 1)

        # If no explicit title candidate, use first identifier or fallback
        if not title_candidates and identifier_candidates:
            title_candidates = [identifier_candidates[0]]

        return InferredSchema(
            field_types=field_types,
            identifier_fields=identifier_candidates,
            title_fields=title_candidates,
            narrative_fields=narrative_candidates,
            categorical_fields=categorical_candidates,
            numeric_fields=sorted(list(numeric_fields)),
            nested_fields=sorted(list(dict_fields)),
            array_fields=sorted(list(list_fields)),
            null_ratio={k: round(v, 3) for k, v in null_ratios.items()},
        )
