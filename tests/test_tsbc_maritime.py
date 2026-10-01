"""
Comprehensive local offline unit tests for the TSBC Maritime Integration.
Runs with ZERO external API calls / credentials.
Covers Levels 0 through 3, safety limits, and all data edge cases.
"""

import copy
import json
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from datasets.tsbc_maritime.pipeline import (
    TSBCRecordNormalizer,
    TSBCContextGenerator,
    TSBCPipeline,
)

SAMPLE_RAW_RECORD_1 = {
    "occurrence_id": 4,
    "document": "CREW RESCUED VESSEL TOWED TO HALIFAX AFTER FIRE IN ENGINE ROOM.",
    "provenance": {
        "perspective": "occurrence_summary",
        "pattern_id": "raw_tsb_summary",
        "spans": [{"rendered_span": "CREW RESCUED", "category": "narrative"}],
    },
    "structured": {
        "occurrence_id": 4,
        "occurrence": {
            "OccID": 4,
            "OccNo": "4",
            "OccClassDisplayEng": "FACT-FINDING",
            "OccDate": "1975-01-08 00:00:00.0000000",
            "OccTime": "19:00:00",
            "TimeZoneDisplayEng": "UTC",
            "OccTypeDisplayEng": "Accident",
            "AccIncTypeDisplayEng": "EXPLOSION",
            "Summary": "CREW RESCUED VESSEL TOWED TO HALIFAX AFTER FIRE IN ENGINE ROOM.",
            "SearchAndRescueIND_DisplayEng": "Yes",
            "DamageIND_DisplayEng": "Yes",
            "NearestLocationDescription": "ST LAWRENCE-GULF OF-RIVIERE AU RENARD-PRET DE",
            "Latitude": 49.0,
            "LatEnum_Bearing_DisplayEng": "N",
            "Longitude": 64.16666667,
            "LongEnum_Bearing_DisplayEng": "W",
            "RegionOfOccurrenceDisplayEng": "LAURENTIAN REGION",
            "WeatherConditionDisplayEng": "CLEAR",
            "SeaStateDisplayEng": "CALM (GLASSY) - 0 meters",
            "WindDirectionID": 3.0,
            "WindSpeedTypeDisplayEng": "Wind Speed",
            "TotalDeaths": 0,
            "TotalMinorInjuries": 0,
            "TotalSeriousInjuries": 0,
            "TotalMissingIndividuals": 0,
        },
        "vessels": [
            {
                "VesselID": 5,
                "OccNo": "4",
                "OccID": 4,
                "VesselName": "ANVOURGON",
                "OfficialNo": "4305",
                "VesselTypeDisplayEng": "CARGO - SOLID",
                "VesselSubTypeDisplayEng": "GENERAL CARGO",
                "VesselFlagDisplayEng": "GREECE",
                "PortOfRegistryDisplayEng": "Piraeus",
                "GrossTonnage": 7266.0,
                "PropulsionTypeDisplayEng": "PROPELLER",
                "HullMaterialDisplayEng": "STEEL",
                "DepartureCountryDisplayEng": "CANADA",
                "DeparturePortDisplayEng": "QUEBEC",
                "DestinationCountryDisplayEng": "CANADA",
                "DestinationPortDisplayEng": "QUEBEC",
                "VesselDamageLocationCategoryDisplayEng": "Hull",
                "VesselDamageLocationSubCategoryDisplayEng": "Engineering Spaces",
                "VesselDamageLocationDisplayEng": "Engine room",
                "VesselDamageDegreeDisplayEng": "MAJOR",
                "injuries": [],
                "lsa_equipment": [
                    {
                        "LsApplianceDisplayEng": "Lifeboat",
                        "UsedEnumDisplayEng": "No",
                        "ApprovedEnumDisplayEng": None,
                    },
                    {
                        # Duplicate entry to test deduplication
                        "LsApplianceDisplayEng": "Lifeboat",
                        "UsedEnumDisplayEng": "No",
                        "ApprovedEnumDisplayEng": None,
                    },
                ],
                "navigation_equipment": [
                    {
                        "NavigationAidTypeDisplayEng": "Magnetic compass",
                        "NavigationAidSubTypeDisplayEng": None,
                        "OnOffEnumDisplayEng": "On",
                    },
                    {
                        # Duplicate entry
                        "NavigationAidTypeDisplayEng": "Magnetic compass",
                        "NavigationAidSubTypeDisplayEng": None,
                        "OnOffEnumDisplayEng": "On",
                    },
                ],
            }
        ],
    },
}

SAMPLE_RAW_RECORD_PERSPECTIVE_2 = {
    "occurrence_id": 4,
    "document": "During maritime operations, the CARGO - SOLID 'ANVOURGON' suffered an engine room explosion.",
    "provenance": {
        "perspective": "vessel_consolidated_narrative",
        "pattern_id": "op_family_e_activity_focus",
    },
    "structured": SAMPLE_RAW_RECORD_1["structured"],
}


