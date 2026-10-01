"""
Unit and integration tests for Generic Hyper-RAG Ingestion Pipeline.
All tests run 100% locally with zero external API calls.
"""

import json
import tempfile
from pathlib import Path
import pytest

from hyperrag.ingestion.models import IngestionConfig, CanonicalRecord
from hyperrag.ingestion.parser import GenericFileParser, SUPPORTED_EXTENSIONS
from hyperrag.ingestion.schema_infer import AutomaticSchemaInferer
from hyperrag.ingestion.normalizer import GenericNormalizer
from hyperrag.ingestion.context_builder import GenericContextBuilder
from hyperrag.ingestion.pipeline import GenericIngestionPipeline, sanitize_database_name


def test_supported_extensions():
    parser = GenericFileParser()
    for ext in [".json", ".jsonl", ".csv", ".txt", ".md", ".pdf", ".docx"]:
        assert parser.is_supported(f"test{ext}")
    assert not parser.is_supported("test.exe")
    assert not parser.is_supported("test.xlsx")


def test_sanitize_database_name():
    assert sanitize_database_name("My Dataset 2026! @#$") == "my_dataset_2026"
    assert sanitize_database_name("employee-records_v1") == "employee-records_v1"
    # Core databases are protected
    assert sanitize_database_name("mock").startswith("mock_custom_")
    assert sanitize_database_name("tsbc_maritime_test").startswith("tsbc_maritime_test_custom_")
    assert sanitize_database_name("") != ""


def test_parse_json_list():
    parser = GenericFileParser()
    data = [
        {"id": "1", "name": "Item A", "price": 10},
        {"id": "2", "name": "Item B", "price": 20},
    ]
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(data, f)
        temp_name = f.name
    try:
        fmt, records = parser.parse_file(temp_name)
        assert fmt == "json"
        assert len(records) == 2
        assert records[0]["name"] == "Item A"
    finally:
        Path(temp_name).unlink()


def test_parse_json_single_record():
    parser = GenericFileParser()
    data = {"id": "100", "title": "Single Doc", "body": "Hello world"}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(data, f)
        temp_name = f.name
    try:
        fmt, records = parser.parse_file(temp_name)
        assert fmt == "json"
        assert len(records) == 1
        assert records[0]["title"] == "Single Doc"
    finally:
        Path(temp_name).unlink()


def test_parse_json_wrapped_records():
    parser = GenericFileParser()
    data = {
        "status": "success",
        "records": [
            {"id": "R1", "val": "A"},
            {"id": "R2", "val": "B"}
        ]
    }
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(data, f)
        temp_name = f.name
    try:
        fmt, records = parser.parse_file(temp_name)
        assert fmt == "json"
        assert len(records) == 2
        assert records[1]["id"] == "R2"
    finally:
        Path(temp_name).unlink()


def test_parse_jsonl():
    parser = GenericFileParser()
    lines = [
        json.dumps({"occ_id": 10, "desc": "Event Alpha"}),
        json.dumps({"occ_id": 20, "desc": "Event Beta"}),
    ]
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
        f.write("\n".join(lines))
        temp_name = f.name
    try:
        fmt, records = parser.parse_file(temp_name)
        assert fmt == "jsonl"
        assert len(records) == 2
        assert records[0]["occ_id"] == 10
    finally:
        Path(temp_name).unlink()


def test_parse_csv():
    parser = GenericFileParser()
    csv_content = "emp_id,emp_name,department\nE1,Alice,Engineering\nE2,Bob,Finance\n"
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write(csv_content)
        temp_name = f.name
    try:
        fmt, records = parser.parse_file(temp_name)
        assert fmt == "csv"
        assert len(records) == 2
        assert records[0]["emp_name"] == "Alice"
        assert records[1]["department"] == "Finance"
    finally:
        Path(temp_name).unlink()


def test_parse_markdown():
    parser = GenericFileParser()
    md_content = "# Project Overview\n\nThis is the overview.\n\n## Section 1\n\nDetails about section 1.\n"
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(md_content)
        temp_name = f.name
    try:
        fmt, sections = parser.parse_file(temp_name)
        assert fmt == "text"
        assert len(sections) >= 1
    finally:
        Path(temp_name).unlink()


def test_error_on_empty_file():
    parser = GenericFileParser()
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        temp_name = f.name
    try:
        with pytest.raises(ValueError, match="empty"):
            parser.parse_file(temp_name)
    finally:
        Path(temp_name).unlink()


def test_error_on_malformed_json():
    parser = GenericFileParser()
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        f.write("{invalid json content")
        temp_name = f.name
    try:
        with pytest.raises(ValueError, match="Malformed JSON"):
            parser.parse_file(temp_name)
    finally:
        Path(temp_name).unlink()


def test_error_on_unsupported_file():
    parser = GenericFileParser()
    with tempfile.NamedTemporaryFile("w", suffix=".exe", delete=False, encoding="utf-8") as f:
        f.write("binary")
        temp_name = f.name
    try:
        with pytest.raises(ValueError, match="Unsupported file format"):
            parser.parse_file(temp_name)
    finally:
        Path(temp_name).unlink()


def test_schema_inference_and_normalization():
    records = [
        {
            "user_id": "U-1",
            "full_name": "Test User",
            "role": "Admin",
            "bio": "A long narrative biography that describes the background of the user in great detail.",
            "skills": ["Python", "Python", "Docker"],  # Duplicate item in list
            "tags": None  # Null field
        }
    ]
    schema = AutomaticSchemaInferer.infer_schema(records)
    assert "user_id" in schema.identifier_fields
    assert "full_name" in schema.title_fields
    assert "bio" in schema.narrative_fields

    canonical = GenericNormalizer.normalize_records(records, "test.json", "json", schema)
    assert len(canonical) == 1
    rec = canonical[0]
    assert rec.record_id == "U-1"
    assert rec.primary_title == "Test User"
    # Deduplication of list
    assert rec.structured_data["skills"] == ["Python", "Docker"]
    # Null removal
    assert "tags" not in rec.structured_data

    contexts = GenericContextBuilder.generate_contexts_for_record(rec, schema)
    assert len(contexts) >= 2
    context_text = "\n".join(c.text for c in contexts)
    assert "Test User" in context_text
    assert "U-1" in context_text
    assert "Python" in context_text


def test_preflight_inspection():
    pipeline = GenericIngestionPipeline(IngestionConfig(dry_run=True))
    report = pipeline.preflight_inspect("datasets/demo/employee_projects.json")
    assert report.is_supported is True
    assert report.record_count == 3
    assert report.estimated_contexts > 0
    assert report.suggested_database_name == "employee_projects"
    assert report.schema is not None
    assert "employee_id" in report.schema.identifier_fields
    assert report.error_message is None
