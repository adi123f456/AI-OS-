"""
AI OS — Fact Checker
Adds confidence scores, source citations, and verification tags to AI responses.
"""

import re
from typing import Dict, List, Any, Optional


class FactChecker:
    """
    Analyzes AI responses for factual claims and adds confidence metadata.
    Uses heuristic analysis since we don't have a live fact-checking API.
    """

    # Phrases that typically indicate uncertainty
    UNCERTAIN_PHRASES = [
        "i think", "i believe", "probably", "might", "could be",
        "it's possible", "not sure", "approximately", "roughly",
        "generally", "in most cases", "typically", "usually",
        "as far as i know", "i'm not certain",
    ]

    # Phrases that indicate higher confidence
    CONFIDENT_PHRASES = [
        "according to", "based on", "research shows",
        "studies show", "it is known", "factually",
        "has been proven", "officially", "documented",
    ]

    # Claim indicator patterns
    CLAIM_PATTERNS = [
        r"(?:is|are|was|were)\s+(?:the|a)\s+.+",
        r"\d+%\s+of",
        r"in\s+\d{4}",
        r"(?:first|largest|smallest|oldest|newest|most|least)",
        r"(?:invented|discovered|founded|created)\s+(?:in|by)",
    ]

    def analyze(self, response_text: str) -> Dict[str, Any]:
        """
        Analyze an AI response for factual claims and confidence.

        Returns:
            {
                "confidence": float (0.0-1.0),
                "claims_count": int,
                "verification_tags": [...],
                "sources_suggested": [...],
                "analysis": str
            }
        """
        text_lower = response_text.lower()

        # Count uncertainty indicators
        uncertainty_count = sum(
            1 for phrase in self.UNCERTAIN_PHRASES
            if phrase in text_lower
        )

        # Count confidence indicators
        confidence_count = sum(
            1 for phrase in self.CONFIDENT_PHRASES
            if phrase in text_lower
        )

        # Count factual claims
        claims = self._extract_claims(response_text)

        # Calculate confidence score
        base_confidence = 0.7
        confidence = base_confidence
        confidence -= uncertainty_count * 0.08
        confidence += confidence_count * 0.05
        confidence = max(0.1, min(1.0, confidence))

        # Determine verification tags
        tags = self._get_verification_tags(confidence, claims, response_text)

        # Suggest sources
        sources = self._suggest_sources(response_text)

        # Build analysis summary
        if confidence >= 0.8:
            analysis = "Response appears factually grounded with high confidence."
        elif confidence >= 0.5:
            analysis = "Response contains claims that may benefit from verification."
        else:
            analysis = "Response contains significant uncertainty. Independent verification recommended."

        return {
            "confidence": round(confidence, 2),
            "claims_count": len(claims),
            "claims": claims[:5],  # Top 5 claims
            "verification_tags": tags,
            "sources_suggested": sources,
            "analysis": analysis,
        }

    def _extract_claims(self, text: str) -> List[str]:
        """Extract sentences that appear to contain factual claims."""
        sentences = re.split(r'[.!?]+', text)
        claims = []

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence or len(sentence) < 20:
                continue

            # Check if sentence contains claim patterns
            for pattern in self.CLAIM_PATTERNS:
                if re.search(pattern, sentence, re.IGNORECASE):
                    claims.append(sentence[:150])
                    break

        return claims

    def _get_verification_tags(
        self,
        confidence: float,
        claims: List[str],
        text: str,
    ) -> List[Dict[str, str]]:
        """Generate verification tags based on analysis."""
        tags = []

        if confidence >= 0.8:
            tags.append({"tag": "VERIFIED", "color": "green", "note": "High confidence response"})
        elif confidence >= 0.5:
            tags.append({"tag": "REVIEW", "color": "yellow", "note": "Contains unverified claims"})
        else:
            tags.append({"tag": "UNVERIFIED", "color": "red", "note": "Low confidence — verify independently"})

        if len(claims) > 5:
            tags.append({"tag": "CLAIM_HEAVY", "color": "yellow", "note": f"{len(claims)} factual claims detected"})

        # Check for code
        if "```" in text:
            tags.append({"tag": "CODE", "color": "blue", "note": "Contains code — test before using"})

        # Check for numbers/statistics
        if re.search(r'\d+(?:\.\d+)?%', text):
            tags.append({"tag": "STATISTICS", "color": "yellow", "note": "Contains statistics — verify data"})

        return tags

    def _suggest_sources(self, text: str) -> List[Dict[str, str]]:
        """Suggest relevant source types based on content."""
        suggestions = []
        text_lower = text.lower()

        topic_sources = {
            "programming": {"source": "Official documentation", "type": "docs"},
            "python": {"source": "docs.python.org", "type": "docs"},
            "javascript": {"source": "developer.mozilla.org", "type": "docs"},
            "science": {"source": "Google Scholar", "type": "academic"},
            "medical": {"source": "PubMed / WHO", "type": "medical"},
            "health": {"source": "WHO / CDC", "type": "medical"},
            "history": {"source": "Wikipedia / Academic sources", "type": "reference"},
            "legal": {"source": "Legal databases", "type": "legal"},
            "financial": {"source": "SEC / Financial reports", "type": "financial"},
            "machine learning": {"source": "arXiv / Papers With Code", "type": "academic"},
        }

        for topic, source_info in topic_sources.items():
            if topic in text_lower:
                suggestions.append(source_info)

        return suggestions[:3]  # Limit to 3 suggestions

    def enrich_response(self, response_text: str, include_analysis: bool = True) -> Dict[str, Any]:
        """
        Enrich a response with fact-checking metadata.
        Returns the response with added confidence/source data.
        """
        analysis = self.analyze(response_text)

        result = {
            "content": response_text,
            "confidence": analysis["confidence"],
            "verification_tags": analysis["verification_tags"],
        }

        if include_analysis:
            result["fact_check"] = {
                "claims_found": analysis["claims_count"],
                "top_claims": analysis["claims"],
                "sources_suggested": analysis["sources_suggested"],
                "analysis": analysis["analysis"],
            }

        return result


# Singleton
fact_checker = FactChecker()
