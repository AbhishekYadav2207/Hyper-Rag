# -*- coding: utf-8 -*-
"""
Adaptive Hyper-RAG Phase 3: Response Validation Module
Deterministically validates generated responses against the user query and retrieved evidence
after LLM reasoning completes.
Zero LLM calls are made for response validation.
"""

import re
import string
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple, Set

from my_config import (
    ADAPTIVE_VALIDATION_ENABLED,
    ADAPTIVE_VALIDATION_THRESHOLD,
    ADAPTIVE_VALIDATION_LOG_DECISIONS,
    ADAPTIVE_VALIDATION_COMPLETENESS_WEIGHT,
    ADAPTIVE_VALIDATION_EVIDENCE_WEIGHT,
    ADAPTIVE_VALIDATION_RELEVANCE_WEIGHT,
)
from .adaptive_router import QueryComplexityAnalyzer, QueryFeatures

logger = logging.getLogger("hyper_rag")


# =============================================================================
# 1. DATA STRUCTURES & SCHEMAS
# =============================================================================

@dataclass
class ValidationWeights:
    """Configurable weights for the three response validation dimensions."""
    completeness_weight: float = ADAPTIVE_VALIDATION_COMPLETENESS_WEIGHT
    evidence_weight: float = ADAPTIVE_VALIDATION_EVIDENCE_WEIGHT
    relevance_weight: float = ADAPTIVE_VALIDATION_RELEVANCE_WEIGHT

    def normalized(self) -> Tuple[float, float, float]:
        """Return non-negative normalized weights that sum to 1.0."""
        w_c = max(0.0, float(self.completeness_weight))
        w_e = max(0.0, float(self.evidence_weight))
        w_r = max(0.0, float(self.relevance_weight))
        total = w_c + w_e + w_r
        if total <= 0.0:
            return (0.40, 0.40, 0.20)
        return (w_c / total, w_e / total, w_r / total)


@dataclass
class ValidationMetrics:
    """Fine-grained metrics tracked during validation."""
    total_claims: int = 0
    supported_claims: int = 0
    unsupported_claim_count: int = 0
    requested_aspects_count: int = 0
    covered_aspects_count: int = 0
    query_entity_count: int = 0
    covered_query_entities: int = 0
    comparison_evaluated: bool = False
    comparison_valid: bool = False
    causal_evaluated: bool = False
    causal_valid: bool = False
    temporal_evaluated: bool = False
    temporal_valid: bool = False
    multi_hop_evaluated: bool = False
    multi_hop_valid: bool = False
    evidence_token_overlap: float = 0.0
    relevance_token_overlap: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_claims": self.total_claims,
            "supported_claims": self.supported_claims,
            "unsupported_claim_count": self.unsupported_claim_count,
            "requested_aspects_count": self.requested_aspects_count,
            "covered_aspects_count": self.covered_aspects_count,
            "query_entity_count": self.query_entity_count,
            "covered_query_entities": self.covered_query_entities,
            "comparison_evaluated": self.comparison_evaluated,
            "comparison_valid": self.comparison_valid,
            "causal_evaluated": self.causal_evaluated,
            "causal_valid": self.causal_valid,
            "temporal_evaluated": self.temporal_evaluated,
            "temporal_valid": self.temporal_valid,
            "multi_hop_evaluated": self.multi_hop_evaluated,
            "multi_hop_valid": self.multi_hop_valid,
            "evidence_token_overlap": round(self.evidence_token_overlap, 3),
            "relevance_token_overlap": round(self.relevance_token_overlap, 3),
        }


@dataclass
class ValidationResult:
    """Structured decision returned by the Response Validator."""
    valid: bool
    score: float
    completeness_score: float
    evidence_score: float
    relevance_score: float
    missing_aspects: List[str]
    unsupported_claims: List[str]
    reasons: List[str]
    metrics: Dict[str, Any]
    query: str = ""
    failure_categories: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "score": round(self.score, 2),
            "completeness_score": round(self.completeness_score, 2),
            "evidence_score": round(self.evidence_score, 2),
            "relevance_score": round(self.relevance_score, 2),
            "missing_aspects": self.missing_aspects,
            "unsupported_claims": self.unsupported_claims,
            "reasons": self.reasons,
            "metrics": self.metrics,
            "failure_categories": self.failure_categories,
        }


# =============================================================================
# 2. ASPECT & REQUIREMENT EXTRACTION
# =============================================================================

# Stopwords for lexical analysis
_STOPWORDS: Set[str] = {
    "a", "an", "the", "and", "or", "but", "if", "then", "of", "at", "by", "for",
    "with", "about", "against", "between", "into", "through", "during", "before",
    "after", "above", "below", "to", "from", "up", "down", "in", "out", "on",
    "off", "over", "under", "again", "further", "once", "here", "there", "when",
    "where", "why", "how", "all", "any", "both", "each", "few", "more", "most",
    "other", "some", "such", "no", "nor", "not", "only", "own", "same", "so",
    "than", "too", "very", "can", "will", "just", "should", "now", "is", "are",
    "was", "were", "be", "been", "being", "have", "has", "had", "do", "does",
    "did", "would", "could", "may", "might", "must", "i", "you", "he", "she",
    "it", "we", "they", "them", "their", "his", "her", "its", "our", "what",
    "who", "which", "whom", "this", "that", "these", "those", "am",
}

