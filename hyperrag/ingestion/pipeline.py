"""
Generic Ingestion Pipeline for Hyper-RAG.
Coordinates file parsing, schema inference, normalization, context synthesis,
and isolated Hyper-RAG indexing.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

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

logger = logging.getLogger("generic_ingestion")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CACHES_DIR = PROJECT_ROOT / "caches"
HYPERRAG_CACHE_DIR = PROJECT_ROOT / "hyperrag_cache"


def sanitize_database_name(raw_name: str) -> str:
    """Produces a clean, filesystem-safe and web-safe database name."""
    clean = re.sub(r"[^\w\-_]", "_", raw_name.strip()).lower()
    clean = re.sub(r"_+", "_", clean).strip("_")
    # Reserve core databases
    reserved = {"mock", "tsbc_maritime_test", "tsbc_maritime_test_3"}
    if clean in reserved:
        clean = f"{clean}_custom_{int(time.time())}"
    if not clean:
        clean = f"dataset_{int(time.time())}"
    return clean[:32]


class GenericIngestionPipeline:
    """End-to-end ingestion pipeline from raw file to isolated Hyper-RAG database."""

    def __init__(self, config: Optional[IngestionConfig] = None):
        self.config = config or IngestionConfig()
        self.parser = GenericFileParser(max_file_size_bytes=self.config.max_file_size_bytes)

    def preflight_inspect(
        self,
        file_path: Union[str, Path],
        original_filename: Optional[str] = None
    ) -> DatasetInspectionReport:
        """
        Executes a 100% local preflight inspection of an uploaded file.
        Returns detailed summary and estimates without any external API calls.
        """
        path = Path(file_path)
        fname = original_filename or path.name
        ext = Path(fname).suffix.lower()
        file_size = path.stat().st_size if path.exists() else 0

        suggested_db = sanitize_database_name(Path(fname).stem)

        if ext not in SUPPORTED_EXTENSIONS:
            return DatasetInspectionReport(
                file_name=fname,
                file_type=ext,
                file_size_bytes=file_size,
                record_count=0,
                is_supported=False,
                suggested_database_name=suggested_db,
                error_message=f"Unsupported format '{ext}'. Supported: {', '.join(sorted(list(SUPPORTED_EXTENSIONS)))}"
            )

        try:
            format_type, raw_records = self.parser.parse_file(path, original_filename=fname)
            schema = AutomaticSchemaInferer.infer_schema(raw_records)
            canonical_records = GenericNormalizer.normalize_records(
                raw_records, source_file=fname, source_type=format_type, schema=schema
            )

            # Estimate contexts and operations
            total_contexts = 0
            total_chars = 0
            sample_recs = []

            for idx, rec in enumerate(canonical_records):
                ctxs = GenericContextBuilder.generate_contexts_for_record(rec, schema)
                total_contexts += len(ctxs)
                total_chars += sum(len(c.text) for c in ctxs)
                if idx < 3:
                    sample_recs.append({
                        "id": rec.record_id,
                        "title": rec.primary_title,
                        "contexts_count": len(ctxs),
                        "snippet": ctxs[0].text[:180] + ("..." if len(ctxs[0].text) > 180 else "")
                    })

            estimated_chunks = max(1, (total_chars // 1000) + 1)
            estimated_embeddings = estimated_chunks
            estimated_llm_calls = estimated_chunks * 2

            return DatasetInspectionReport(
                file_name=fname,
                file_type=ext,
                file_size_bytes=file_size,
                record_count=len(canonical_records),
                is_supported=True,
                suggested_database_name=suggested_db,
                schema=schema,
                estimated_contexts=total_contexts,
                estimated_chunks=estimated_chunks,
                estimated_embeddings=estimated_embeddings,
                estimated_llm_calls=estimated_llm_calls,
                sample_records=sample_recs,
            )

        except Exception as e:
            return DatasetInspectionReport(
                file_name=fname,
                file_type=ext,
                file_size_bytes=file_size,
                record_count=0,
                is_supported=False,
                suggested_database_name=suggested_db,
                error_message=str(e),
            )

    async def ingest_file(
        self,
        file_path: Union[str, Path],
        target_database_name: Optional[str] = None,
        original_filename: Optional[str] = None,
        progress_callback: Optional[Callable[[str, Dict[str, Any]], Any]] = None,
    ) -> Dict[str, Any]:
        """
        Executes full ingestion:
        Parse -> Schema Inference -> Normalization -> Context Synthesis -> Hyper-RAG indexing.
        Ensures strict database isolation and proper embedding dimension validation.
        """
        path = Path(file_path)
        fname = original_filename or path.name

        async def notify(stage: str, details: Dict[str, Any]):
            if progress_callback:
                res = progress_callback(stage, details)
                if asyncio.iscoroutine(res):
                    await res

        await notify("inspecting", {"message": f"Inspecting file: {fname}"})
        report = self.preflight_inspect(path, original_filename=fname)

        if not report.is_supported or report.error_message:
            await notify("failed", {"error": report.error_message or "Unsupported file"})
            raise ValueError(f"Preflight inspection failed: {report.error_message}")

        if report.record_count > self.config.max_records:
            err = (
                f"Dataset contains {report.record_count} records, which exceeds the safety limit "
                f"of {self.config.max_records} records. Please adjust IngestionConfig.max_records if intended."
            )
            await notify("failed", {"error": err})
            raise ValueError(err)

        # Determine target database name
        db_name = sanitize_database_name(target_database_name or report.suggested_database_name)
        await notify("parsing", {"message": f"Parsing {report.record_count} records from {fname}"})

        format_type, raw_records = self.parser.parse_file(path, original_filename=fname)
        schema = AutomaticSchemaInferer.infer_schema(raw_records)

        await notify("preparing", {"message": "Normalizing data and synthesizing retrieval contexts"})
        canonical_records = GenericNormalizer.normalize_records(
            raw_records, source_file=fname, source_type=format_type, schema=schema
        )

        all_contexts: List[ContextPerspective] = []
        for rec in canonical_records:
            ctxs = GenericContextBuilder.generate_contexts_for_record(rec, schema)
            rec.contexts = ctxs
            all_contexts.extend(ctxs)

        if not all_contexts:
            err = "No retrieval contexts could be generated from the uploaded file."
            await notify("failed", {"error": err})
            raise ValueError(err)

        # Prepare isolated storage directories
        cache_db_dir = CACHES_DIR / db_name
        cache_db_dir.mkdir(parents=True, exist_ok=True)
        hyperrag_link_dir = HYPERRAG_CACHE_DIR / db_name

        self._ensure_cache_link(cache_db_dir, hyperrag_link_dir)

        if self.config.dry_run:
            await notify("ready", {"message": "Dry-run complete (zero external API calls)"})
            return {
                "status": "DRY_RUN_SUCCESS",
                "database_name": db_name,
                "records_processed": len(canonical_records),
                "contexts_generated": len(all_contexts),
                "cache_directory": str(cache_db_dir),
            }

        # Initialize Hyper-RAG with project-verified configurations
        await notify("indexing", {
            "message": f"Building vector & hypergraph indices for database '{db_name}' ({len(all_contexts)} contexts)...",
            "database_name": db_name,
            "total_contexts": len(all_contexts),
        })

        try:
            from hyperrag import HyperRAG
            from hyperrag.utils import EmbeddingFunc
            from hyperrag.llm import openai_embedding, openrouter_mistral_complete_if_cache

            llm_func = self.config.llm_func
            emb_func = self.config.embedding_func
            emb_dim = 1024

            if llm_func is None:
                async def default_llm(prompt, system_prompt=None, history_messages=None, **kwargs):
                    return await openrouter_mistral_complete_if_cache(
                        prompt,
                        system_prompt=system_prompt,
                        history_messages=history_messages or [],
                        **kwargs,
                    )
                llm_func = default_llm

            if emb_func is None:
                from my_config import EMB_MODEL, EMB_DIM, EMB_BASE_URL, EMB_API_KEY
                emb_dim = EMB_DIM
                if emb_dim != 1024:
                    raise ValueError(
                        f"Invalid embedding dimension {emb_dim}. Project requires 1024-dimensional Mistral embeddings."
                    )
                async def default_emb(texts: list[str]):
                    return await openai_embedding(
                        texts,
                        model=EMB_MODEL,
                        api_key=EMB_API_KEY,
                        base_url=EMB_BASE_URL,
                    )
                emb_func = default_emb

            rag = HyperRAG(
                working_dir=str(cache_db_dir),
                llm_model_func=llm_func,
                embedding_func=EmbeddingFunc(
                    embedding_dim=emb_dim,
                    max_token_size=8192,
                    func=emb_func,
                ),
            )

            # Synthesize combined document units
            doc_units = [c.text for c in all_contexts]
            combined_doc = "\n\n---\n\n".join(doc_units)

            logger.info(f"Inserting {len(all_contexts)} contexts into HyperRAG database '{db_name}'...")
            await rag.ainsert(combined_doc)
            logger.info(f"HyperRAG insertion complete for database '{db_name}'!")

            # Verify index artifacts were created
            hgdb_path = cache_db_dir / "hypergraph_chunk_entity_relation.hgdb"
            vdb_chunks = cache_db_dir / "vdb_chunks.json"
            if not hgdb_path.exists() and not vdb_chunks.exists():
                logger.warning("Index files not found at expected location after ainsert")

            # Ensure hyperrag_cache is up to date
            self._ensure_cache_link(cache_db_dir, hyperrag_link_dir)

            await notify("ready", {
                "message": f"Knowledge base '{db_name}' is ready for query!",
                "database_name": db_name,
                "records_indexed": len(canonical_records),
                "contexts_indexed": len(all_contexts),
            })

            return {
                "status": "READY",
                "database_name": db_name,
                "records_indexed": len(canonical_records),
                "contexts_indexed": len(all_contexts),
                "cache_directory": str(cache_db_dir),
                "embedding_model": EMB_MODEL,
                "embedding_dim": EMB_DIM,
            }

        except Exception as e:
            err_msg = f"Hyper-RAG indexing failed: {str(e)}"
            logger.error(err_msg, exc_info=True)
            await notify("failed", {"error": err_msg})
            raise RuntimeError(err_msg)

    def _ensure_cache_link(self, source_dir: Path, target_link: Path):
        """Ensures hyperrag_cache link or folder points to the isolated cache directory."""
        if target_link.exists():
            return
        try:
            # On Windows try directory junction
            cmd = f'cmd /c mklink /J "{target_link}" "{source_dir}"'
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if res.returncode == 0:
                logger.info(f"Created directory junction from {target_link} to {source_dir}")
            else:
                # If junction fails, create directory directly
                target_link.mkdir(parents=True, exist_ok=True)
                logger.warning(f"Junction fallback: created directory {target_link}")
        except Exception as e:
            logger.warning(f"Failed to create junction from {target_link} to {source_dir}: {e}")
            target_link.mkdir(parents=True, exist_ok=True)
