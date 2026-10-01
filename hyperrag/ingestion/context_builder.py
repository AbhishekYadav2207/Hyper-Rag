"""
Generic retrieval context builder for Hyper-RAG ingestion.
Transforms canonical records into rich, targeted narrative contexts
optimized for mistral-embed vector retrieval and hypergraph entity-relation extraction.
100% deterministic and local; zero LLM calls.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from .models import CanonicalRecord, ContextPerspective, InferredSchema


class GenericContextBuilder:
    """Derives retrieval-friendly textual contexts from canonical records."""

    @classmethod
    def generate_contexts_for_record(
        cls,
        record: CanonicalRecord,
        schema: Optional[InferredSchema] = None
    ) -> List[ContextPerspective]:
        """Generates 1 to 4 focused perspectives for a record."""
        # Case A: Pure document / text section (from PDF, DOCX, TXT, MD)
        if record.source_type in ("text", "pdf", "docx") or (record.raw_text and len(record.structured_data) <= 3):
            return cls._build_document_context(record)

        # Case B: Structured record (from JSON, JSONL, CSV)
        return cls._build_structured_contexts(record, schema)

    @classmethod
    def _build_document_context(cls, record: CanonicalRecord) -> List[ContextPerspective]:
        title = record.primary_title or record.source_file
        body = record.raw_text or record.structured_data.get("text", "")
        section_type = record.structured_data.get("section_type", "document")
        page_num = record.structured_data.get("page_number")

        lines = [f"# {title}"]
        if page_num:
            lines.append(f"Source Page: {page_num}")
        lines.append(f"Source Document: {record.source_file}")
        lines.append("")
        lines.append(body)

        full_text = "\n".join(lines).strip()
        perspective = ContextPerspective(
            perspective_name=f"{section_type}_overview",
            text=full_text,
            source_id=record.record_id,
            provenance=record.provenance,
            metadata={"title": title, "page_number": page_num}
        )
        return [perspective]

    @classmethod
    def _build_structured_contexts(
        cls,
        record: CanonicalRecord,
        schema: Optional[InferredSchema] = None
    ) -> List[ContextPerspective]:
        data = record.structured_data
        title = record.primary_title
        rec_id = record.record_id
        contexts: List[ContextPerspective] = []

        narrative_keys = set(schema.narrative_fields if schema else [])
        categorical_keys = set(schema.categorical_fields if schema else [])
        array_keys = set(schema.array_fields if schema else [])
        nested_keys = set(schema.nested_fields if schema else [])
        numeric_keys = set(schema.numeric_fields if schema else [])

        # Categorize keys
        seen_keys = set()

        # 1. Perspective: Record Overview & Identity
        overview_lines = [
            f"Record Identity: {title} (ID: {rec_id})",
            f"Source File: {record.source_file}"
        ]

        # Add categorical and status indicators
        for cat_k in sorted(categorical_keys):
            if cat_k in data and data[cat_k] is not None:
                val = data[cat_k]
                overview_lines.append(f"{cat_k.replace('_', ' ').title()}: {val}")
                seen_keys.add(cat_k)

        # Add brief description if present
        for nk in sorted(narrative_keys):
            val = data.get(nk)
            if val and isinstance(val, str) and len(val) < 200:
                overview_lines.append(f"{nk.replace('_', ' ').title()}: {val}")
                seen_keys.add(nk)

        contexts.append(ContextPerspective(
            perspective_name="record_overview",
            text="\n".join(overview_lines),
            source_id=rec_id,
            provenance={**record.provenance, "perspective": "record_overview"},
        ))

        # 2. Perspective: Attributes & Specifications
        attr_lines = [f"Attributes for {title} (ID: {rec_id}):"]
        for k, v in data.items():
            if k in seen_keys or k in array_keys or k in nested_keys or k in narrative_keys:
                continue
            if v is not None and v != "":
                if isinstance(v, (str, int, float, bool)):
                    attr_lines.append(f"- {k.replace('_', ' ').title()}: {v}")
                    seen_keys.add(k)

        if len(attr_lines) > 1:
            contexts.append(ContextPerspective(
                perspective_name="specifications_and_attributes",
                text="\n".join(attr_lines),
                source_id=rec_id,
                provenance={**record.provenance, "perspective": "specifications_and_attributes"},
            ))

        # 3. Perspective: Narratives / Long Descriptions
        narrative_lines = []
        for nk in sorted(narrative_keys):
            val = data.get(nk)
            if val and isinstance(val, str) and len(val) >= 50:
                narrative_lines.append(f"--- {nk.replace('_', ' ').title()} ---")
                narrative_lines.append(val)
                seen_keys.add(nk)

        if narrative_lines:
            header = f"Narrative and Detailed Account for {title} (ID: {rec_id}):\n"
            full_narrative = header + "\n\n".join(narrative_lines)
            contexts.append(ContextPerspective(
                perspective_name="narrative_details",
                text=full_narrative,
                source_id=rec_id,
                provenance={**record.provenance, "perspective": "narrative_details"},
            ))

        # 4. Perspective: Collections / Relations / Nested Arrays
        collection_lines = []
        for ak in sorted(array_keys):
            val = data.get(ak)
            if val and isinstance(val, list):
                collection_lines.append(f"Associated {ak.replace('_', ' ').title()} for {title}:")
                for item in val:
                    if isinstance(item, dict):
                        # Format nested dict properties
                        item_props = [f"{ik}: {iv}" for ik, iv in item.items() if iv is not None and iv != ""]
                        collection_lines.append(f"  * {', '.join(item_props)}")
                    else:
                        collection_lines.append(f"  * {item}")

        # Also include nested dict objects
        for dk in sorted(nested_keys):
            val = data.get(dk)
            if val and isinstance(val, dict):
                collection_lines.append(f"{dk.replace('_', ' ').title()} for {title}:")
                for sub_k, sub_v in val.items():
                    if sub_v is not None and sub_v != "" and not isinstance(sub_v, (dict, list)):
                        collection_lines.append(f"  * {sub_k.replace('_', ' ').title()}: {sub_v}")

        if collection_lines:
            contexts.append(ContextPerspective(
                perspective_name="relations_and_collections",
                text="\n".join(collection_lines),
                source_id=rec_id,
                provenance={**record.provenance, "perspective": "relations_and_collections"},
            ))

        return contexts