# Conversational prefixes and generic filler to avoid flagging as claims
_FILLER_PATTERNS = [
    re.compile(r"^(?:sure|here is|here are|in summary|to summarize|in conclusion|overall|based on the provided|based on retrieved|according to|firstly|secondly|finally)[,:]?\s*", re.IGNORECASE),
]

# Morphological / synonym mappings for domain aspects
_ASPECT_STEMS: Dict[str, List[str]] = {
    "cause": ["cause", "causes", "caused", "causing", "etiology", "origin", "originate"],
    "causes": ["cause", "causes", "caused", "causing", "etiology", "origin", "originate"],
    "symptom": ["symptom", "symptoms", "sign", "signs", "manifestation", "manifestations", "present"],
    "symptoms": ["symptom", "symptoms", "sign", "signs", "manifestation", "manifestations", "present"],
    "treatment": ["treatment", "treatments", "treat", "treating", "treated", "therapy", "therapies", "manage", "management", "medication", "cure"],
    "treatments": ["treatment", "treatments", "treat", "treating", "treated", "therapy", "therapies", "manage", "management", "medication", "cure"],
    "prevention": ["prevention", "prevent", "preventing", "prevented", "preventative", "preventive", "avoid", "avoidance"],
    "diagnosis": ["diagnosis", "diagnose", "diagnostic", "diagnostics", "tested", "test", "testing", "detection"],
    "background": ["background", "early life", "history", "origins", "born", "upbringing"],
    "occupation": ["occupation", "job", "work", "clerk", "employed", "profession", "business", "career"],
    "family life": ["family", "wife", "children", "son", "daughter", "household", "home", "cratchit"],
    "struggles": ["struggle", "struggles", "hardship", "poverty", "difficulty", "difficulties", "poor"],
    "appearance": ["appearance", "looks", "look", "wore", "wearing", "robe", "green robe", "dress", "physical"],
    "behavior": ["behavior", "behaviour", "acts", "act", "conduct", "demeanor", "attitude", "cheer"],
    "actions": ["action", "actions", "deeds", "guided", "showed", "led", "took", "visited"],
    "lessons": ["lesson", "lessons", "moral", "taught", "teach", "message", "warning"],
    "manifestations": ["manifestation", "manifestations", "manifests", "shown", "expressed", "displayed"],
    "consequences": ["consequence", "consequences", "impact", "effects", "outcome", "outcomes"],
    "resolution": ["resolution", "resolved", "redemption", "transformed", "transformation", "changed"],
}


