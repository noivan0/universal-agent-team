"""
Technology Stack Detection System

Detects frontend and backend technologies from natural language project descriptions.
Uses both explicit pattern matching and implicit inference.
"""

from typing import Dict, Optional, Literal
from dataclasses import dataclass


@dataclass
class TechStackResult:
    """Result of tech stack detection."""
    frontend: Optional[str]
    backend: Optional[str]
    detected_from: Literal["explicit", "implicit", "both"]
    confidence: float
    patterns_matched: list[str]


class TechStackDetector:
    """Detects technology stack from project descriptions."""

    # Explicit patterns with high confidence
    FRONTEND_EXPLICIT = {
        r'\breact\b': 'react',
        r'\breact\s*native\b': 'react-native',
        r'\bvue\b': 'vue',
        r'\bsvelte\b': 'svelte',
        r'\bangular\b': 'angular',
        r'\bflutter\b': 'flutter',
        r'\bswiftui\b': 'swiftui',
        r'\bkotlin\b': 'kotlin',
    }

    BACKEND_EXPLICIT = {
        r'\bfastapi\b': 'fastapi',
        r'\bdjango\b': 'django',
        r'\bflask\b': 'flask',
        r'\bnode\.?js\b': 'nodejs',
        r'\bexpress\b': 'nodejs',
        r'\bfastify\b': 'nodejs',
        r'\bgo\b': 'go',
        r'\bruby\s*on\s*rails\b': 'rails',
        r'\brails\b': 'rails',
        r'\bspring\b': 'java',
        r'\b\.net\b': 'dotnet',
        r'\bc#\b': 'dotnet',
    }

    # Implicit patterns for inference
    IMPLICIT_PATTERNS = {
        'real-time': ['nodejs', 'fastapi'],
        'mobile': ['react-native', 'flutter', 'kotlin'],
        'scalable': ['nodejs', 'fastapi', 'go'],
        'microservices': ['go', 'fastapi', 'nodejs'],
        'websocket': ['nodejs', 'fastapi'],
        'concurrent': ['nodejs', 'fastapi', 'go'],
        'high load': ['nodejs', 'fastapi', 'go'],
        'machine learning': ['fastapi', 'django'],
        'data processing': ['fastapi', 'django'],
        'dashboard': ['react', 'vue'],
        'visualization': ['react', 'vue'],
    }

    def detect_tech_stack(self, user_request: str) -> TechStackResult:
        """
        Detect technology stack from user request.

        Args:
            user_request: Natural language project description

        Returns:
            TechStackResult with detected technologies
        """
        import re

        request_lower = user_request.lower()

        # Check for explicit matches
        frontend = self._match_explicit(request_lower, self.FRONTEND_EXPLICIT)
        backend = self._match_explicit(request_lower, self.BACKEND_EXPLICIT)

        patterns_matched = []
        if frontend:
            patterns_matched.append(f"frontend: {frontend}")
        if backend:
            patterns_matched.append(f"backend: {backend}")

        # If no explicit matches, try implicit inference
        if not frontend or not backend:
            implicit_backend = self._infer_implicit(request_lower)
            if not backend and implicit_backend:
                backend = implicit_backend
                patterns_matched.append(f"inferred backend: {backend}")

            # Default frontend inference
            if not frontend and 'mobile' in request_lower:
                frontend = 'react-native'
                patterns_matched.append("inferred frontend: react-native")
            elif not frontend and any(x in request_lower for x in ['dashboard', 'visualization', 'ui', 'interface']):
                frontend = 'react'
                patterns_matched.append("inferred frontend: react")

        detected_from = self._determine_detection_source(frontend, backend, user_request)
        confidence = self._calculate_confidence(patterns_matched)

        return TechStackResult(
            frontend=frontend,
            backend=backend,
            detected_from=detected_from,
            confidence=confidence,
            patterns_matched=patterns_matched
        )

    def _match_explicit(self, text: str, patterns: Dict[str, str]) -> Optional[str]:
        """Match explicit technology patterns."""
        import re
        for pattern, tech in patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                return tech
        return None

    def _infer_implicit(self, text: str) -> Optional[str]:
        """Infer backend technology from implicit patterns."""
        for keyword, technologies in self.IMPLICIT_PATTERNS.items():
            if keyword in text:
                # Return the first (most commonly used) option
                return technologies[0]
        return None

    def _determine_detection_source(self, frontend: str, backend: str, original: str) -> str:
        """Determine if detection was explicit or implicit."""
        has_explicit = any(
            term.lower() in original.lower()
            for terms in [self.FRONTEND_EXPLICIT.keys(), self.BACKEND_EXPLICIT.keys()]
            for term in terms
        )

        if has_explicit:
            return "explicit"
        elif frontend or backend:
            return "implicit"
        return "explicit"

    def _calculate_confidence(self, patterns: list[str]) -> float:
        """Calculate confidence score based on number of matches."""
        # More patterns matched = higher confidence
        base = 0.7
        bonus = min(0.3, len(patterns) * 0.1)
        return min(1.0, base + bonus)
