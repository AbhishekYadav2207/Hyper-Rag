"""
Hyper-RAG Generic Ingestion Package.
Provides generic ingestion, schema inference, normalization, and context synthesis.
"""

from .models import (
    CanonicalRecord,
    ContextPerspective,
    DatasetInspectionReport,
    InferredSchema,
    IngestionConfig,
)
from .parser import GenericFileParser, SUPPORTED_EXTENSIONS
from .schema_infer import AutomaticSchemaInferer
from .normalizer import GenericNormalizer
from .context_builder import GenericContextBuilder
from .pipeline import GenericIngestionPipeline, sanitize_database_name

__all__ = [
    "CanonicalRecord",
    "ContextPerspective",
    "DatasetInspectionReport",
    "InferredSchema",
    "IngestionConfig",
    "GenericFileParser",
    "SUPPORTED_EXTENSIONS",
    "AutomaticSchemaInferer",
    "GenericNormalizer",
    "GenericContextBuilder",
    "GenericIngestionPipeline",
    "sanitize_database_name",
]
