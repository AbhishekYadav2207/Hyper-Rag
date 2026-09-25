# -*- coding: utf-8 -*-
"""
Adaptive Hyper-RAG Phase 2: Retrieval Sufficiency Evaluator
Deterministically evaluates whether the evidence retrieved by Hyper-Lite is sufficient
to answer the query, or if it must be escalated to Hyper-Core.
Zero LLM calls are made for sufficiency evaluation.
"""

import re
import string
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional, Tuple, Set

from my_config import (
    ADAPTIVE_RETRIEVAL_SUFFICIENCY_ENABLED,
    ADAPTIVE_RETRIEVAL_SUFFICIENCY_THRESHOLD,
    ADAPTIVE_LOG_DECISIONS,
)
from .adaptive_router import QueryComplexityAnalyzer

logger = logging.getLogger("hyper_rag")


@dataclass
class RetrievalMetrics:
    """Detailed evidence metrics extracted from retrieved context."""
    entity_count: int
    hyperedge_count: int
    text_unit_count: int
    total_char_length: int
    query_entity_coverage: float
    lexical_overlap: float
    duplicate_ratio: float
    has_relational_evidence: bool
    retrieved_entity_names: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_count": self.entity_count,
            "hyperedge_count": self.hyperedge_count,
            "text_unit_count": self.text_unit_count,
            "total_char_length": self.total_char_length,
            "query_entity_coverage": round(self.query_entity_coverage, 2),
            "lexical_overlap": round(self.lexical_overlap, 2),
            "duplicate_ratio": round(self.duplicate_ratio, 2),
            "has_relational_evidence": self.has_relational_evidence,
            "retrieved_entity_names": self.retrieved_entity_names,
        }


@dataclass
class RetrievalSufficiency:
    """Structured decision returned by the Retrieval Sufficiency Evaluator."""
    sufficient: bool
    score: int  # 0-100
    threshold: int  # default 60
    confidence: float
    reasons: List[str]
    metrics: Dict[str, Any]
    query: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sufficient": self.sufficient,
            "score": self.score,
            "threshold": self.threshold,
            "confidence": self.confidence,
            "reasons": self.reasons,
            "metrics": self.metrics,
        }


@dataclass
class SufficiencyWeights:
    """Configurable weights for deterministic retrieval sufficiency scoring."""
    # Volume & Item count (max 25 pts)
    text_unit_1_pts: float = 10.0
    text_unit_2_pts: float = 18.0
    text_unit_3_plus_pts: float = 25.0

    # Entity Coverage (max 25 pts)
    entity_coverage_max_pts: float = 25.0

    # Relationship Evidence (max 25 pts)
    hyperedge_2_plus_pts: float = 25.0
    hyperedge_1_pts: float = 15.0
    hyperedge_simple_baseline_pts: float = 20.0  # Simple queries don't require hyperedges

    # Context Quality & Length (max 25 pts)
    context_length_max_pts: float = 20.0
    diversity_bonus_pts: float = 5.0
    duplicate_penalty_max: float = 15.0

    # Penalties for unsatisfied query requirements
    multi_hop_missing_relation_penalty: float = 25.0
    comparison_missing_coverage_penalty: float = 20.0


# Basic stopwords for lexical overlap calculation
_STOPWORDS_SET: Set[str] = {
    "a", "an", "the", "and", "or", "but", "if", "then", "of", "at", "by", "for",
    "with", "about", "against", "between", "into", "through", "during", "before",
    "after", "above", "below", "to", "from", "up", "down", "in", "out", "on",
    "off", "over", "under", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "can", "could", "should", "would",
    "what", "how", "why", "who", "which", "when", "where", "this", "that", "these",
}


