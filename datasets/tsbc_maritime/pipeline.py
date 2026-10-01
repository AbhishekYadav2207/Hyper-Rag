"""
TSBC Maritime Pipeline Integration for Hyper-RAG.

Provides deterministic local preprocessing, normalization, deduplication,
context generation, dry-run estimation, and isolated Hyper-RAG indexing.
MAXIMIZES local offline processing; enforces strict API safety limits.
"""

from __future__ import annotations

import argparse
import copy
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Setup logging
logger = logging.getLogger("tsbc_pipeline")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Root resolution
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SOURCE_CORPUS_PATH = Path(os.getenv("TSBC_CORPUS_PATH", PROJECT_ROOT / "datasets" / "external" / "maritime_corpus.jsonl"))

# Safety guard defaults
DEFAULT_MAX_RECORDS = 1
DEFAULT_MAX_CONTEXTS = 5
ISOLATED_CACHE_DIR = PROJECT_ROOT / "caches" / "tsbc_maritime_test"
HYPERRAG_CACHE_LINK = PROJECT_ROOT / "hyperrag_cache" / "tsbc_maritime_test"


class TSBCRecordNormalizer:
    """
    Deterministic normalization and deduplication layer for TSBC maritime records.
    Never calls external APIs; strictly preserves provenance and original facts.
    """

    @staticmethod
    def deduplicate_equipment(items: List[Dict[str, Any]], key_fields: List[str]) -> List[Dict[str, Any]]:
        """Deduplicate nested equipment entries by unique key combinations."""
        seen = set()
        deduped = []
        for item in items:
            key = tuple(str(item.get(k, "")).strip().lower() for k in key_fields)
            if key not in seen:
                seen.add(key)
                deduped.append(item)
        return deduped

    @classmethod
    def normalize_occurrence(cls, raw_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Normalize raw corpus rows for a single occurrence ID into a canonical structure.
        Deduplicates nested items and merges available perspectives.
        """
        if not raw_records:
            raise ValueError("No raw records provided for normalization")

        first = raw_records[0]
        occ_id = first.get("occurrence_id")
        structured = first.get("structured", {})
        occ_raw = structured.get("occurrence", {})
        vessels_raw = structured.get("vessels", [])
        vessel_raw = vessels_raw[0] if vessels_raw else {}

        # 1. Occurrence metadata
        occurrence_meta = {
            "occurrence_id": occ_id,
            "occurrence_number": occ_raw.get("OccNo"),
            "occurrence_class": occ_raw.get("OccClassDisplayEng"),
            "occurrence_type": occ_raw.get("OccTypeDisplayEng"),
            "incident_type": occ_raw.get("AccIncTypeDisplayEng"),
            "date": occ_raw.get("OccDate"),
            "time": occ_raw.get("OccTime"),
            "timezone": occ_raw.get("TimeZoneDisplayEng"),
            "summary": (occ_raw.get("Summary") or "").strip(),
            "region": occ_raw.get("RegionOfOccurrenceDisplayEng") or occ_raw.get("RegionResponsibilityDisplayEng"),
            "area_type": occ_raw.get("AreaTypeDisplayEng"),
        }

        # 2. Location
        location = {
            "nearest_location": occ_raw.get("NearestLocationDescription"),
            "latitude": occ_raw.get("Latitude"),
            "lat_bearing": occ_raw.get("LatEnum_Bearing_DisplayEng"),
            "longitude": occ_raw.get("Longitude"),
            "long_bearing": occ_raw.get("LongEnum_Bearing_DisplayEng"),
        }

        # 3. Environment
        environment = {
            "weather_condition": occ_raw.get("WeatherConditionDisplayEng"),
            "sea_state": occ_raw.get("SeaStateDisplayEng"),
            "wind_direction_id": occ_raw.get("WindDirectionID"),
            "wind_speed_type": occ_raw.get("WindSpeedTypeDisplayEng"),
            "light_condition": occ_raw.get("LightConditionDisplayEng"),
        }

        # 4. Vessel details
        vessel = {
            "vessel_id": vessel_raw.get("VesselID"),
            "vessel_name": vessel_raw.get("VesselName"),
            "official_no": vessel_raw.get("OfficialNo"),
            "vessel_type": vessel_raw.get("VesselTypeDisplayEng"),
            "vessel_subtype": vessel_raw.get("VesselSubTypeDisplayEng"),
            "flag": vessel_raw.get("VesselFlagDisplayEng"),
            "port_of_registry": vessel_raw.get("PortOfRegistryDisplayEng"),
            "gross_tonnage": vessel_raw.get("GrossTonnage"),
            "propulsion_type": vessel_raw.get("PropulsionTypeDisplayEng"),
            "hull_material": vessel_raw.get("HullMaterialDisplayEng"),
            "departure_port": vessel_raw.get("DeparturePortDisplayEng"),
            "departure_country": vessel_raw.get("DepartureCountryDisplayEng"),
            "destination_port": vessel_raw.get("DestinationPortDisplayEng"),
            "destination_country": vessel_raw.get("DestinationCountryDisplayEng"),
            "activity_type": vessel_raw.get("ActivityTypeDisplayEng"),
        }

        # 5. Damage and Safety
        damage_safety = {
            "damage_indicator": occ_raw.get("DamageIND_DisplayEng"),
            "vessel_damage_category": vessel_raw.get("VesselDamageLocationCategoryDisplayEng"),
            "vessel_damage_subcategory": vessel_raw.get("VesselDamageLocationSubCategoryDisplayEng"),
            "vessel_damage_location": vessel_raw.get("VesselDamageLocationDisplayEng"),
            "vessel_damage_degree": vessel_raw.get("VesselDamageDegreeDisplayEng"),
            "search_and_rescue_indicator": occ_raw.get("SearchAndRescueIND_DisplayEng"),
            "total_deaths": occ_raw.get("TotalDeaths", 0),
            "total_serious_injuries": occ_raw.get("TotalSeriousInjuries", 0),
            "total_minor_injuries": occ_raw.get("TotalMinorInjuries", 0),
            "total_missing": occ_raw.get("TotalMissingIndividuals", 0),
        }

        # 6. Equipment (deduplicated)
        raw_lsa = vessel_raw.get("lsa_equipment") or []
        deduped_lsa = cls.deduplicate_equipment(
            raw_lsa, ["LsApplianceDisplayEng", "UsedEnumDisplayEng", "ApprovedEnumDisplayEng"]
        )
        lsa_cleaned = [
            {
                "appliance": item.get("LsApplianceDisplayEng"),
                "used": item.get("UsedEnumDisplayEng"),
                "approved": item.get("ApprovedEnumDisplayEng"),
            }
            for item in deduped_lsa
            if item.get("LsApplianceDisplayEng")
        ]

        raw_nav = vessel_raw.get("navigation_equipment") or []
        deduped_nav = cls.deduplicate_equipment(
            raw_nav, ["NavigationAidTypeDisplayEng", "NavigationAidSubTypeDisplayEng", "OnOffEnumDisplayEng"]
        )
        nav_cleaned = [
            {
                "aid_type": item.get("NavigationAidTypeDisplayEng"),
                "subtype": item.get("NavigationAidSubTypeDisplayEng"),
                "status": item.get("OnOffEnumDisplayEng"),
            }
            for item in deduped_nav
            if item.get("NavigationAidTypeDisplayEng")
        ]

        equipment = {
            "life_saving_appliances": lsa_cleaned,
            "navigation_equipment": nav_cleaned,
        }

        # 7. Collect narratives from corpus rows
        narratives = []
        for r in raw_records:
            doc_text = (r.get("document") or "").strip()
            if doc_text and doc_text not in narratives:
                narratives.append(doc_text)

        # 8. Provenance
        provenance = {
            "source_file": str(SOURCE_CORPUS_PATH),
            "occurrence_id": occ_id,
            "vessel_identifier": vessel.get("vessel_name"),
            "vessel_id": vessel.get("vessel_id"),
            "source_records_count": len(raw_records),
            "source_perspectives": [r.get("provenance", {}).get("perspective") for r in raw_records],
        }

        return {
            "provenance": provenance,
            "occurrence": occurrence_meta,
            "location": location,
            "environment": environment,
            "vessel": vessel,
            "damage_and_safety": damage_safety,
            "equipment": equipment,
            "narratives": narratives,
        }


class TSBCContextGenerator:
    """
    Converts normalized TSBC occurrence records into deterministic,
    Hyper-RAG-compatible text contexts.
    Never infers missing fields or calls an LLM.
    """

    @classmethod
    def generate_contexts(cls, normalized: Dict[str, Any]) -> List[Dict[str, Any]]:
        contexts = []
        occ_id = normalized["occurrence"]["occurrence_id"]
        vessel_name = normalized["vessel"].get("vessel_name") or "Unknown Vessel"
        source_file = normalized["provenance"]["source_file"]

        # Context 1: Occurrence Overview
        occ = normalized["occurrence"]
        loc = normalized["location"]
        coords_str = ""
        if loc.get("latitude") is not None and loc.get("longitude") is not None:
            coords_str = f"Coordinates: {loc.get('latitude')} {loc.get('lat_bearing') or ''}, {loc.get('longitude')} {loc.get('long_bearing') or ''}".strip()
        loc_desc = loc.get("nearest_location") or "Unavailable"
        date_str = occ.get("date") or "Unavailable"
        time_str = f"{occ.get('time') or ''} {occ.get('timezone') or ''}".strip() or "Unavailable"
        inc_type = occ.get("incident_type") or "Unavailable"
        occ_class = occ.get("occurrence_class") or "Unavailable"
        region = occ.get("region") or "Unavailable"
        summary = occ.get("summary") or "No narrative summary recorded."

        overview_text = (
            f"TSBC Maritime Occurrence {occ_id} Overview:\n"
            f"- Occurrence ID: {occ_id} (Number: {occ.get('occurrence_number')})\n"
            f"- Vessel Involved: {vessel_name}\n"
            f"- Date and Time: {date_str} {time_str}\n"
            f"- Incident Type: {inc_type} (Classification: {occ_class})\n"
            f"- Region: {region}\n"
            f"- Geographic Location: {loc_desc} ({coords_str})\n"
            f"- Incident Summary: {summary}"
        )
        contexts.append({
            "context_id": f"tsbc_{occ_id}_overview",
            "context_type": "occurrence_overview",
            "occurrence_id": occ_id,
            "vessel_identifier": vessel_name,
            "source_file": source_file,
            "text": overview_text,
        })

        # Context 2: Vessel Profile
        v = normalized["vessel"]
        v_parts = [
            f"TSBC Maritime Occurrence {occ_id} Vessel Profile:",
            f"- Vessel Name: {v.get('vessel_name') or 'Unavailable'}",
            f"- Official Number: {v.get('official_no') or 'Unavailable'}",
            f"- Vessel Flag: {v.get('flag') or 'Unavailable'}",
            f"- Port of Registry: {v.get('port_of_registry') or 'Unavailable'}",
            f"- Vessel Type: {v.get('vessel_type') or 'Unavailable'} (Subtype: {v.get('vessel_subtype') or 'Unavailable'})",
            f"- Gross Tonnage: {v.get('gross_tonnage') or 'Unavailable'} GT",
            f"- Propulsion Type: {v.get('propulsion_type') or 'Unavailable'}",
            f"- Hull Material: {v.get('hull_material') or 'Unavailable'}",
            f"- Departure Port: {v.get('departure_port') or 'Unavailable'}, {v.get('departure_country') or ''}".strip(" ,"),
            f"- Destination Port: {v.get('destination_port') or 'Unavailable'}, {v.get('destination_country') or ''}".strip(" ,"),
        ]
        contexts.append({
            "context_id": f"tsbc_{occ_id}_vessel",
            "context_type": "vessel_profile",
            "occurrence_id": occ_id,
            "vessel_identifier": vessel_name,
            "source_file": source_file,
            "text": "\n".join(v_parts),
        })

        # Context 3: Environmental Conditions
        env = normalized["environment"]
        env_parts = [
            f"TSBC Maritime Occurrence {occ_id} Environmental Conditions:",
            f"- Weather Condition: {env.get('weather_condition') or 'Unavailable'}",
            f"- Sea State: {env.get('sea_state') or 'Unavailable'}",
            f"- Light Condition: {env.get('light_condition') or 'Unavailable'}",
            f"- Wind Information: Speed Type: {env.get('wind_speed_type') or 'Unavailable'}, Direction ID: {env.get('wind_direction_id') or 'Unavailable'}",
        ]
        contexts.append({
            "context_id": f"tsbc_{occ_id}_environment",
            "context_type": "environmental_conditions",
            "occurrence_id": occ_id,
            "vessel_identifier": vessel_name,
            "source_file": source_file,
            "text": "\n".join(env_parts),
        })

        # Context 4: Damage and Safety
        ds = normalized["damage_and_safety"]
        ds_parts = [
            f"TSBC Maritime Occurrence {occ_id} Damage and Safety:",
            f"- Damage Reported: {ds.get('damage_indicator') or 'Unavailable'}",
            f"- Damage Location: {ds.get('vessel_damage_location') or 'Unavailable'} (Category: {ds.get('vessel_damage_category') or 'Unavailable'}, Subcategory: {ds.get('vessel_damage_subcategory') or 'Unavailable'})",
            f"- Damage Degree: {ds.get('vessel_damage_degree') or 'Unavailable'}",
            f"- Search and Rescue (SAR) Deployment: {ds.get('search_and_rescue_indicator') or 'Unavailable'}",
            f"- Fatalities: {ds.get('total_deaths')}",
            f"- Serious Injuries: {ds.get('total_serious_injuries')}",
            f"- Minor Injuries: {ds.get('total_minor_injuries')}",
            f"- Missing Individuals: {ds.get('total_missing')}",
        ]
        contexts.append({
            "context_id": f"tsbc_{occ_id}_damage_safety",
            "context_type": "damage_and_safety",
            "occurrence_id": occ_id,
            "vessel_identifier": vessel_name,
            "source_file": source_file,
            "text": "\n".join(ds_parts),
        })

        # Context 5: Equipment Profile
        eq = normalized["equipment"]
        eq_parts = [f"TSBC Maritime Occurrence {occ_id} Equipment Profile:"]
        
        # Navigation
        nav_items = eq.get("navigation_equipment") or []
        if nav_items:
            eq_parts.append("- Navigation Equipment:")
            for item in nav_items:
                status = item.get("status") or "Recorded"
                eq_parts.append(f"  * {item.get('aid_type')} (Status: {status})")
        else:
            eq_parts.append("- Navigation Equipment: None recorded")

        # Life saving
        lsa_items = eq.get("life_saving_appliances") or []
        if lsa_items:
            eq_parts.append("- Life-Saving Appliances (LSA):")
            for item in lsa_items:
                used = f", Used: {item.get('used')}" if item.get("used") else ""
                eq_parts.append(f"  * {item.get('appliance')}{used}")
        else:
            eq_parts.append("- Life-Saving Appliances: None recorded")

        contexts.append({
            "context_id": f"tsbc_{occ_id}_equipment",
            "context_type": "equipment_profile",
            "occurrence_id": occ_id,
            "vessel_identifier": vessel_name,
            "source_file": source_file,
            "text": "\n".join(eq_parts),
        })

        return contexts


class TSBCPipeline:
    """
    Orchestrates dataset extraction, normalization, dry-run estimation,
    and isolated indexing with strict API quotas.
    """

    def __init__(
        self,
        dataset_name: str = "tsbc_maritime_test_1",
        cache_dir: Optional[Path] = None,
        max_records: int = DEFAULT_MAX_RECORDS,
        max_contexts: int = DEFAULT_MAX_CONTEXTS,
    ):
        self.dataset_name = dataset_name
        self.max_records = max_records
        self.max_contexts = max_contexts
        
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            if self.dataset_name == "tsbc_maritime_test_1":
                self.cache_dir = PROJECT_ROOT / "caches" / "tsbc_maritime_test"
            else:
                self.cache_dir = PROJECT_ROOT / "caches" / self.dataset_name

        self.hyperrag_cache_link = PROJECT_ROOT / "hyperrag_cache" / (
            "tsbc_maritime_test" if self.dataset_name == "tsbc_maritime_test_1" else self.dataset_name
        )

        self.dataset_dir = PROJECT_ROOT / "datasets" / "tsbc_maritime"
        self.raw_dir = self.dataset_dir / "raw_reference"
        self.norm_dir = self.dataset_dir / "normalized"
        self.ctx_dir = self.dataset_dir / "contexts"
        self.rep_dir = self.dataset_dir / "reports"

        for d in [self.raw_dir, self.norm_dir, self.ctx_dir, self.rep_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def select_and_extract_raw(self, target_ids: List[int]) -> Path:
        """
        Deterministically extract the raw rows for the specified occurrence IDs
        directly from the source corpus without modifying the source corpus.
        """
        if not SOURCE_CORPUS_PATH.exists():
            raise FileNotFoundError(f"Source corpus not found at {SOURCE_CORPUS_PATH}")

        output_path = self.raw_dir / f"{self.dataset_name}.jsonl"
        target_set = set(target_ids)
        extracted_rows = []

        logger.info(f"Extracting {len(target_ids)} target occurrence(s) {target_ids} from {SOURCE_CORPUS_PATH}...")
        with open(SOURCE_CORPUS_PATH, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if not stripped:
                    continue
                data = json.loads(stripped)
                if data.get("occurrence_id") in target_set:
                    extracted_rows.append(stripped)

        with open(output_path, "w", encoding="utf-8") as f:
            for row in extracted_rows:
                f.write(row + "\n")

        logger.info(f"Saved {len(extracted_rows)} raw records to {output_path}")
        return output_path

    def process_normalization(self, raw_path: Path) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Normalize raw lines and generate deterministic contexts."""
        records_by_occ = {}
        with open(raw_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                data = json.loads(line)
                occ_id = data.get("occurrence_id")
                records_by_occ.setdefault(occ_id, []).append(data)

        # Enforce safety limits
        if len(records_by_occ) > self.max_records:
            raise ValueError(
                f"SAFETY GUARD TRIGGERED: Dataset has {len(records_by_occ)} occurrences, "
                f"exceeding max_records={self.max_records}"
            )

        normalized_list = []
        all_contexts = []
        for occ_id, rows in records_by_occ.items():
            norm = TSBCRecordNormalizer.normalize_occurrence(rows)
            normalized_list.append(norm)
            ctxs = TSBCContextGenerator.generate_contexts(norm)
            all_contexts.extend(ctxs)

        if len(all_contexts) > self.max_contexts:
            raise ValueError(
                f"SAFETY GUARD TRIGGERED: Generated {len(all_contexts)} contexts, "
                f"exceeding max_contexts={self.max_contexts}"
            )

        # Save normalized records
        norm_file = self.norm_dir / f"{self.dataset_name}_normalized.json"
        with open(norm_file, "w", encoding="utf-8") as f:
            json.dump(normalized_list, f, indent=2, ensure_ascii=False)

        # Save contexts
        ctx_file = self.ctx_dir / f"{self.dataset_name}_contexts.json"
        with open(ctx_file, "w", encoding="utf-8") as f:
            json.dump(all_contexts, f, indent=2, ensure_ascii=False)

        logger.info(f"Normalized {len(normalized_list)} occurrence(s), generated {len(all_contexts)} context(s)")
        return normalized_list, all_contexts

    def dry_run(self, raw_path: Path) -> Dict[str, Any]:
        """
        Execute dry-run estimation.
        NO external API calls are made.
        """
        from my_config import EMB_MODEL, EMB_DIM, OPENROUTER_MODEL

        normalized_list, all_contexts = self.process_normalization(raw_path)

        # Text chunk estimation
        total_chars = sum(len(c["text"]) for c in all_contexts)
        estimated_chunks = max(1, (total_chars // 1000) + 1)
        estimated_embeddings = estimated_chunks
        estimated_llm_calls = estimated_chunks * 2  # ~1-2 extraction passes

        report = {
            "status": "DRY_RUN_SUCCESS",
            "dataset_name": self.dataset_name,
            "raw_dataset_path": str(raw_path),
            "occurrences_discovered": len(normalized_list),
            "occurrences_selected": len(normalized_list),
            "contexts_generated": len(all_contexts),
            "total_character_count": total_chars,
            "estimated_text_chunks": estimated_chunks,
            "estimated_embedding_calls": estimated_embeddings,
            "estimated_llm_calls": estimated_llm_calls,
            "external_api_calls_made": 0,
            "output_index_location": str(self.cache_dir),
            "embedding_model": EMB_MODEL,
            "embedding_dimension": EMB_DIM,
            "llm_model": OPENROUTER_MODEL,
            "max_records_limit": self.max_records,
            "max_contexts_limit": self.max_contexts,
        }

        # Save report
        report_file = self.rep_dir / f"{self.dataset_name}_dry_run_report.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        logger.info("=" * 60)
        logger.info("DRY-RUN ESTIMATION REPORT (ZERO API CALLS MADE)")
        logger.info("=" * 60)
        for k, v in report.items():
            logger.info(f"  {k}: {v}")
        logger.info("=" * 60)

        return report

    def index_isolated(self, raw_path: Path) -> Dict[str, Any]:
        """
        Index the dataset into an isolated working directory.
        Strictly enforces the 1-record limit before making any API calls.
        """
        from my_config import EMB_MODEL, EMB_DIM, EMB_BASE_URL, EMB_API_KEY
        from hyperrag import HyperRAG
        from hyperrag.utils import EmbeddingFunc
        from hyperrag.llm import openai_embedding, openrouter_mistral_complete_if_cache

        logger.info(f"Preparing isolated index for dataset: {self.dataset_name}")
        normalized_list, all_contexts = self.process_normalization(raw_path)

        if len(normalized_list) > self.max_records:
            raise RuntimeError(
                f"SAFETY GUARD: Refusing to index {len(normalized_list)} records (limit={self.max_records})"
            )

        # Ensure cache directory exists and is strictly isolated
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Using isolated working directory: {self.cache_dir}")

        async def llm_func(prompt, system_prompt=None, history_messages=None, **kwargs):
            return await openrouter_mistral_complete_if_cache(
                prompt,
                system_prompt=system_prompt,
                history_messages=history_messages or [],
                **kwargs,
            )

        async def emb_func(texts: list[str]):
            return await openai_embedding(
                texts,
                model=EMB_MODEL,
                api_key=EMB_API_KEY,
                base_url=EMB_BASE_URL,
            )

        rag = HyperRAG(
            working_dir=str(self.cache_dir),
            llm_model_func=llm_func,
            embedding_func=EmbeddingFunc(
                embedding_dim=EMB_DIM,
                max_token_size=8192,
                func=emb_func,
            ),
        )

        # Prepare document context texts
        # Combine contexts into a clean structured document
        document_texts = [c["text"] for c in all_contexts]
        combined_doc = "\n\n---\n\n".join(document_texts)

        logger.info(f"Starting HyperRAG insertion for {len(all_contexts)} contexts ({len(combined_doc)} chars)...")
        rag.insert(combined_doc)
        logger.info("HyperRAG insertion completed successfully!")

        # Create/ensure symlink or junction in hyperrag_cache so WebUI / db_manager discovers it
        self._ensure_hyperrag_cache_link()

        return {
            "status": "INDEX_SUCCESS",
            "working_dir": str(self.cache_dir),
            "contexts_indexed": len(all_contexts),
            "embedding_model": EMB_MODEL,
            "embedding_dim": EMB_DIM,
        }

    def _ensure_hyperrag_cache_link(self):
        """Ensure hyperrag_cache link points to isolated cache."""
        try:
            if not self.hyperrag_cache_link.exists():
                # On Windows, try directory junction or symbolic link
                import subprocess
                cmd = f'cmd /c mklink /J "{self.hyperrag_cache_link}" "{self.cache_dir}"'
                res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                if res.returncode == 0:
                    logger.info(f"Created directory junction from {self.hyperrag_cache_link} to {self.cache_dir}")
                else:
                    logger.warning(f"Could not create junction, copying files or fallback: {res.stderr}")
        except Exception as e:
            logger.warning(f"Failed to link to hyperrag_cache: {e}")


def main():
    parser = argparse.ArgumentParser(description="TSBC Maritime Integration Pipeline")
    parser.add_argument("--dataset", type=str, default="tsbc_maritime_test_1", help="Dataset name")
    parser.add_argument("--dry-run", action="store_true", help="Run dry run without API calls")
    parser.add_argument("--index", action="store_true", help="Perform isolated Hyper-RAG indexing")
    parser.add_argument("--max-records", type=int, default=1, help="Max records allowed (default: 1)")
    parser.add_argument("--max-contexts", type=int, default=5, help="Max contexts allowed (default: 5)")
    args = parser.parse_args()

    pipeline = TSBCPipeline(
        dataset_name=args.dataset,
        max_records=args.max_records,
        max_contexts=args.max_contexts,
    )

    # Deterministic occurrence selection:
    # tsbc_maritime_test_1 -> [4]
    # tsbc_maritime_test_3 -> [4, 48, 205]
    if args.dataset == "tsbc_maritime_test_1":
        target_ids = [4]
    elif args.dataset == "tsbc_maritime_test_3":
        target_ids = [4, 48, 205]
    else:
        target_ids = [4]

    raw_path = pipeline.select_and_extract_raw(target_ids)

    if args.dry_run:
        pipeline.dry_run(raw_path)
    elif args.index:
        pipeline.index_isolated(raw_path)
    else:
        # Default is dry-run for safety
        pipeline.dry_run(raw_path)


if __name__ == "__main__":
    main()
