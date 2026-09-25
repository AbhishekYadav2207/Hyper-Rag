# -*- coding: utf-8 -*-
"""
Adaptive Hyper-RAG Router Module
Deterministically routes user queries to Hyper-Lite or Hyper-Core based on
transparent, interpretable complexity heuristics without making LLM routing calls.
"""

import re
import string
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional, Tuple, Literal, Set

from my_config import (
    ADAPTIVE_RAG_ENABLED,
    ADAPTIVE_RAG_MODE,
    ADAPTIVE_CORE_THRESHOLD,
    ADAPTIVE_LOG_DECISIONS,
)

logger = logging.getLogger("hyper_rag")


# =============================================================================
# 1. DATA STRUCTURES & SCHEMAS
# =============================================================================

@dataclass
class QueryFeatures:
    """Detailed structural and semantic features extracted from a query."""
    query_length: int
    word_count: int
    sentence_count: int
    question_count: int
    entity_count: int
    detected_entities: List[str]
    aspect_count: int
    aspect_signals: List[str]
    comparison: bool
    comparison_signals: List[str]
    causal_reasoning: bool
    causal_signals: List[str]
    temporal_reasoning: bool
    temporal_signals: List[str]
    multi_hop: bool
    multi_hop_signals: List[str]
    aggregation: bool
    aggregation_signals: List[str]
    detailed_depth: bool
    depth_signals: List[str]
    relationship_reasoning: bool
    relationship_signals: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Return features formatted for structured routing decision."""
        return {
            "entity_count": self.entity_count,
            "question_count": self.question_count,
            "comparison": self.comparison,
            "causal_reasoning": self.causal_reasoning,
            "temporal_reasoning": self.temporal_reasoning,
            "multi_hop": self.multi_hop,
            "aggregation": self.aggregation,
            "aspect_count": self.aspect_count,
            "query_length": self.query_length,
            "word_count": self.word_count,
            "sentence_count": self.sentence_count,
            "detailed_depth": self.detailed_depth,
            "relationship_reasoning": self.relationship_reasoning,
            "detected_entities": self.detected_entities,
        }


@dataclass
class AdaptiveDecision:
    """Structured decision returned by the Adaptive Router."""
    mode: Literal["lite", "core"]
    score: int
    threshold: int
    confidence: float
    reason: str
    reasons: List[str]
    features: Dict[str, Any]
    query: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "score": self.score,
            "threshold": self.threshold,
            "confidence": self.confidence,
            "reason": self.reason,
            "reasons": self.reasons,
            "features": self.features,
        }

    def format_log(self) -> str:
        """Format the decision for clean, readable logging without secrets."""
        if len(self.reasons) > 1:
            reasons_formatted = "\n".join(f"- {r}" for r in self.reasons)
            return (
                f"[Adaptive RAG]\n"
                f"Query complexity score: {self.score}\n"
                f"Selected mode: {self.mode}\n"
                f"Reasons:\n{reasons_formatted}"
            )
        else:
            return (
                f"[Adaptive RAG]\n"
                f"Query complexity score: {self.score}\n"
                f"Selected mode: {self.mode}\n"
                f"Reason: {self.reason}"
            )

    def format_evaluation(self) -> str:
        """Format decision for test evaluation output (Step 14)."""
        detected_items = []
        if self.features.get("comparison"):
            detected_items.append("comparison=True")
        if self.features.get("causal_reasoning"):
            detected_items.append("causal=True")
        if self.features.get("temporal_reasoning"):
            detected_items.append("temporal=True")
        if self.features.get("multi_hop"):
            detected_items.append("multi_hop=True")
        if self.features.get("aggregation"):
            detected_items.append("aggregation=True")
        if self.features.get("aspect_count", 0) > 1:
            detected_items.append("multi_aspect=True")
        if self.features.get("detailed_depth"):
            detected_items.append("depth=True")
        detected_items.append(f"entity_count={self.features.get('entity_count', 0)}")

        detected_str = "\n".join(detected_items)
        reasons_str = "\n".join(self.reasons) if self.reasons else self.reason

        return (
            f"Query:\n{self.query}\n\n"
            f"Score:\n{self.score}\n\n"
            f"Detected:\n{detected_str}\n\n"
            f"Selected:\n{self.mode.upper()}\n\n"
            f"Reasons:\n{reasons_str}"
        )


@dataclass
class ComplexityWeights:
    """Configurable weights for deterministic query complexity scoring."""
    # Feature category weights (0-100 scale components)
    comparison_weight: float = 20.0
    causal_weight: float = 15.0
    temporal_weight: float = 15.0
    multi_hop_weight: float = 15.0
    aggregation_weight: float = 15.0
    depth_weight: float = 12.0
    relationship_weight: float = 10.0

    # Entity count points
    entity_weight_1: float = 5.0
    entity_weight_2: float = 10.0
    entity_weight_3: float = 15.0
    entity_weight_4_plus: float = 20.0

    # Aspect count points
    aspect_weight_2: float = 8.0
    aspect_weight_3: float = 12.0
    aspect_weight_4_plus: float = 16.0

    # Structural points
    length_weight_max: float = 10.0
    sentence_weight_max: float = 6.0
    question_weight_max: float = 4.0


# =============================================================================
# 2. FEATURE EXTRACTION (LIGHTWEIGHT NLP HEURISTICS)
# =============================================================================

# Stopwords to filter during entity/topic extraction (lightweight set)
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

# Words indicating question instructions or meta-tasks to ignore when detecting entities
_META_FILTER_WORDS: Set[str] = {
    "compare", "comparison", "difference", "differences", "versus", "vs",
    "similar", "similarities", "similarity", "contrast", "cause", "causes",
    "effect", "effects", "impact", "influence", "consequence", "mechanism",
    "timeline", "evolution", "detail", "detailed", "depth", "overview",
    "summary", "summarize", "comprehensive", "explain", "describe", "discuss",
    "list", "tell", "analyze", "identify", "provide", "please", "give",
}


class QueryComplexityAnalyzer:
    """
    Analyzes queries to extract 12 interpretable structural and semantic signals
    using deterministic regex patterns and lightweight NLP heuristics without LLM calls.
    """

    # Feature 1: Multi-aspect signals
    ASPECT_PATTERNS = [
        re.compile(r"\b(?:and|also|additionally|as well as|along with|including|in terms of|covering|explain both|discuss both)\b", re.IGNORECASE),
        re.compile(r"\bboth\s+[\w\s]{2,25}?\s+and\s+[\w\s]{2,25}\b", re.IGNORECASE),
    ]

    # Feature 2: Comparison signals
    COMPARISON_PATTERNS = [
        re.compile(r"\b(?:compare|comparison|difference|differences|different from|versus|vs\.?|similar|similarities|similarity|contrast|contrasting|distinguish|distinguishing|better than|worse than|pros and cons|advantages and disadvantages|trade-offs?|differ)\b", re.IGNORECASE),
        re.compile(r"\bbetween\s+[\w\s]{2,30}?\s+and\s+[\w\s]{2,30}\b", re.IGNORECASE),
    ]

    # Feature 3: Causal / Explanatory reasoning signals
    CAUSAL_PATTERNS = [
        re.compile(r"\b(?:why|how does|how do|how did|how can|how could|what causes|causes?|caused by|cause of|effects?|impacts?|influence[sd]?|consequence[s]?|resulting in|results in|leads? to|led to|mechanisms?|underlying reason[s]?|root cause[s]?|rationale|factors? that led to|contribute[sd]? to|contributing to)\b", re.IGNORECASE),
    ]

    # Feature 4: Temporal reasoning signals
    TEMPORAL_PATTERNS = [
        re.compile(r"\b(?:before|after|during|over time|timeline|progression|historically|historical|trends?|changes? over time|evolution|evolving|initially|eventually|subsequently|previous|previously|later|current vs past|past vs present|chronology|chronological|decades?|centur(?:y|ies))\b", re.IGNORECASE),
        re.compile(r"\b(?:since \d{4}|from \d{4} to \d{4}|\d{4}s)\b", re.IGNORECASE),
    ]

    # Feature 5: Multi-hop reasoning signals
    MULTI_HOP_PATTERNS = [
        re.compile(r"\b(?:relationship between|connection between|connected to|through which|leads to|associated with|indirectly|chain of|downstream|upstream|interconnect(?:ed|ion)?|interplay|pathway|cascade|correlated with|interaction between)\b", re.IGNORECASE),
        re.compile(r"\bhow\s+[\w\s]{2,25}?\s+(?:affects?|influences?|impacts?)\s+[\w\s]{2,25}\b", re.IGNORECASE),
        re.compile(r"\bthrough\s+(?:the\s+|a\s+)?(?:mechanism|pathway|process|channel|intermediary|factor|agent)\b", re.IGNORECASE),
        re.compile(r"\b(?:affect|affects|influence|influences|impact|impacts)\s+[\w\s]{1,25}?\s+through\b", re.IGNORECASE),
    ]

    # Feature 6: Aggregation / Synthesis signals
    AGGREGATION_PATTERNS = [
        re.compile(r"\b(?:summarize all|summary of all|list all|identify all|identify multiple|across (?:all|multiple|different)|among (?:all|the various)|overall|combined|collectively|from multiple sources|synthesize|synthesis|integrate|integration|comprehensive overview|all factors|all causes|all the ways|aggregate|enumerate all)\b", re.IGNORECASE),
    ]

    # Feature 7: Relationship signals
    RELATIONSHIP_PATTERNS = [
        re.compile(r"\b(?:relationship|relationships|related to|relate to|correlation|correlations|link between|linked to|association|associations)\b", re.IGNORECASE),
    ]

    # Feature 8: Requested depth signals
    DEPTH_PATTERNS = [
        re.compile(r"\b(?:detailed|in-depth|in depth|deeply|thoroughly|thorough|explain fully|exhaustive|step by step|step-by-step|complete analysis|comprehensive|elaborate|rigorous|full breakdown|extensive)\b", re.IGNORECASE),
    ]

    @classmethod
    def extract_entities(cls, query: str) -> List[str]:
        """
        Lightweight entity & meaningful topic phrase extraction without heavyweight NER.
        Extracts:
        1. Quoted terms ("...")
        2. Proper nouns / capitalized phrases (e.g. Eiffel Tower, Marie Curie, NASA)
        3. Symbolic variables (e.g. treatment A, condition B, mechanism C, A cause B)
        4. Significant content noun phrases after stopword and question-prefix filtering.
        """
        entities: List[str] = []

        # 1. Quoted terms
        quoted = re.findall(r'["\']([^"\']{2,40})["\']', query)
        for q in quoted:
            cleaned = q.strip()
            if cleaned and cleaned.lower() not in _STOPWORDS:
                entities.append(cleaned)

        # 2a. Symbolic entities / variables
        symbolic_pairs = re.findall(
            r"\b(?:treatment|condition|mechanism|factor|drug|patient|variable|group|component|disease|symptom)\s+([A-Za-z0-9])\b",
            query,
            re.IGNORECASE,
        )
        for sp in symbolic_pairs:
            entities.append(f"entity_{sp.upper()}")

        symbolic_rel = re.findall(
            r"\b(?:between|cause|causes|affects?|influences?|and|vs|versus)\s+([A-Z])\b",
            query,
        )
        for sr in symbolic_rel:
            entities.append(f"entity_{sr}")

        symbolic_subj = re.findall(
            r"\b([A-Z])\s+(?:cause|causes|affects?|influences?|leads?\s+to)\b",
            query,
        )
        for ss in symbolic_subj:
            entities.append(f"entity_{ss}")

        # 2b. Capitalized phrases & acronyms (exclude first word if simply capitalized at sentence start)
        cap_matches = re.finditer(r"\b[A-Z][a-zA-Z0-9]*(?:\s+[A-Z][a-zA-Z0-9]*)*\b", query)
        for m in cap_matches:
            match_str = m.group(0).strip()
            # If it's at index 0 and followed by lowercase, it might just be the first word capitalized
            if m.start() == 0 and len(match_str.split()) == 1 and match_str.lower() in _STOPWORDS:
                continue
            if match_str.lower() not in _STOPWORDS and match_str.lower() not in _META_FILTER_WORDS:
                if len(match_str) > 1:
                    entities.append(match_str)

        # 3. Strip leading question phrases to extract core content nouns
        stripped = re.sub(
            r"^(?:what\s+(?:is|are|was|were)|who\s+(?:is|was|are|were)|where\s+(?:is|was|can|are)|how\s+(?:does|do|did|can|could|is|are)|why\s+(?:is|was|are|do|does|did)|can\s+you\s+(?:explain|describe|tell\s+me\s+about)|tell\s+me\s+about|explain|describe|discuss|summarize)\b\s*",
            "",
            query,
            flags=re.IGNORECASE,
        )

        # Split into tokens and remove punctuation
        clean_text = stripped.translate(str.maketrans("", "", string.punctuation))
        tokens = clean_text.split()

        # Gather consecutive non-stopwords into noun phrases
        current_chunk: List[str] = []
        for t in tokens:
            t_low = t.lower()
            if t_low not in _STOPWORDS and t_low not in _META_FILTER_WORDS and len(t_low) > 1:
                current_chunk.append(t)
            else:
                if current_chunk:
                    entities.append(" ".join(current_chunk))
                    current_chunk = []
        if current_chunk:
            entities.append(" ".join(current_chunk))

        # Deduplicate while preserving case and order
        seen_lower = set()
        unique_entities: List[str] = []
        for e in entities:
            e_clean = e.strip()
            e_lower = e_clean.lower()
            if e_clean and e_lower not in seen_lower and len(e_clean) > 1:
                seen_lower.add(e_lower)
                unique_entities.append(e_clean)

        return unique_entities

    @classmethod
    def analyze(cls, query: str) -> QueryFeatures:
        """Analyze query text and return QueryFeatures."""
        q_clean = query.strip()
        words = q_clean.split()
        word_count = len(words)
        query_length = len(q_clean)

        # Sentence count (split on . ! ? or newline)
        sentences = [s.strip() for s in re.split(r"[.!?\n]+", q_clean) if s.strip()]
        sentence_count = max(1, len(sentences))

        # Question marks
        question_count = q_clean.count("?")
        if question_count == 0 and any(q_clean.lower().startswith(w) for w in ["what", "who", "where", "how", "why", "which"]):
            question_count = 1

        # Entities
        detected_entities = cls.extract_entities(q_clean)
        entity_count = len(detected_entities)

        # Aspect detection
        aspect_signals: List[str] = []
        for p in cls.ASPECT_PATTERNS:
            matches = p.findall(q_clean)
            if matches:
                aspect_signals.extend([m if isinstance(m, str) else m[0] for m in matches])

        # Comma list detection (e.g., "causes, symptoms, diagnosis, treatment, and prevention")
        comma_items = [c.strip() for c in q_clean.split(",") if c.strip()]
        aspect_count = max(1, len(comma_items)) if len(comma_items) >= 2 else (2 if aspect_signals else 1)

        # Feature 2: Comparison
        comparison_signals: List[str] = []
        for p in cls.COMPARISON_PATTERNS:
            m = p.findall(q_clean)
            if m:
                comparison_signals.extend([s if isinstance(s, str) else s[0] for s in m])
        comparison = len(comparison_signals) > 0

        # Feature 3: Causal
        causal_signals: List[str] = []
        for p in cls.CAUSAL_PATTERNS:
            m = p.findall(q_clean)
            if m:
                causal_signals.extend([s if isinstance(s, str) else s[0] for s in m])
        causal_reasoning = len(causal_signals) > 0

        # Feature 4: Temporal
        temporal_signals: List[str] = []
        for p in cls.TEMPORAL_PATTERNS:
            m = p.findall(q_clean)
            if m:
                temporal_signals.extend([s if isinstance(s, str) else s[0] for s in m])
        temporal_reasoning = len(temporal_signals) > 0

        # Feature 5: Multi-hop
        multi_hop_signals: List[str] = []
        for p in cls.MULTI_HOP_PATTERNS:
            m = p.findall(q_clean)
            if m:
                multi_hop_signals.extend([s if isinstance(s, str) else s[0] for s in m])
        # If query connects multiple entities with causal or comparison relations, multi-hop is implied
        if entity_count >= 3 and (causal_reasoning or comparison):
            if not multi_hop_signals:
                multi_hop_signals.append("multi-entity relationship pathway")
        multi_hop = len(multi_hop_signals) > 0

        # Feature 6: Aggregation
        aggregation_signals: List[str] = []
        for p in cls.AGGREGATION_PATTERNS:
            m = p.findall(q_clean)
            if m:
                aggregation_signals.extend([s if isinstance(s, str) else s[0] for s in m])
        aggregation = len(aggregation_signals) > 0

        # Feature 7: Relationship
        relationship_signals: List[str] = []
        for p in cls.RELATIONSHIP_PATTERNS:
            m = p.findall(q_clean)
            if m:
                relationship_signals.extend([s if isinstance(s, str) else s[0] for s in m])
        relationship_reasoning = len(relationship_signals) > 0

        # Feature 8: Requested depth
        depth_signals: List[str] = []
        for p in cls.DEPTH_PATTERNS:
            m = p.findall(q_clean)
            if m:
                depth_signals.extend([s if isinstance(s, str) else s[0] for s in m])
        detailed_depth = len(depth_signals) > 0

        return QueryFeatures(
            query_length=query_length,
            word_count=word_count,
            sentence_count=sentence_count,
            question_count=question_count,
            entity_count=entity_count,
            detected_entities=detected_entities,
            aspect_count=aspect_count,
            aspect_signals=aspect_signals,
            comparison=comparison,
            comparison_signals=comparison_signals,
            causal_reasoning=causal_reasoning,
            causal_signals=causal_signals,
            temporal_reasoning=temporal_reasoning,
            temporal_signals=temporal_signals,
            multi_hop=multi_hop,
            multi_hop_signals=multi_hop_signals,
            aggregation=aggregation,
            aggregation_signals=aggregation_signals,
            detailed_depth=detailed_depth,
            depth_signals=depth_signals,
            relationship_reasoning=relationship_reasoning,
            relationship_signals=relationship_signals,
        )


# =============================================================================
# 3. MODULAR SCORING ENGINE
# =============================================================================

class BaseComplexityScorer(ABC):
    """Abstract interface for query complexity scoring, enabling modular future classifiers."""

    @abstractmethod
    def score(
        self, features: QueryFeatures, threshold: int
    ) -> Tuple[int, List[str], str, float]:
        """
        Calculates complexity score, reasons, primary reason, and confidence.
        Returns:
            Tuple of (score: int [0-100], reasons: List[str], primary_reason: str, confidence: float)
        """
        pass


class HeuristicComplexityScorer(BaseComplexityScorer):
    """
    Transparent, deterministic weighted scoring implementation using interpretable signals.
    """

    def __init__(self, weights: Optional[ComplexityWeights] = None):
        self.weights = weights or ComplexityWeights()

    def score(
        self, features: QueryFeatures, threshold: int
    ) -> Tuple[int, List[str], str, float]:
        raw_score: float = 0.0
        reasons: List[str] = []

        w = self.weights

        # 1. Structural Length & Sentences
        length_pts = min(w.length_weight_max, features.word_count * 0.35)
        raw_score += length_pts

        if features.sentence_count > 1:
            sent_pts = min(w.sentence_weight_max, (features.sentence_count - 1) * 3.0)
            raw_score += sent_pts

        if features.question_count > 1:
            q_pts = min(w.question_weight_max, (features.question_count - 1) * 2.0)
            raw_score += q_pts
            reasons.append(f"{features.question_count} question marks / clauses")

        # 2. Entity Count
        if features.entity_count == 1:
            raw_score += w.entity_weight_1
        elif features.entity_count == 2:
            raw_score += w.entity_weight_2
            reasons.append("multiple entities (2 detected)")
        elif features.entity_count == 3:
            raw_score += w.entity_weight_3
            reasons.append("multiple entities (3 detected)")
        elif features.entity_count >= 4:
            raw_score += w.entity_weight_4_plus
            reasons.append(f"multiple entities ({features.entity_count} detected)")

        # 3. Multi-aspect
        if features.aspect_count >= 4:
            raw_score += w.aspect_weight_4_plus
            reasons.append(f"multiple requested aspects ({features.aspect_count} aspects)")
        elif features.aspect_count == 3:
            raw_score += w.aspect_weight_3
            reasons.append("multiple requested aspects (3 aspects)")
        elif features.aspect_count == 2 or features.aspect_signals:
            raw_score += w.aspect_weight_2
            reasons.append("multiple requested aspects")

        # 4. Comparison
        if features.comparison:
            raw_score += w.comparison_weight
            reasons.append("comparison detected")

        # 5. Causal Reasoning
        if features.causal_reasoning:
            raw_score += w.causal_weight
            reasons.append("causal reasoning detected")

        # 6. Temporal Reasoning
        if features.temporal_reasoning:
            raw_score += w.temporal_weight
            reasons.append("temporal reasoning detected")

        # 7. Multi-hop Reasoning
        if features.multi_hop:
            raw_score += w.multi_hop_weight
            reasons.append("multi-hop structure detected")

        # 8. Aggregation / Synthesis
        if features.aggregation:
            raw_score += w.aggregation_weight
            reasons.append("aggregation / synthesis requested")

        # 9. Relationship Reasoning (if not already counted under multi-hop/causal)
        if features.relationship_reasoning and not features.multi_hop and not features.causal_reasoning:
            raw_score += w.relationship_weight
            reasons.append("relationship reasoning detected")

        # 10. Requested Depth
        if features.detailed_depth:
            raw_score += w.depth_weight
            reasons.append("detailed in-depth analysis requested")

        # Clamp score to [0, 100]
        final_score = int(min(100, max(0, round(raw_score))))

        # Determine primary reason summary
        if final_score >= threshold:
            if reasons:
                primary_reason = f"High-complexity query: {', '.join(reasons[:3])}"
            else:
                primary_reason = "Complex query exceeding threshold"
        else:
            if final_score <= 25 and features.entity_count <= 1:
                primary_reason = "Simple single-entity factual query"
            elif final_score <= 35:
                primary_reason = "Low-complexity direct factual query"
            else:
                primary_reason = "Moderate complexity query within Lite processing capacity"

        # Deterministic, monotonic confidence heuristic based on distance from threshold
        if final_score >= threshold:
            denom = max(1, 100 - threshold)
            confidence = 0.5 + 0.5 * ((final_score - threshold) / denom)
        else:
            denom = max(1, threshold)
            confidence = 0.5 + 0.5 * ((threshold - final_score) / denom)
        confidence = round(min(1.0, max(0.5, confidence)), 2)

        return final_score, reasons, primary_reason, confidence


# =============================================================================
# 4. ADAPTIVE ROUTER CONTROLLER
# =============================================================================

class AdaptiveRouter:
    """
    Adaptive Hyper-RAG Controller.
    Determines whether a user query should be executed using:
    - Hyper-Lite
    or
    - Hyper-Core
    based on transparent, configurable complexity heuristics.
    """

    def __init__(
        self,
        core_threshold: Optional[int] = None,
        weights: Optional[ComplexityWeights] = None,
        scorer: Optional[BaseComplexityScorer] = None,
        log_decisions: Optional[bool] = None,
    ):
        self.core_threshold: int = (
            core_threshold if core_threshold is not None else ADAPTIVE_CORE_THRESHOLD
        )
        self.weights: ComplexityWeights = weights or ComplexityWeights()
        self.scorer: BaseComplexityScorer = (
            scorer or HeuristicComplexityScorer(weights=self.weights)
        )
        self.log_decisions: bool = (
            log_decisions if log_decisions is not None else ADAPTIVE_LOG_DECISIONS
        )

    def analyze_query(self, query: str) -> QueryFeatures:
        """Extract interpretable structural and semantic query features."""
        return QueryComplexityAnalyzer.analyze(query)

    def calculate_complexity(
        self, query: str, features: Optional[QueryFeatures] = None
    ) -> Tuple[int, List[str], str, float, QueryFeatures]:
        """Calculate complexity score and explainable reasons for a query."""
        feat = features or self.analyze_query(query)
        score, reasons, primary_reason, confidence = self.scorer.score(
            feat, threshold=self.core_threshold
        )
        return score, reasons, primary_reason, confidence, feat

    def select_mode(self, score: int) -> Literal["lite", "core"]:
        """Determine mode from score and threshold."""
        return "core" if score >= self.core_threshold else "lite"

    def route(self, query: str) -> AdaptiveDecision:
        """
        Analyze query and return structured AdaptiveDecision.
        Logs routing decision cleanly if log_decisions is True.
        """
        features = self.analyze_query(query)
        score, reasons, primary_reason, confidence, _ = self.calculate_complexity(
            query, features=features
        )
        mode = self.select_mode(score)

        decision = AdaptiveDecision(
            mode=mode,
            score=score,
            threshold=self.core_threshold,
            confidence=confidence,
            reason=primary_reason,
            reasons=reasons,
            features=features.to_dict(),
            query=query,
        )

        if self.log_decisions:
            log_text = decision.format_log()
            logger.info(log_text)
            # Avoid printing secrets; only print formatted decision to console
            print(log_text)

        return decision

    def inspect_query(self, query: str) -> str:
        """
        Evaluate query and return human-readable Step 14 evaluation output.
        """
        prev_log = self.log_decisions
        try:
            self.log_decisions = False
            decision = self.route(query)
            return decision.format_evaluation()
        finally:
            self.log_decisions = prev_log


# Component aliases conforming to project abstractions
QueryFeatureExtractor = QueryComplexityAnalyzer
ComplexityScorer = HeuristicComplexityScorer