class RetrievalSufficiencyEvaluator:
    """
    Evaluates whether the evidence retrieved by Hyper-Lite is sufficient for answering
    the query given its structural complexity, entity requirements, and relational needs.
    """

    def __init__(
        self,
        threshold: Optional[int] = None,
        weights: Optional[SufficiencyWeights] = None,
        log_evaluations: Optional[bool] = None,
    ):
        self.threshold: int = (
            threshold
            if threshold is not None
            else ADAPTIVE_RETRIEVAL_SUFFICIENCY_THRESHOLD
        )
        self.weights: SufficiencyWeights = weights or SufficiencyWeights()
        self.log_evaluations: bool = (
            log_evaluations if log_evaluations is not None else ADAPTIVE_LOG_DECISIONS
        )

    def extract_metrics(
        self,
        query: str,
        entity_context: Optional[dict],
        features: Optional[dict] = None,
    ) -> RetrievalMetrics:
        """Extract quantifiable evidence metrics from retrieved context."""
        if not entity_context:
            return RetrievalMetrics(
                entity_count=0,
                hyperedge_count=0,
                text_unit_count=0,
                total_char_length=0,
                query_entity_coverage=0.0,
                lexical_overlap=0.0,
                duplicate_ratio=0.0,
                has_relational_evidence=False,
                retrieved_entity_names=[],
            )

        entities = entity_context.get("entities", []) or []
        hyperedges = entity_context.get("hyperedges", []) or []
        text_units = entity_context.get("text_units", []) or []

        retrieved_entity_names = [
            e.get("entity_name", "") for e in entities if e.get("entity_name")
        ]

        # Total text characters
        all_text = " ".join([t.get("content", "") for t in text_units])
        total_char_length = len(all_text)

        # 1. Query Entity Coverage
        detected_query_entities: List[str] = []
        if features and "detected_entities" in features:
            detected_query_entities = features["detected_entities"]
        else:
            detected_query_entities = QueryComplexityAnalyzer.extract_entities(query)

        if detected_query_entities:
            covered = 0
            all_text_lower = all_text.lower()
            ret_entities_lower = [e.lower() for e in retrieved_entity_names]
            for q_ent in detected_query_entities:
                q_ent_clean = q_ent.lower().replace("entity_", "").strip()
                if not q_ent_clean:
                    continue
                # Match against retrieved entity names or text chunk content
                if any(q_ent_clean in ret_e for ret_e in ret_entities_lower) or (q_ent_clean in all_text_lower):
                    covered += 1
            query_entity_coverage = covered / max(1, len(detected_query_entities))
        else:
            # Fallback to general content words coverage
            query_words = [
                w.lower().strip(string.punctuation)
                for w in query.split()
                if len(w) > 2 and w.lower() not in _STOPWORDS_SET
            ]
            if query_words:
                covered = sum(1 for w in query_words if w in all_text.lower())
                query_entity_coverage = covered / len(query_words)
            else:
                query_entity_coverage = 1.0

        # 2. Lexical Overlap
        query_words = set(
            w.lower().strip(string.punctuation)
            for w in query.split()
            if len(w) > 2 and w.lower() not in _STOPWORDS_SET
        )
        if query_words and all_text:
            text_words = set(all_text.lower().split())
            overlap_count = len(query_words.intersection(text_words))
            lexical_overlap = overlap_count / len(query_words)
        else:
            lexical_overlap = 0.0

        # 3. Duplicate ratio / text diversity
        duplicate_ratio = 0.0
        if len(text_units) > 1:
            contents = [t.get("content", "").strip() for t in text_units if t.get("content")]
            unique_contents = set(contents)
            duplicate_ratio = 1.0 - (len(unique_contents) / len(contents))
        elif len(text_units) == 1:
            duplicate_ratio = 0.0

        has_relational_evidence = len(hyperedges) > 0

        return RetrievalMetrics(
            entity_count=len(entities),
            hyperedge_count=len(hyperedges),
            text_unit_count=len(text_units),
            total_char_length=total_char_length,
            query_entity_coverage=query_entity_coverage,
            lexical_overlap=lexical_overlap,
            duplicate_ratio=duplicate_ratio,
            has_relational_evidence=has_relational_evidence,
            retrieved_entity_names=retrieved_entity_names,
        )

    def evaluate(
        self,
        query: str,
        entity_context: Optional[dict],
        features: Optional[dict] = None,
        complexity_score: Optional[int] = None,
    ) -> RetrievalSufficiency:
        """
        Evaluate retrieval sufficiency deterministically combining query requirements
        and retrieved evidence.
        """
        metrics = self.extract_metrics(query, entity_context, features=features)
        w = self.weights
        reasons: List[str] = []

        # Instant failure: Empty retrieval
        if metrics.text_unit_count == 0 and metrics.entity_count == 0:
            return RetrievalSufficiency(
                sufficient=False,
                score=0,
                threshold=self.threshold,
                confidence=1.0,
                reasons=["Empty retrieval: no entities or text units found"],
                metrics=metrics.to_dict(),
                query=query,
            )

        raw_score = 0.0

        # 1. Volume & Text Unit Count (max 25 pts)
        if metrics.text_unit_count >= 3:
            raw_score += w.text_unit_3_plus_pts
        elif metrics.text_unit_count == 2:
            raw_score += w.text_unit_2_pts
        elif metrics.text_unit_count == 1:
            raw_score += w.text_unit_1_pts
        else:
            raw_score += 0.0

        # 2. Query Entity Coverage (max 25 pts)
        cov_pts = metrics.query_entity_coverage * w.entity_coverage_max_pts
        raw_score += cov_pts
        if metrics.query_entity_coverage < 0.5:
            reasons.append(f"Low query entity coverage ({int(metrics.query_entity_coverage * 100)}%)")

        # 3. Context Length & Diversity (max 25 pts)
        len_pts = min(w.context_length_max_pts, (metrics.total_char_length / 250.0) * w.context_length_max_pts)
        raw_score += len_pts

        if metrics.duplicate_ratio > 0.5:
            dup_pen = metrics.duplicate_ratio * w.duplicate_penalty_max
            raw_score -= dup_pen
            reasons.append("Duplicate-heavy retrieval: repetitive text chunks")
        elif metrics.text_unit_count > 0:
            raw_score += w.diversity_bonus_pts

        # 4. Relationship Evidence (max 25 pts)
        # Check query complexity traits
        is_multi_hop = features.get("multi_hop", False) if features else False
        is_comparison = features.get("comparison", False) if features else False
        is_causal = features.get("causal_reasoning", False) if features else False
        query_needs_relations = is_multi_hop or is_comparison or is_causal

        if metrics.hyperedge_count >= 2:
            raw_score += w.hyperedge_2_plus_pts
        elif metrics.hyperedge_count == 1:
            raw_score += w.hyperedge_1_pts
        else:
            if not query_needs_relations:
                # Simple factual queries do not require hyperedges
                raw_score += w.hyperedge_simple_baseline_pts
            else:
                # Missing relations when needed
                raw_score += 0.0

        # 5. Targeted Penalties for Multi-Hop / Relational Requirements (Step 5)
        if is_multi_hop and metrics.hyperedge_count == 0:
            raw_score -= w.multi_hop_missing_relation_penalty
            reasons.append("Insufficient relationship evidence for multi-hop query")

        if is_comparison and metrics.query_entity_coverage < 0.7:
            raw_score -= w.comparison_missing_coverage_penalty
            reasons.append("Insufficient comparative entity coverage")

        if metrics.text_unit_count < 2 and (is_multi_hop or is_comparison):
            raw_score -= 10.0
            reasons.append("Insufficient text units for complex query")

        # Clamp score to [0, 100]
        final_score = int(min(100, max(0, round(raw_score))))
        sufficient = final_score >= self.threshold

        if sufficient:
            if not reasons:
                reasons.append("Sufficient evidence retrieved for query requirements")
        else:
            if not reasons:
                reasons.append(f"Retrieval evidence score {final_score} below threshold {self.threshold}")

        # Deterministic confidence based on margin from threshold
        if final_score >= self.threshold:
            denom = max(1, 100 - self.threshold)
            confidence = 0.5 + 0.5 * ((final_score - self.threshold) / denom)
        else:
            denom = max(1, self.threshold)
            confidence = 0.5 + 0.5 * ((self.threshold - final_score) / denom)
        confidence = round(min(1.0, max(0.5, confidence)), 2)

        return RetrievalSufficiency(
            sufficient=sufficient,
            score=final_score,
            threshold=self.threshold,
            confidence=confidence,
            reasons=reasons,
            metrics=metrics.to_dict(),
            query=query,
        )
