"""
Canonical internal representation models for generic Hyper-RAG ingestion pipeline.
Supports arbitrary structured, semi-structured, and unstructured document formats.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import time


@dataclass
class ContextPerspective:
    """A synthesized textual perspective ready for Hyper-RAG embedding and entity extraction."""
    perspective_name: str
    text: str
    source_id: str
    provenance: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "perspective_name": self.perspective_name,
            "text": self.text,
            "source_id": self.source_id,
            "provenance": self.provenance,
            "metadata": self.metadata,
        }


@dataclass
class CanonicalRecord:
    """Canonical representation of a single data record or document section."""
    record_id: str
    source_file: str
    source_type: str  # 'json', 'jsonl', 'csv', 'txt', 'md', 'pdf', 'docx'
    primary_title: str
    raw_text: Optional[str] = None
    structured_data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    provenance: Dict[str, Any] = field(default_factory=dict)
    contexts: List[ContextPerspective] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "source_file": self.source_file,
            "source_type": self.source_type,
            "primary_title": self.primary_title,
            "raw_text": self.raw_text,
            "structured_data": self.structured_data,
            "metadata": self.metadata,
            "provenance": self.provenance,
            "contexts": [c.to_dict() for c in self.contexts],
        }


@dataclass
class InferredSchema:
    """Inferred schema information for structured / semi-structured datasets."""
    field_types: Dict[str, str] = field(default_factory=dict)
    identifier_fields: List[str] = field(default_factory=list)
    title_fields: List[str] = field(default_factory=list)
    narrative_fields: List[str] = field(default_factory=list)
    categorical_fields: List[str] = field(default_factory=list)
    numeric_fields: List[str] = field(default_factory=list)
    nested_fields: List[str] = field(default_factory=list)
    array_fields: List[str] = field(default_factory=list)
    null_ratio: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field_types": self.field_types,
            "identifier_fields": self.identifier_fields,
            "title_fields": self.title_fields,
            "narrative_fields": self.narrative_fields,
            "categorical_fields": self.categorical_fields,
            "numeric_fields": self.numeric_fields,
            "nested_fields": self.nested_fields,
            "array_fields": self.array_fields,
            "null_ratio": self.null_ratio,
        }


@dataclass
class DatasetInspectionReport:
    """Preflight / preview summary of an uploaded file."""
    file_name: str
    file_type: str
    file_size_bytes: int
    record_count: int
    is_supported: bool
    suggested_database_name: str
    schema: Optional[InferredSchema] = None
    estimated_contexts: int = 0
    estimated_chunks: int = 0
    estimated_embeddings: int = 0
    estimated_llm_calls: int = 0
    sample_records: List[Dict[str, Any]] = field(default_factory=list)
    error_message: Optional[str] = None
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_name": self.file_name,
            "file_type": self.file_type,
            "file_size_bytes": self.file_size_bytes,
            "record_count": self.record_count,
            "is_supported": self.is_supported,
            "suggested_database_name": self.suggested_database_name,
            "schema": self.schema.to_dict() if self.schema else None,
            "estimated_contexts": self.estimated_contexts,
            "estimated_chunks": self.estimated_chunks,
            "estimated_embeddings": self.estimated_embeddings,
            "estimated_llm_calls": self.estimated_llm_calls,
            "sample_records": self.sample_records,
            "error_message": self.error_message,
            "created_at": self.created_at,
        }


@dataclass
class IngestionConfig:
    """Configuration options for file processing and Hyper-RAG indexing."""
    max_records: int = 100
    max_file_size_bytes: int = 50 * 1024 * 1024  # 50MB
    chunk_token_size: int = 1200
    chunk_overlap_token_size: int = 100
    dry_run: bool = False
    target_database_name: Optional[str] = None
    llm_func: Optional[Any] = None
    embedding_func: Optional[Any] = None