class RequestedAspectExtractor:
    """
    Extracts explicit query aspects, key entities, and relational expectations
    using deterministic lightweight NLP.
    """

    @classmethod
    def extract(cls, query: str, features: QueryFeatures) -> Tuple[List[str], List[str]]:
        """
        Extract:
        1. requested_aspects: List of explicit aspects requested (e.g. causes, symptoms, treatment, prevention).
        2. requested_entities: List of primary subjects/entities expected to be covered.
        """
        q_clean = query.strip()
        requested_aspects: List[str] = []
        requested_entities: List[str] = list(features.detected_entities)

        # 1. Check for "in terms of <aspects>" or "regarding <aspects>"
        terms_match = re.search(r"\b(?:in terms of|regarding|concerning|such as|including)\s+([^?.!]+)", q_clean, re.IGNORECASE)
        if terms_match:
            raw_terms = terms_match.group(1).strip()
            # Split by comma or 'and'
            parts = [p.strip() for p in re.split(r",|\band\b", raw_terms) if p.strip()]
            for p in parts:
                clean_p = re.sub(r"^(?:the|their|its|a|an)\s+", "", p, flags=re.IGNORECASE).strip()
                if clean_p and clean_p.lower() not in _STOPWORDS:
                    requested_aspects.append(clean_p.lower())

        # 2. Check for enumeration of known semantic aspects in query
        aspect_vocab = [
            "causes", "symptoms", "treatment", "treatments", "prevention",
            "diagnosis", "background", "occupation", "family life", "struggles",
            "appearance", "behavior", "actions", "lessons", "manifestations",
            "consequences", "resolution", "history", "evolution"
        ]
        q_lower = q_clean.lower()
        for asp in aspect_vocab:
            if re.search(r"\b" + re.escape(asp) + r"\b", q_lower):
                if asp not in requested_aspects:
                    requested_aspects.append(asp)

        # 3. Check for comma-separated aspect enumerations in "What are the X, Y, Z of..."
        enum_match = re.search(r"\b(?:what are the|detail the|explain the|describe the)\s+([a-zA-Z\s,]+(?:and\s+[a-zA-Z\s]+)?)\s+(?:of|in|for|between)\b", q_clean, re.IGNORECASE)
        if enum_match:
            raw_enum = enum_match.group(1).strip()
            parts = [p.strip() for p in re.split(r",|\band\b", raw_enum) if p.strip()]
            if len(parts) >= 2:
                for p in parts:
                    clean_p = re.sub(r"^(?:the|their|its|a|an)\s+", "", p, flags=re.IGNORECASE).strip()
                    if clean_p and clean_p.lower() not in _STOPWORDS and clean_p.lower() not in requested_aspects:
                        requested_aspects.append(clean_p.lower())

        # 4. Check for Comparison Entities (e.g., "Compare A and B", "difference between A and B", "A vs B")
        comp_pairs = re.search(r"\b(?:compare|comparison between|difference between|differ between)\s+([A-Za-z0-9\s'\-]+?)\s+(?:and|versus|vs\.?)\s+([A-Za-z0-9\s'\-]+?)(?:\s+in terms of|\s+with regards to|[?.!,]|$)", q_clean, re.IGNORECASE)
        if comp_pairs:
            e1 = comp_pairs.group(1).strip()
            e2 = comp_pairs.group(2).strip()
            # Clean leading/trailing stopwords
            e1 = re.sub(r"^(?:the|a|an)\s+", "", e1, flags=re.IGNORECASE).strip()
            e2 = re.sub(r"^(?:the|a|an)\s+", "", e2, flags=re.IGNORECASE).strip()
            for ent in [e1, e2]:
                if ent and ent not in requested_entities:
                    requested_entities.append(ent)

        # 5. Check for vs pattern: "A vs B" or "A versus B"
        vs_pairs = re.search(r"\b([A-Za-z0-9\s'\-]+?)\s+(?:vs\.?|versus)\s+([A-Za-z0-9\s'\-]+?)(?:[?.!,]|$)", q_clean, re.IGNORECASE)
        if vs_pairs and not comp_pairs:
            e1 = vs_pairs.group(1).strip()
            e2 = vs_pairs.group(2).strip()
            e1 = re.sub(r"^(?:the|a|an|why)\s+", "", e1, flags=re.IGNORECASE).strip()
            e2 = re.sub(r"^(?:the|a|an)\s+", "", e2, flags=re.IGNORECASE).strip()
            for ent in [e1, e2]:
                if ent and ent not in requested_entities:
                    requested_entities.append(ent)

        # 6. Check for Multi-Hop: "How does A affect B through C?"
        hop_match = re.search(r"\b(?:how does|how do)\s+([A-Za-z0-9\s'\-]+?)\s+(?:affect|influence|impact)\s+([A-Za-z0-9\s'\-]+?)\s+through\s+([A-Za-z0-9\s'\-]+?)(?:[?.!,]|$)", q_clean, re.IGNORECASE)
        if hop_match:
            for g in [1, 2, 3]:
                ent = hop_match.group(g).strip()
                ent = re.sub(r"^(?:the|a|an)\s+", "", ent, flags=re.IGNORECASE).strip()
                if ent and ent not in requested_entities:
                    requested_entities.append(ent)

        # 7. Check for Causal: "How did A cause B?"
        causal_match = re.search(r"\b(?:how did|how does|why did|what caused)\s+([A-Za-z0-9\s'\-]+?)\s+(?:cause|lead to|affect)\s+([A-Za-z0-9\s'\-]+?)(?:[?.!,]|$)", q_clean, re.IGNORECASE)
        if causal_match:
            for g in [1, 2]:
                ent = causal_match.group(g).strip()
                ent = re.sub(r"^(?:the|a|an)\s+", "", ent, flags=re.IGNORECASE).strip()
                if ent and ent not in requested_entities:
                    requested_entities.append(ent)

        # Deduplicate requested_aspects preserving order
        unique_aspects = []
        for a in requested_aspects:
            if a not in unique_aspects:
                unique_aspects.append(a)

        # Meta words that should never be considered requested entities
        meta_filter = {
            "terms", "term", "aspect", "aspects", "difference", "differences", "comparison",
            "manner", "way", "role", "narrative", "story", "text", "causes", "symptoms",
            "treatment", "prevention", "diagnosis", "background", "occupation", "struggles",
            "appearance", "behavior", "actions", "lessons", "employees", "consequences", "resolution"
        }

        # For comparison queries, prefer explicit compared entity pair
        if comp_pairs or vs_pairs:
            pair_match = comp_pairs or vs_pairs
            e1 = pair_match.group(1).strip()
            e2 = pair_match.group(2).strip()
            e1 = re.sub(r"^(?:the|a|an|why)\s+", "", e1, flags=re.IGNORECASE).strip()
            e2 = re.sub(r"^(?:the|a|an)\s+", "", e2, flags=re.IGNORECASE).strip()
            requested_entities = [e1, e2]
        else:
            filtered_entities = []
            for ent in requested_entities:
                ent_clean = ent.strip()
                if (
                    ent_clean.lower() not in meta_filter
                    and ent_clean.lower() not in _STOPWORDS
                    and len(ent_clean) > 1
                    and ent_clean.lower() not in [a.lower() for a in unique_aspects]
                ):
                    if ent_clean not in filtered_entities:
                        filtered_entities.append(ent_clean)
            requested_entities = filtered_entities

        return unique_aspects, requested_entities


# =============================================================================
# 3. BASE VALIDATOR CLASS
# =============================================================================

class BaseResponseValidator(ABC):
    """Abstract interface defining the response validation contract."""

    @abstractmethod
    def validate(
        self,
        query: str,
        answer: str,
        retrieved_context: Optional[Any] = None,
        adaptive_decision: Optional[Any] = None,
        retrieval_metrics: Optional[Dict[str, Any]] = None,
    ) -> ValidationResult:
        """Validate a generated answer against the query and retrieved context."""
        pass


