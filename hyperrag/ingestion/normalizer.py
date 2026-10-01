"""
Generic normalizer and deduplication layer for arbitrary data records.
Operates 100% locally with zero external network or LLM calls.
Preserves original source provenance and semantics.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from .models import CanonicalRecord, InferredSchema


class GenericNormalizer:
    """Normalizes raw parsed records into clean canonical representations."""

    @staticmethod
    def clean_value(val: Any) -> Any:
        """Cleans whitespace and normalizes basic scalar types."""
        if val is None:
            return None
        if isinstance(val, str):
            cleaned = val.strip()
            # Collapse internal repeated whitespace
            cleaned = re.sub(r"[ \t]+", " ", cleaned)
            return cleaned if cleaned else None
        if isinstance(val, (int, float, bool)):
            return val
        if isinstance(val, list):
            cleaned_list = []
            for item in val:
                c = GenericNormalizer.clean_value(item)
                if c is not None:
                    cleaned_list.append(c)
            # Deduplicate items if scalars or dicts
            return GenericNormalizer.deduplicate_list(cleaned_list)
        if isinstance(val, dict):
            cleaned_dict = {}
            for k, v in val.items():
                c = GenericNormalizer.clean_value(v)
                if c is not None:
                    cleaned_dict[str(k).strip()] = c
            return cleaned_dict if cleaned_dict else None
        return val

    @staticmethod
    def deduplicate_list(items: List[Any]) -> List[Any]:
        """Deduplicates items in a list while preserving order."""
        seen = set()
        deduped = []
        for it in items:
            if isinstance(it, (str, int, float, bool)):
                key = str(it).lower()
                if key not in seen:
                    seen.add(key)
                    deduped.append(it)
            elif isinstance(it, dict):
                # Hashable representation of dict
                try:
                    key = json.dumps(it, sort_keys=True)
                except Exception:
                    key = str(it)
                if key not in seen:
                    seen.add(key)
                    deduped.append(it)
            else:
                deduped.append(it)
        return deduped

    @classmethod
    def normalize_records(
        cls,
        raw_records: List[Dict[str, Any]],
        source_file: str,
        source_type: str,
        schema: InferredSchema
    ) -> List[CanonicalRecord]:
        """
        Normalizes a list of raw records:
        1. Cleans fields.
        2. Detects shared record identifiers and merges multi-perspective records.
        3. Identifies primary title and key attributes.
        4. Builds CanonicalRecord instances with full provenance.
        """
        if not raw_records:
            return []

        # Find primary identifier field if available
        id_field = schema.identifier_fields[0] if schema.identifier_fields else None
        title_field = schema.title_fields[0] if schema.title_fields else id_field

        # Group by record_id if multi-record merging is appropriate (e.g. multiple perspectives in TSBC or repeated keys)
        grouped_records: Dict[str, List[Dict[str, Any]]] = {}
        for idx, raw in enumerate(raw_records):
            clean_raw = cls.clean_value(raw) or {}
            
            # Determine record_id
            rec_id = None
            if id_field and clean_raw.get(id_field) is not None:
                rec_id = str(clean_raw[id_field])
            elif "id" in clean_raw:
                rec_id = str(clean_raw["id"])
            elif "record_id" in clean_raw:
                rec_id = str(clean_raw["record_id"])
            else:
                rec_id = f"rec_{idx + 1}"

            grouped_records.setdefault(rec_id, []).append(clean_raw)

        canonical_list: List[CanonicalRecord] = []
        for rec_id, rows in grouped_records.items():
            merged_structured: Dict[str, Any] = {}
            raw_texts: List[str] = []

            for row_idx, r in enumerate(rows):
                for k, v in r.items():
                    if k == "text" and isinstance(v, str):
                        raw_texts.append(v)
                    elif k not in merged_structured:
                        merged_structured[k] = copy.deepcopy(v)
                    else:
                        existing = merged_structured[k]
                        if isinstance(existing, list) and isinstance(v, list):
                            merged_structured[k] = cls.deduplicate_list(existing + v)
                        elif isinstance(existing, list) and not isinstance(v, list):
                            if v not in existing:
                                existing.append(v)
                        elif existing != v and v is not None:
                            # If different scalar values, keep both or promote to list
                            if not isinstance(existing, list):
                                merged_structured[k] = [existing, v]
                            elif v not in existing:
                                existing.append(v)

            # Determine title
            primary_title = ""
            if title_field and merged_structured.get(title_field):
                primary_title = str(merged_structured[title_field])
            elif merged_structured.get("title"):
                primary_title = str(merged_structured["title"])
            elif merged_structured.get("name"):
                primary_title = str(merged_structured["name"])
            else:
                primary_title = f"{source_file} - Record {rec_id}"

            # Extract raw text if present
            raw_text = "\n\n".join(raw_texts) if raw_texts else merged_structured.get("text")
            if raw_text is not None and not isinstance(raw_text, str):
                raw_text = str(raw_text)

            provenance = {
                "source_file": source_file,
                "source_type": source_type,
                "record_id": rec_id,
                "raw_occurrence_count": len(rows),
            }

            canonical = CanonicalRecord(
                record_id=rec_id,
                source_file=source_file,
                source_type=source_type,
                primary_title=primary_title,
                raw_text=raw_text,
                structured_data=merged_structured,
                metadata={"field_count": len(merged_structured)},
                provenance=provenance,
            )
            canonical_list.append(canonical)

        return canonical_list
