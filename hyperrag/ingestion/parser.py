"""
Generic file parser for Hyper-RAG ingestion.
Deterministically inspects and extracts raw records or document sections
from various file formats without external API calls.
"""

from __future__ import annotations

import csv
import io
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from .models import CanonicalRecord


SUPPORTED_EXTENSIONS = {
    ".json", ".jsonl", ".csv", ".txt", ".md", ".markdown", ".pdf", ".docx"
}


class GenericFileParser:
    """Parses arbitrary files into raw record dictionaries or text units."""

    def __init__(self, max_file_size_bytes: int = 50 * 1024 * 1024):
        self.max_file_size_bytes = max_file_size_bytes

    def is_supported(self, file_path_or_name: Union[str, Path]) -> bool:
        ext = Path(file_path_or_name).suffix.lower()
        return ext in SUPPORTED_EXTENSIONS

    def parse_file(
        self,
        file_path: Union[str, Path],
        original_filename: Optional[str] = None
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Parses a file and returns (format_type, list_of_raw_record_dicts).
        Each record dict contains either structured fields or {'text': ..., 'section': ...}.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        file_size = path.stat().st_size
        if file_size > self.max_file_size_bytes:
            raise ValueError(
                f"File size ({file_size / (1024*1024):.2f} MB) exceeds maximum allowed limit "
                f"({self.max_file_size_bytes / (1024*1024):.2f} MB)"
            )
        if file_size == 0:
            raise ValueError(f"File is empty: {path.name}")

        fname = original_filename or path.name
        ext = Path(fname).suffix.lower()

        if ext not in SUPPORTED_EXTENSIONS:
            supported_str = ", ".join(sorted(list(SUPPORTED_EXTENSIONS)))
            raise ValueError(
                f"Unsupported file format '{ext}'. Supported formats: {supported_str}"
            )

        if ext == ".json":
            return "json", self._parse_json(path)
        elif ext == ".jsonl":
            return "jsonl", self._parse_jsonl(path)
        elif ext == ".csv":
            return "csv", self._parse_csv(path)
        elif ext in (".txt", ".md", ".markdown"):
            return "text", self._parse_text_or_markdown(path, ext)
        elif ext == ".pdf":
            return "pdf", self._parse_pdf(path)
        elif ext == ".docx":
            return "docx", self._parse_docx(path)
        else:
            raise ValueError(f"No parser handler for extension: {ext}")

    def _parse_json(self, path: Path) -> List[Dict[str, Any]]:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                raise ValueError(f"Malformed JSON in {path.name}: {e}")

        if isinstance(data, list):
            records = []
            for idx, item in enumerate(data):
                if isinstance(item, dict):
                    records.append(item)
                else:
                    records.append({"value": item, "index": idx})
            return records

        elif isinstance(data, dict):
            # Check if this dict wraps a list of records (e.g. {"items": [...], ...})
            list_candidates = ["records", "items", "data", "results", "rows", "elements", "documents"]
            for candidate in list_candidates:
                if candidate in data and isinstance(data[candidate], list) and len(data[candidate]) > 0:
                    records = []
                    for idx, item in enumerate(data[candidate]):
                        if isinstance(item, dict):
                            records.append(item)
                        else:
                            records.append({"value": item, "index": idx})
                    return records

            # Single record object
            return [data]

        else:
            return [{"value": data}]

    def _parse_jsonl(self, path: Path) -> List[Dict[str, Any]]:
        records = []
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line_no, line in enumerate(f, start=1):
                s = line.strip()
                if not s:
                    continue
                try:
                    item = json.loads(s)
                    if isinstance(item, dict):
                        records.append(item)
                    else:
                        records.append({"value": item, "line_no": line_no})
                except json.JSONDecodeError as e:
                    raise ValueError(f"Malformed JSONL on line {line_no} in {path.name}: {e}")

        if not records:
            raise ValueError(f"No valid JSON records found in {path.name}")
        return records

    def _parse_csv(self, path: Path) -> List[Dict[str, Any]]:
        records = []
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                raise ValueError(f"Empty or headerless CSV file: {path.name}")
            for row in reader:
                # Strip keys and values
                clean_row = {
                    (k.strip() if k else f"col_{i}"): (v.strip() if v else None)
                    for i, (k, v) in enumerate(row.items())
                }
                # Skip completely empty rows
                if any(v is not None and v != "" for v in clean_row.values()):
                    records.append(clean_row)

        if not records:
            raise ValueError(f"No data rows found in CSV: {path.name}")
        return records

    def _parse_text_or_markdown(self, path: Path, ext: str) -> List[Dict[str, Any]]:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        if not content.strip():
            raise ValueError(f"Document {path.name} contains no readable text")

        # Split into meaningful sections if markdown or large text
        sections = []
        if ext in (".md", ".markdown"):
            # Split by markdown headers (#, ##, ###)
            header_pattern = re.compile(r"^(#{1,4}\s+.+)$", re.MULTILINE)
            parts = header_pattern.split(content)
            current_title = path.stem
            
            # parts will alternate: [text_before, header1, text1, header2, text2, ...]
            if len(parts) > 1:
                # First element might be intro text
                if parts[0].strip():
                    sections.append({
                        "title": f"{current_title} - Introduction",
                        "text": parts[0].strip(),
                        "section_type": "intro"
                    })
                for i in range(1, len(parts), 2):
                    header = parts[i].strip("# ").strip()
                    body = parts[i+1].strip() if i+1 < len(parts) else ""
                    if body:
                        sections.append({
                            "title": f"{current_title} - {header}",
                            "text": f"{header}\n\n{body}",
                            "section_type": "section"
                        })
            else:
                sections.append({
                    "title": current_title,
                    "text": content.strip(),
                    "section_type": "document"
                })
        else:
            # Plain text: split by double newlines or paragraph blocks if very large
            paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
            if len(paragraphs) <= 3:
                sections.append({
                    "title": path.stem,
                    "text": content.strip(),
                    "section_type": "document"
                })
            else:
                # Group paragraphs into coherent sections (~1000-2000 chars)
                chunk_buf = []
                chunk_len = 0
                sec_idx = 1
                for p in paragraphs:
                    chunk_buf.append(p)
                    chunk_len += len(p)
                    if chunk_len >= 1200:
                        sections.append({
                            "title": f"{path.stem} (Part {sec_idx})",
                            "text": "\n\n".join(chunk_buf),
                            "section_type": "part"
                        })
                        sec_idx += 1
                        chunk_buf = []
                        chunk_len = 0
                if chunk_buf:
                    sections.append({
                        "title": f"{path.stem} (Part {sec_idx})",
                        "text": "\n\n".join(chunk_buf),
                        "section_type": "part"
                    })

        return sections

    def _parse_pdf(self, path: Path) -> List[Dict[str, Any]]:
        try:
            try:
                import PyPDF2
                pdf_reader = PyPDF2.PdfReader(str(path))
            except Exception:
                import pypdf
                pdf_reader = pypdf.PdfReader(str(path))

            sections = []
            for page_idx, page in enumerate(pdf_reader.pages, start=1):
                page_text = page.extract_text() or ""
                if page_text.strip():
                    sections.append({
                        "title": f"{path.stem} - Page {page_idx}",
                        "text": page_text.strip(),
                        "page_number": page_idx,
                        "section_type": "page"
                    })

            if not sections:
                raise ValueError(f"No extractable text found in PDF: {path.name}")
            return sections

        except Exception as e:
            if isinstance(e, ValueError):
                raise
            raise ValueError(f"Failed to parse PDF {path.name}: {str(e)}")

    def _parse_docx(self, path: Path) -> List[Dict[str, Any]]:
        try:
            import docx2txt
            text = docx2txt.process(str(path))
            if not text or not text.strip():
                raise ValueError(f"No text extracted from DOCX {path.name}")

            paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
            sections = []
            if len(paragraphs) <= 3:
                sections.append({
                    "title": path.stem,
                    "text": text.strip(),
                    "section_type": "document"
                })
            else:
                chunk_buf = []
                chunk_len = 0
                sec_idx = 1
                for p in paragraphs:
                    chunk_buf.append(p)
                    chunk_len += len(p)
                    if chunk_len >= 1200:
                        sections.append({
                            "title": f"{path.stem} (Part {sec_idx})",
                            "text": "\n\n".join(chunk_buf),
                            "section_type": "part"
                        })
                        sec_idx += 1
                        chunk_buf = []
                        chunk_len = 0
                if chunk_buf:
                    sections.append({
                        "title": f"{path.stem} (Part {sec_idx})",
                        "text": "\n\n".join(chunk_buf),
                        "section_type": "part"
                    })

            return sections

        except Exception as e:
            if isinstance(e, ValueError):
                raise
            raise ValueError(f"Failed to parse DOCX {path.name}: {str(e)}")