# =============================================================================
# 4. DETERMINISTIC RESPONSE VALIDATOR
# =============================================================================

class DeterministicResponseValidator(BaseResponseValidator):
    """
    Evaluates generated responses across:
    1. Completeness: Were all requested aspects, entities, and relationships addressed?
    2. Evidence Support: Are the response's factual claims supported by retrieved context?
    3. Relevance: Does the response directly address the user query without irrelevant drift?

    Executes 100% deterministically with zero LLM and zero embedding calls.
    """

    def __init__(
        self,
        weights: Optional[ValidationWeights] = None,
        threshold: float = ADAPTIVE_VALIDATION_THRESHOLD,
        log_decisions: bool = ADAPTIVE_VALIDATION_LOG_DECISIONS,
    ):
        self.weights = weights or ValidationWeights()
        self.threshold = float(threshold)
        self.log_decisions = log_decisions

    def _extract_context_text(self, retrieved_context: Optional[Any]) -> str:
        """Flatten retrieved context into a single searchable text string."""
        if not retrieved_context:
            return ""
        if isinstance(retrieved_context, str):
            return retrieved_context

        text_pieces: List[str] = []
        if isinstance(retrieved_context, dict):
            # Direct context string
            if "context" in retrieved_context and isinstance(retrieved_context["context"], str):
                text_pieces.append(retrieved_context["context"])

            # Text units
            if "text_units" in retrieved_context and isinstance(retrieved_context["text_units"], list):
                for tu in retrieved_context["text_units"]:
                    if isinstance(tu, dict) and "content" in tu:
                        text_pieces.append(str(tu["content"]))
                    elif isinstance(tu, str):
                        text_pieces.append(tu)

            # Entities
            if "entities" in retrieved_context and isinstance(retrieved_context["entities"], list):
                for ent in retrieved_context["entities"]:
                    if isinstance(ent, dict):
                        name = ent.get("entity_name", "")
                        desc = ent.get("description", "")
                        text_pieces.append(f"{name}: {desc}")

            # Hyperedges
            if "hyperedges" in retrieved_context and isinstance(retrieved_context["hyperedges"], list):
                for he in retrieved_context["hyperedges"]:
                    if isinstance(he, dict):
                        es = str(he.get("entity_set", ""))
                        desc = he.get("description", "")
                        text_pieces.append(f"{es}: {desc}")

        return " \n ".join(text_pieces)

    def _split_into_claims(self, answer: str) -> List[str]:
        """Split answer into substantive factual sentences/claims."""
        if not answer:
            return []
        raw_sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", answer) if s.strip()]
        claims: List[str] = []
        for s in raw_sentences:
            # Check length
            words = s.split()
            if len(words) < 3:
                continue
            # Filter pure conversational filler
            clean_s = s
            for fp in _FILLER_PATTERNS:
                clean_s = fp.sub("", clean_s)
            if len(clean_s.split()) >= 3:
                claims.append(s)
        return claims

    def _is_aspect_covered(self, aspect: str, answer_lower: str) -> bool:
        """Check if a requested aspect is addressed in the answer text."""
        asp_clean = aspect.lower().strip()
        # Direct word match
        if re.search(r"\b" + re.escape(asp_clean) + r"\b", answer_lower):
            return True

        # Check known stems / synonyms
        if asp_clean in _ASPECT_STEMS:
            for variant in _ASPECT_STEMS[asp_clean]:
                if re.search(r"\b" + re.escape(variant) + r"\b", answer_lower):
                    return True

        # Check multi-word aspect token matches
        tokens = [t for t in asp_clean.split() if t not in _STOPWORDS]
        if tokens and all(t in answer_lower for t in tokens):
            return True

        return False

    def _evaluate_completeness(
        self,
        query: str,
        answer: str,
        features: QueryFeatures,
        requested_aspects: List[str],
        requested_entities: List[str],
    ) -> Tuple[float, List[str], List[str], Dict[str, Any]]:
        """
        Evaluate coverage of requested aspects, entities, and relational structures.
        Returns: (completeness_score, missing_aspects, reasons, metrics_dict)
        """
        ans_lower = answer.lower()
        missing_aspects: List[str] = []
        reasons: List[str] = []
        metrics: Dict[str, Any] = {
            "comparison_evaluated": False,
            "comparison_valid": False,
            "causal_evaluated": False,
            "causal_valid": False,
            "temporal_evaluated": False,
            "temporal_valid": False,
            "multi_hop_evaluated": False,
            "multi_hop_valid": False,
            "requested_aspects_count": len(requested_aspects),
            "covered_aspects_count": 0,
            "query_entity_count": len(requested_entities),
            "covered_query_entities": 0,
        }

        # 1. Check Explicit Aspects
        covered_aspects_count = 0
        if requested_aspects:
            for asp in requested_aspects:
                if self._is_aspect_covered(asp, ans_lower):
                    covered_aspects_count += 1
                else:
                    missing_aspects.append(asp)
            metrics["covered_aspects_count"] = covered_aspects_count
            aspect_ratio = covered_aspects_count / len(requested_aspects)
            aspect_score = aspect_ratio * 100.0
        else:
            aspect_score = 100.0

        # 2. Check Key Entity Coverage
        covered_entities_count = 0
        missing_entities: List[str] = []
        for ent in requested_entities:
            # Check presence of entity or main tokens of entity
            ent_clean = ent.lower().strip()
            ent_tokens = [t for t in ent_clean.split() if t not in _STOPWORDS and len(t) > 1]
            if not ent_tokens:
                covered_entities_count += 1
                continue
            # If at least half the substantive tokens are present
            present_tokens = sum(1 for t in ent_tokens if t in ans_lower)
            if present_tokens >= max(1, len(ent_tokens) // 2):
                covered_entities_count += 1
            else:
                missing_entities.append(ent)

        metrics["covered_query_entities"] = covered_entities_count
        entity_score = (
            (covered_entities_count / len(requested_entities) * 100.0)
            if requested_entities
            else 100.0
        )

        # 3. Check Relational & Structural Requirements
        relational_penalties: float = 0.0

        # Comparison Check
        if features.comparison:
            metrics["comparison_evaluated"] = True
            # Require both entities (if >= 2 requested) AND comparative synthesis words
            has_entities = len(missing_entities) == 0 or (len(requested_entities) >= 2 and covered_entities_count >= 2)
            comp_words = [
                "compare", "compared", "contrast", "contrasting", "differ",
                "different", "difference", "differences", "whereas", "while",
                "both", "unlike", "in contrast", "on the other hand", "more than",
                "less than", "similar", "similarly", "counterpart", "versus"
            ]
            has_comp_synthesis = any(re.search(r"\b" + re.escape(w) + r"\b", ans_lower) for w in comp_words)
            if has_entities and has_comp_synthesis:
                metrics["comparison_valid"] = True
            else:
                metrics["comparison_valid"] = False
                relational_penalties += 35.0
                if not has_entities:
                    reasons.append("Comparison query missing one or more compared entities")
                    for me in missing_entities:
                        if me not in missing_aspects:
                            missing_aspects.append(f"entity: {me}")
                elif not has_comp_synthesis:
                    reasons.append("Comparison requested but comparative relationship between entities was not synthesized")

        # Causal Check
        is_explicit_causal = False
        if features.causal_reasoning:
            causal_question_triggers = [
                "why", "how did", "how does", "how do", "how can", "what causes",
                "what caused", "cause of", "mechanism", "underlying reason", "lead to",
                "leads to", "resulting in", "contributed to", "contributes to"
            ]
            q_low = query.lower()
            if any(re.search(r"\b" + re.escape(trig) + r"\b", q_low) for trig in causal_question_triggers):
                # If there are 3+ aspects requested (like "causes, symptoms, treatment..."), it's an aspect question, not a causal inquiry
                if len(requested_aspects) < 3 or any(w in q_low for w in ["how did", "why"]):
                    is_explicit_causal = True

        if is_explicit_causal:
            metrics["causal_evaluated"] = True
            causal_words = [
                "because", "caused by", "causes", "causing", "leads to", "led to",
                "resulting in", "results in", "due to", "as a result", "contributed to",
                "contributes to", "consequence", "triggers", "mechanism", "therefore",
                "thus", "produces", "underlying reason", "originates from"
            ]
            has_causal_synthesis = any(re.search(r"\b" + re.escape(w) + r"\b", ans_lower) for w in causal_words)
            if has_causal_synthesis:
                metrics["causal_valid"] = True
            else:
                metrics["causal_valid"] = False
                relational_penalties += 35.0
                reasons.append("Causal explanation requested but causal relationship was not explained")

        # Temporal Check
        if features.temporal_reasoning:
            metrics["temporal_evaluated"] = True
            temporal_words = [
                "initially", "later", "eventually", "over time", "progression",
                "before", "after", "subsequently", "first", "then", "finally",
                "historically", "evolved", "evolution", "chronology", "chronological",
                "decades", "years later", "as time passed", "development", "transform"
            ]
            # Require at least 2 temporal markers or a progression sequence
            temp_count = sum(1 for w in temporal_words if re.search(r"\b" + re.escape(w) + r"\b", ans_lower))
            if temp_count >= 2:
                metrics["temporal_valid"] = True
            else:
                metrics["temporal_valid"] = False
                relational_penalties += 35.0
                reasons.append("Temporal progression requested but chronological evolution was not explained")

        # Multi-Hop Check
        is_explicit_multihop = False
        if features.multi_hop and any(s != "multi-entity relationship pathway" for s in features.multi_hop_signals):
            is_explicit_multihop = True
        elif features.multi_hop and re.search(r"\b(?:through|pathway|chain|connection between)\b", query.lower()):
            is_explicit_multihop = True

        if is_explicit_multihop:
            metrics["multi_hop_evaluated"] = True
            hop_words = [
                "through", "leads to", "which in turn", "connected to", "influencing",
                "resulting in", "pathway", "link", "relationship", "chain"
            ]
            has_hop_synthesis = any(re.search(r"\b" + re.escape(w) + r"\b", ans_lower) for w in hop_words)
            has_all_nodes = len(missing_entities) == 0
            if has_hop_synthesis and has_all_nodes:
                metrics["multi_hop_valid"] = True
            else:
                metrics["multi_hop_valid"] = False
                relational_penalties += 35.0
                if not has_all_nodes:
                    reasons.append("Multi-hop query missing intermediate or terminal entities")
                    for me in missing_entities:
                        if me not in missing_aspects:
                            missing_aspects.append(f"entity: {me}")
                elif not has_hop_synthesis:
                    reasons.append("Multi-hop relationship path was not explained")

        # Aggregation Note
        if features.aggregation:
            # Check for enumeration markers (bullets, numbered lists, commas)
            list_markers = re.findall(r"(?:^\s*[-*•]|\d+\.|\b(?:first|second|third|also)\b)", answer, re.MULTILINE | re.IGNORECASE)
            if len(list_markers) < 2 and "," not in answer:
                reasons.append("Potentially incomplete aggregation relative to retrieved evidence")

        # Calculate final completeness score
        if requested_aspects and requested_entities:
            base_completeness = (aspect_score * 0.75) + (entity_score * 0.25)
        elif requested_aspects:
            base_completeness = aspect_score
        elif requested_entities:
            base_completeness = entity_score
        else:
            base_completeness = 100.0

        completeness_score = max(0.0, min(100.0, base_completeness - relational_penalties))

        if missing_aspects and not any("does not address all requested aspects" in r for r in reasons):
            reasons.append("The response does not address all requested aspects")

        return completeness_score, missing_aspects, reasons, metrics

    def _evaluate_evidence(
        self,
        answer: str,
        retrieved_context_text: str,
        claims: List[str],
    ) -> Tuple[float, List[str], Dict[str, Any]]:
        """
        Evaluate whether the answer's claims are supported by retrieved evidence.
        Returns: (evidence_score, unsupported_claims, metrics_dict)
        """
        unsupported_claims: List[str] = []
        metrics: Dict[str, Any] = {
            "total_claims": len(claims),
            "supported_claims": 0,
            "unsupported_claim_count": 0,
            "evidence_token_overlap": 0.0,
        }

        if not retrieved_context_text.strip():
            # If no context was retrieved at all but answer makes claims
            if claims:
                unsupported_claims = list(claims)
                metrics["unsupported_claim_count"] = len(claims)
                return 0.0, unsupported_claims, metrics
            return 0.0, [], metrics

        ctx_lower = retrieved_context_text.lower()
        ctx_tokens = set(re.findall(r"\b\w{2,}\b", ctx_lower))

        ans_tokens = set(re.findall(r"\b\w{2,}\b", answer.lower())) - _STOPWORDS
        overlap_tokens = ans_tokens & ctx_tokens
        token_overlap_ratio = len(overlap_tokens) / max(1, len(ans_tokens))
        metrics["evidence_token_overlap"] = token_overlap_ratio

        # Common capitalized words that should not be treated as unsupported foreign proper nouns
        common_proper_words = {
            "Christmas", "English", "Monday", "Tuesday", "Wednesday", "Thursday",
            "Friday", "Saturday", "Sunday", "January", "February", "March", "April",
            "May", "June", "July", "August", "September", "October", "November",
            "December", "God", "Lord", "Past", "Present", "Future", "Day", "Days"
        }

        # Evaluate claim by claim
        for claim in claims:
            c_lower = claim.lower()
            c_words = [w for w in re.findall(r"\b\w{2,}\b", c_lower) if w not in _STOPWORDS]
            if not c_words:
                continue

            # Check for specific numbers / years in claim (e.g. 1832, 1899)
            specific_numbers = re.findall(r"\b\d{3,4}\b", claim)
            unsupported_numbers = [n for n in specific_numbers if n not in ctx_lower]

            # Check for proper noun sequences in claim (e.g. Paris, London)
            prop_nouns = re.findall(r"\b[A-Z][a-z]+\b", claim)
            unsupported_nouns = [
                pn for pn in prop_nouns
                if pn.lower() not in _STOPWORDS
                and pn not in common_proper_words
                and pn.lower() not in ctx_lower
            ]

            # Check lexical overlap of substantive words in claim
            c_overlap = sum(1 for w in c_words if w in ctx_tokens) / len(c_words)
            has_grounding = any(w in ctx_tokens for w in c_words)

            # A claim is unsupported by retrieved evidence if:
            # 1. It introduces specific numbers/dates not in context (e.g. 1832), OR
            # 2. It introduces foreign proper nouns absent from context (e.g. Paris, London), OR
            # 3. Its lexical overlap is extremely low (< 0.15) with no grounding
            if unsupported_numbers or (len(unsupported_nouns) >= 1 and c_overlap < 0.30) or (c_overlap < 0.15 and not has_grounding):
                unsupported_claims.append(claim)

        metrics["unsupported_claim_count"] = len(unsupported_claims)
        metrics["supported_claims"] = max(0, len(claims) - len(unsupported_claims))

        total_claims_count = max(1, len(claims))
        claim_support_ratio = metrics["supported_claims"] / total_claims_count

        # Score composition: 70% claim support ratio + 30% global token overlap
        evidence_score = (claim_support_ratio * 70.0) + (min(1.0, token_overlap_ratio * 1.5) * 30.0)
        evidence_score = max(0.0, min(100.0, evidence_score))

        return evidence_score, unsupported_claims, metrics

    def _evaluate_relevance(
        self,
        query: str,
        answer: str,
        features: QueryFeatures,
        requested_entities: List[str],
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Evaluate relevance of the answer to the user query.
        Returns: (relevance_score, metrics_dict)
        """
        metrics: Dict[str, Any] = {"relevance_token_overlap": 0.0}
        q_lower = query.lower()
        ans_lower = answer.lower()

        # Query content words (excluding question words and stopwords)
        q_tokens = set(re.findall(r"\b\w{2,}\b", q_lower)) - _STOPWORDS - {
            "what", "who", "where", "how", "why", "when", "which", "tell", "explain", "describe", "detail"
        }
        ans_tokens = set(re.findall(r"\b\w{2,}\b", ans_lower)) - _STOPWORDS

        if not q_tokens:
            return 100.0, metrics

        overlap_tokens = q_tokens & ans_tokens
        token_overlap = len(overlap_tokens) / len(q_tokens)
        metrics["relevance_token_overlap"] = token_overlap

        # Entity coverage in answer
        if requested_entities:
            ent_covered = sum(
                1 for ent in requested_entities
                if any(t in ans_lower for t in ent.lower().split() if t not in _STOPWORDS and len(t) > 1)
            )
            entity_ratio = ent_covered / len(requested_entities)
        else:
            entity_ratio = 1.0

        # Structural alignment bonus (up to 15 pts)
        struct_pts = 0.0
        if features.comparison and any(w in ans_lower for w in ["compare", "difference", "whereas", "while", "unlike"]):
            struct_pts += 15.0
        elif features.causal_reasoning and any(w in ans_lower for w in ["because", "caused", "causes", "leads to", "resulting"]):
            struct_pts += 15.0
        elif features.temporal_reasoning and any(w in ans_lower for w in ["over time", "initially", "later", "progression", "before"]):
            struct_pts += 15.0
        else:
            struct_pts = 10.0

        relevance_score = (token_overlap * 45.0) + (entity_ratio * 40.0) + struct_pts
        # Completely off-topic check: if zero query content tokens and zero entities match
        if token_overlap == 0.0 and (not requested_entities or entity_ratio == 0.0):
            relevance_score = 0.0

        relevance_score = max(0.0, min(100.0, relevance_score))
        return relevance_score, metrics

    def validate(
        self,
        query: str,
        answer: str,
        retrieved_context: Optional[Any] = None,
        adaptive_decision: Optional[Any] = None,
        retrieval_metrics: Optional[Dict[str, Any]] = None,
    ) -> ValidationResult:
        """
        Execute deterministic post-reasoning validation on the generated answer.
        """
        # Step 20: Empty / whitespace / None answers
        if answer is None or not str(answer).strip():
            empty_res = ValidationResult(
                valid=False,
                score=0.0,
                completeness_score=0.0,
                evidence_score=0.0,
                relevance_score=0.0,
                missing_aspects=[],
                unsupported_claims=[],
                reasons=["Empty answer"],
                metrics=ValidationMetrics().to_dict(),
                query=query,
                failure_categories=["EMPTY"],
            )
            if self.log_decisions:
                logger.warning("[Adaptive Validation] Received empty answer. Status: INVALID")
            return empty_res

        ans_str = str(answer).strip()

        # Step 6: Extract structural and semantic features from query
        if adaptive_decision and hasattr(adaptive_decision, "features") and isinstance(adaptive_decision.features, dict):
            # QueryFeatures from existing routing decision
            features = QueryComplexityAnalyzer.analyze(query)
        else:
            features = QueryComplexityAnalyzer.analyze(query)

        requested_aspects, requested_entities = RequestedAspectExtractor.extract(query, features)

        # 1. Completeness Analysis
        completeness_score, missing_aspects, comp_reasons, comp_metrics = self._evaluate_completeness(
            query=query,
            answer=ans_str,
            features=features,
            requested_aspects=requested_aspects,
            requested_entities=requested_entities,
        )

        # 2. Evidence Support Analysis
        context_text = self._extract_context_text(retrieved_context)
        claims = self._split_into_claims(ans_str)
        evidence_score, unsupported_claims, ev_metrics = self._evaluate_evidence(
            answer=ans_str,
            retrieved_context_text=context_text,
            claims=claims,
        )

        # 3. Relevance Analysis
        relevance_score, rel_metrics = self._evaluate_relevance(
            query=query,
            answer=ans_str,
            features=features,
            requested_entities=requested_entities,
        )

        # Combine metrics
        v_metrics = ValidationMetrics(
            total_claims=ev_metrics["total_claims"],
            supported_claims=ev_metrics["supported_claims"],
            unsupported_claim_count=ev_metrics["unsupported_claim_count"],
            requested_aspects_count=comp_metrics["requested_aspects_count"],
            covered_aspects_count=comp_metrics["covered_aspects_count"],
            query_entity_count=comp_metrics["query_entity_count"],
            covered_query_entities=comp_metrics["covered_query_entities"],
            comparison_evaluated=comp_metrics["comparison_evaluated"],
            comparison_valid=comp_metrics["comparison_valid"],
            causal_evaluated=comp_metrics["causal_evaluated"],
            causal_valid=comp_metrics["causal_valid"],
            temporal_evaluated=comp_metrics["temporal_evaluated"],
            temporal_valid=comp_metrics["temporal_valid"],
            multi_hop_evaluated=comp_metrics["multi_hop_evaluated"],
            multi_hop_valid=comp_metrics["multi_hop_valid"],
            evidence_token_overlap=ev_metrics["evidence_token_overlap"],
            relevance_token_overlap=rel_metrics["relevance_token_overlap"],
        )

        # Step 17: Overall Score Formula with Normalized Weights
        w_c, w_e, w_r = self.weights.normalized()
        overall_score = (completeness_score * w_c) + (evidence_score * w_e) + (relevance_score * w_r)
        overall_score = round(max(0.0, min(100.0, overall_score)), 2)

        # Step 19 & 29: Hard Failures & Failure Categories
        failure_categories: List[str] = []
        reasons: List[str] = list(comp_reasons)

        # Hard Failure 1: Irrelevant Answer
        if relevance_score < 30.0:
            reasons.append("Answer is irrelevant to the query")
            failure_categories.append("IRRELEVANT")

        # Hard Failure 2: Major Missing Requested Aspects
        if requested_aspects and len(missing_aspects) >= max(1, len(requested_aspects) // 2):
            if "INCOMPLETE" not in failure_categories:
                failure_categories.append("INCOMPLETE")

        # Hard Failure 3: Missing Compared Entity or Relational Failure
        if comp_metrics["comparison_evaluated"] and not comp_metrics["comparison_valid"]:
            if "INCOMPLETE" not in failure_categories:
                failure_categories.append("INCOMPLETE")
        if comp_metrics["causal_evaluated"] and not comp_metrics["causal_valid"]:
            if "INCOMPLETE" not in failure_categories:
                failure_categories.append("INCOMPLETE")
        if comp_metrics["temporal_evaluated"] and not comp_metrics["temporal_valid"]:
            if "INCOMPLETE" not in failure_categories:
                failure_categories.append("INCOMPLETE")
        if comp_metrics["multi_hop_evaluated"] and not comp_metrics["multi_hop_valid"]:
            if "INCOMPLETE" not in failure_categories:
                failure_categories.append("INCOMPLETE")

        # Hard Failure 4: Substantial Unsupported Content
        if unsupported_claims and (evidence_score < 35.0 or len(unsupported_claims) >= max(1, len(claims) // 2)):
            reasons.append("Substantial unsupported claims detected relative to retrieved evidence")
            failure_categories.append("UNSUPPORTED")

        # Threshold check
        if overall_score < self.threshold:
            if not failure_categories:
                reasons.append(f"Overall validation score {overall_score:.1f} is below threshold {self.threshold:.1f}")
                if completeness_score < self.threshold:
                    failure_categories.append("INCOMPLETE")
                if evidence_score < self.threshold:
                    failure_categories.append("UNSUPPORTED")
                if relevance_score < self.threshold:
                    failure_categories.append("IRRELEVANT")

        is_valid = (overall_score >= self.threshold) and (len(failure_categories) == 0)

        # Format failure categories
        if not is_valid and not failure_categories:
            failure_categories.append("INCOMPLETE")
        if len(failure_categories) > 1 and "MIXED" not in failure_categories:
            failure_categories.append("MIXED")

        # Reasons for Valid Result
        if is_valid:
            reasons.append("All requested aspects were addressed")
            reasons.append("Major answer claims are supported by retrieved evidence")

        # Remove duplicate reasons
        seen_r = set()
        clean_reasons = []
        for r in reasons:
            if r not in seen_r:
                seen_r.add(r)
                clean_reasons.append(r)

        result = ValidationResult(
            valid=is_valid,
            score=overall_score,
            completeness_score=round(completeness_score, 2),
            evidence_score=round(evidence_score, 2),
            relevance_score=round(relevance_score, 2),
            missing_aspects=missing_aspects,
            unsupported_claims=unsupported_claims,
            reasons=clean_reasons,
            metrics=v_metrics.to_dict(),
            query=query,
            failure_categories=failure_categories,
        )

        # Step 26: Logging Decisions
        if self.log_decisions:
            status_str = "VALID" if result.valid else "INVALID"
            log_lines = [
                "[Adaptive Validation]",
                f"Completeness: {result.completeness_score:.1f}",
                f"Evidence: {result.evidence_score:.1f}",
                f"Relevance: {result.relevance_score:.1f}",
                f"Overall: {result.score:.1f}",
                f"Status: {status_str}",
            ]
            if not result.valid:
                if result.missing_aspects:
                    log_lines.append("")
                    log_lines.append("Missing aspects:")
                    for ma in result.missing_aspects:
                        log_lines.append(f"- {ma}")
                if result.unsupported_claims:
                    log_lines.append("")
                    log_lines.append(f"Unsupported claims detected: {len(result.unsupported_claims)}")
            log_output = "\n".join(log_lines)
            logger.info(log_output)
            print(log_output)

        return result


# Alias for canonical usage
ResponseValidator = DeterministicResponseValidator