class TestTSBCNormalization:
    """Level 1 & Deduplication tests."""

    def test_normalization_basic(self):
        norm = TSBCRecordNormalizer.normalize_occurrence([SAMPLE_RAW_RECORD_1])
        assert norm["occurrence"]["occurrence_id"] == 4
        assert norm["vessel"]["vessel_name"] == "ANVOURGON"
        assert norm["vessel"]["official_no"] == "4305"
        assert norm["vessel"]["flag"] == "GREECE"
        assert norm["damage_and_safety"]["vessel_damage_degree"] == "MAJOR"
        assert norm["damage_and_safety"]["total_deaths"] == 0

    def test_deduplication_equipment(self):
        norm = TSBCRecordNormalizer.normalize_occurrence([SAMPLE_RAW_RECORD_1])
        # Two lifeboat entries existed in raw data -> should be deduplicated to exactly 1
        lsa = norm["equipment"]["life_saving_appliances"]
        assert len(lsa) == 1
        assert lsa[0]["appliance"] == "Lifeboat"

        # Two magnetic compass entries -> deduplicated to 1
        nav = norm["equipment"]["navigation_equipment"]
        assert len(nav) == 1
        assert nav[0]["aid_type"] == "Magnetic compass"

    def test_multi_perspective_merging(self):
        norm = TSBCRecordNormalizer.normalize_occurrence([SAMPLE_RAW_RECORD_1, SAMPLE_RAW_RECORD_PERSPECTIVE_2])
        assert len(norm["narratives"]) == 2
        assert norm["provenance"]["source_records_count"] == 2
        assert "occurrence_summary" in norm["provenance"]["source_perspectives"]
        assert "vessel_consolidated_narrative" in norm["provenance"]["source_perspectives"]


class TestTSBCContextGeneration:
    """Level 2 tests."""

    def test_generate_contexts(self):
        norm = TSBCRecordNormalizer.normalize_occurrence([SAMPLE_RAW_RECORD_1])
        contexts = TSBCContextGenerator.generate_contexts(norm)

        # 5 distinct perspective contexts
        assert len(contexts) == 5
        types = [c["context_type"] for c in contexts]
        assert "occurrence_overview" in types
        assert "vessel_profile" in types
        assert "environmental_conditions" in types
        assert "damage_and_safety" in types
        assert "equipment_profile" in types

        # Check provenance in each context
        for c in contexts:
            assert c["occurrence_id"] == 4
            assert c["vessel_identifier"] == "ANVOURGON"
            assert "text" in c
            assert len(c["text"]) > 20

    def test_no_synthetic_facts(self):
        norm = TSBCRecordNormalizer.normalize_occurrence([SAMPLE_RAW_RECORD_1])
        contexts = TSBCContextGenerator.generate_contexts(norm)
        vessel_ctx = next(c for c in contexts if c["context_type"] == "vessel_profile")
        # IMO was not in sample record, should not invent one
        assert "IMO:" not in vessel_ctx["text"] or "Unavailable" in vessel_ctx["text"]


class TestTSBCSafetyGuardsAndDryRun:
    """Level 3 tests."""

    def test_safety_guard_record_limit(self, tmp_path):
        pipe = TSBCPipeline(dataset_name="test_guard", cache_dir=tmp_path / "cache", max_records=1)
        raw_file = tmp_path / "test.jsonl"
        # Write two distinct occurrence IDs
        rec1 = copy.deepcopy(SAMPLE_RAW_RECORD_1)
        rec2 = copy.deepcopy(SAMPLE_RAW_RECORD_1)
        rec2["occurrence_id"] = 999
        with open(raw_file, "w") as f:
            f.write(json.dumps(rec1) + "\n")
            f.write(json.dumps(rec2) + "\n")

        with pytest.raises(ValueError, match="SAFETY GUARD TRIGGERED: Dataset has 2 occurrences"):
            pipe.process_normalization(raw_file)

    def test_dry_run_zero_api_calls(self, tmp_path):
        pipe = TSBCPipeline(dataset_name="test_dry_run", cache_dir=tmp_path / "cache", max_records=1)
        raw_file = tmp_path / "test_1.jsonl"
        with open(raw_file, "w") as f:
            f.write(json.dumps(SAMPLE_RAW_RECORD_1) + "\n")

        report = pipe.dry_run(raw_file)
        assert report["status"] == "DRY_RUN_SUCCESS"
        assert report["external_api_calls_made"] == 0
        assert report["occurrences_selected"] == 1
        assert report["contexts_generated"] == 5
        assert report["embedding_dimension"] == 1024
        assert report["embedding_model"] == "mistral-embed"


class TestDataEdgeCases:
    """Edge cases: missing values, nulls, empty arrays, malformed structures."""

    def test_empty_vessels(self):
        rec = copy.deepcopy(SAMPLE_RAW_RECORD_1)
        rec["structured"]["vessels"] = []
        norm = TSBCRecordNormalizer.normalize_occurrence([rec])
        assert norm["vessel"]["vessel_name"] is None
        ctxs = TSBCContextGenerator.generate_contexts(norm)
        assert len(ctxs) == 5

    def test_null_everything_except_id(self):
        rec = {
            "occurrence_id": 9999,
            "document": "",
            "provenance": {"perspective": "minimal"},
            "structured": {
                "occurrence_id": 9999,
                "occurrence": {"OccID": 9999},
                "vessels": [{}],
            },
        }
        norm = TSBCRecordNormalizer.normalize_occurrence([rec])
        assert norm["occurrence"]["occurrence_id"] == 9999
        ctxs = TSBCContextGenerator.generate_contexts(norm)
        assert len(ctxs) == 5
        assert all("Unavailable" in c["text"] or len(c["text"]) > 10 for c in ctxs)

    def test_unicode_and_special_chars(self):
        rec = copy.deepcopy(SAMPLE_RAW_RECORD_1)
        rec["structured"]["occurrence"]["Summary"] = "Accident près de la Côte-Nord avec des vagues de 3 mètres; café & éclat d'étincelles."
        norm = TSBCRecordNormalizer.normalize_occurrence([rec])
        ctxs = TSBCContextGenerator.generate_contexts(norm)
        overview = next(c for c in ctxs if c["context_type"] == "occurrence_overview")
        assert "Côte-Nord" in overview["text"]
        assert "café & éclat" in overview["text"]
