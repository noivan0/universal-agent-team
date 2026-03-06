"""
Specialization loader for multi-technology support.

Manages:
- Tech stack detection from user requests
- Specialization file selection
- Fallback strategies for unsupported stacks
- Specialization manifest management
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ============================================================================
# Technology Stack Detection
# ============================================================================

class TechStackDetector:
    """Detects technology stack from user requests and context."""

    # Explicit keywords that indicate specific technologies
    EXPLICIT_KEYWORDS = {
        # Frontend technologies
        "react": ["react", "react.js", "reactjs"],
        "react-native": ["react native", "react-native", "mobile app"],
        "vue": ["vue", "vue.js", "vuejs"],
        "svelte": ["svelte", "sveltekit"],
        "angular": ["angular", "angularjs"],
        "nextjs": ["next.js", "nextjs", "next"],

        # Backend technologies
        "fastapi": ["fastapi", "fast api", "python api"],
        "nodejs": ["node.js", "nodejs", "node", "javascript backend"],
        "express": ["express", "express.js"],
        "django": ["django", "django rest framework", "drf"],
        "go": ["go", "golang", "go lang"],
        "rust": ["rust", "actix", "rocket"],
        "java": ["java", "spring boot", "spring"],

        # Implicit indicators
        "mobile": ["mobile", "ios", "android"],
        "realtime": ["real-time", "realtime", "websocket", "socket.io"],
        "microservices": ["microservices", "micro-services"],
    }

    # Implicit rules (context → tech stack)
    IMPLICIT_RULES = {
        "mobile": {
            "frontend": "react-native",
            "reason": "mobile app → React Native"
        },
        "realtime": {
            "backend": "nodejs",
            "reason": "real-time data → Node.js (native WebSocket support)"
        },
        "microservices": {
            "backend": "go",
            "reason": "microservices → Go (lightweight, concurrent)"
        },
    }

    @staticmethod
    def detect_tech_stack(
        user_request: str,
        context: Optional[str] = None
    ) -> Dict[str, Optional[str]]:
        """
        Detect technology stack from user request.

        Args:
            user_request: User's project description
            context: Optional additional context

        Returns:
            {
                "frontend": "react" | "react-native" | "vue" | "svelte" | None,
                "backend": "fastapi" | "nodejs" | "django" | "go" | None,
                "detected_from": "explicit" | "implicit"
            }
        """
        combined = f"{user_request} {context or ''}".lower()

        # Search for explicit keywords
        detected_frontend = None
        detected_backend = None
        detected_from = "implicit"

        # Check frontend technologies
        for tech in ["react", "react-native", "vue", "svelte", "nextjs"]:
            keywords = TechStackDetector.EXPLICIT_KEYWORDS.get(tech, [])
            if any(keyword in combined for keyword in keywords):
                detected_frontend = tech
                detected_from = "explicit"
                break

        # Check backend technologies
        for tech in ["fastapi", "nodejs", "express", "django", "go"]:
            keywords = TechStackDetector.EXPLICIT_KEYWORDS.get(tech, [])
            if any(keyword in combined for keyword in keywords):
                detected_backend = tech
                detected_from = "explicit"
                break

        # Check implicit indicators
        for indicator, rule in TechStackDetector.IMPLICIT_RULES.items():
            if indicator in combined:
                keywords = TechStackDetector.EXPLICIT_KEYWORDS.get(indicator, [])
                if any(keyword in combined for keyword in keywords):
                    if not detected_frontend and "frontend" in rule:
                        detected_frontend = rule["frontend"]
                    if not detected_backend and "backend" in rule:
                        detected_backend = rule["backend"]
                    detected_from = "implicit"

        return {
            "frontend": detected_frontend,
            "backend": detected_backend,
            "detected_from": detected_from
        }


# ============================================================================
# Complexity Scoring
# ============================================================================

class ComplexityScorer:
    """Scores project complexity based on features and requirements."""

    COMPLEXITY_FACTORS = {
        # Data-related
        "real-time": 20,
        "live data": 20,
        "streaming": 20,
        "websocket": 20,

        # Architecture
        "microservice": 25,
        "distributed": 25,
        "scalable": 15,
        "high-load": 20,

        # Features
        "authentication": 10,
        "oauth": 15,
        "multi-tenant": 15,
        "multi-tenancy": 15,
        "payment": 15,
        "payment processing": 15,

        # Database
        "complex": 10,
        "relational": 5,
        "nosql": 5,
        "caching": 10,
        "redis": 10,

        # Performance
        "optimization": 10,
        "performant": 10,
        "fast": 5,

        # Integration
        "integration": 10,
        "api integration": 10,
        "external": 10,

        # Compliance
        "gdpr": 15,
        "compliance": 15,
        "security": 15,
    }

    @staticmethod
    def calculate_complexity(
        user_request: str,
        context: Optional[str] = None
    ) -> Tuple[int, List[str]]:
        """
        Calculate project complexity score.

        Args:
            user_request: User's project description
            context: Optional additional context

        Returns:
            (complexity_score, factors_list)
            complexity_score: 1-100
        """
        combined = f"{user_request} {context or ''}".lower()
        score = 50  # Base score

        detected_factors = []

        for factor, points in ComplexityScorer.COMPLEXITY_FACTORS.items():
            if factor in combined:
                score += points
                detected_factors.append(factor)

        # Cap score at 100
        score = min(score, 100)
        score = max(score, 1)

        return score, detected_factors


# ============================================================================
# Specialization Loader
# ============================================================================

class SpecializationLoader:
    """Loads and manages specialization files for agents."""

    AGENTS_BASE = Path("/workspace/agents")

    SUPPORTED_SPECIALIZATIONS = {
        "frontend": {
            "react": "react-typescript",
            "react-native": "react-native",
            "vue": "vue",
            "svelte": "svelte",
        },
        "backend": {
            "fastapi": "fastapi-python",
            "nodejs": "node-express",
            "express": "node-express",
            "django": "django",
            "go": "go",
        }
    }

    @staticmethod
    def get_specialization_path(
        agent_type: str,  # "frontend" or "backend"
        specialization: str
    ) -> Optional[Path]:
        """
        Get path to specialization file.

        Args:
            agent_type: "frontend" or "backend"
            specialization: Specialization name (e.g., "react", "fastapi")

        Returns:
            Path to specialization file or None if not found
        """
        # Normalize specialization name
        spec_name = SpecializationLoader.SUPPORTED_SPECIALIZATIONS.get(
            agent_type, {}
        ).get(specialization, specialization)

        # Construct path
        spec_path = (
            SpecializationLoader.AGENTS_BASE
            / f"{agent_type}-agent"
            / "specializations"
            / f"{spec_name}.md"
        )

        if spec_path.exists():
            return spec_path

        return None

    @staticmethod
    def load_specialization(
        agent_type: str,
        specialization: str
    ) -> Optional[str]:
        """
        Load specialization file content.

        Args:
            agent_type: "frontend" or "backend"
            specialization: Specialization name

        Returns:
            File content or None if not found
        """
        spec_path = SpecializationLoader.get_specialization_path(
            agent_type,
            specialization
        )

        if not spec_path:
            return None

        try:
            with open(spec_path, "r") as f:
                return f.read()
        except Exception:
            return None

    @staticmethod
    def get_base_agent_spec(agent_type: str) -> Optional[str]:
        """
        Load base agent specification.

        Args:
            agent_type: "frontend" or "backend"

        Returns:
            Base spec content or None
        """
        base_path = (
            SpecializationLoader.AGENTS_BASE
            / f"{agent_type}-agent"
            / "base.md"
        )

        if base_path.exists():
            try:
                with open(base_path, "r") as f:
                    return f.read()
            except Exception:
                return None

        return None

    @staticmethod
    def get_agent_spec(
        agent_type: str,
        specialization: Optional[str] = None
    ) -> Optional[str]:
        """
        Get agent specification (base + specialization).

        Args:
            agent_type: "frontend" or "backend"
            specialization: Specialization name (optional)

        Returns:
            Combined spec content
        """
        # Get base spec
        base = SpecializationLoader.get_base_agent_spec(agent_type)

        if not base:
            # Fallback to old single-file agent spec
            agent_path = (
                SpecializationLoader.AGENTS_BASE
                / f"0{2 if agent_type == 'frontend' else 3}-{agent_type}-agent.md"
            )
            if agent_path.exists():
                try:
                    with open(agent_path, "r") as f:
                        return f.read()
                except Exception:
                    pass
            return None

        if not specialization:
            return base

        # Add specialization
        spec_content = SpecializationLoader.load_specialization(
            agent_type,
            specialization
        )

        if spec_content:
            return f"{base}\n\n## {specialization.upper()} SPECIALIZATION\n\n{spec_content}"

        return base

    @staticmethod
    def get_available_specializations(agent_type: str) -> List[str]:
        """Get available specializations for an agent type."""
        return list(
            SpecializationLoader.SUPPORTED_SPECIALIZATIONS.get(agent_type, {}).keys()
        )

    @staticmethod
    def validate_specialization(
        agent_type: str,
        specialization: str
    ) -> bool:
        """Check if specialization is supported."""
        supported = SpecializationLoader.get_available_specializations(agent_type)
        return specialization in supported


# ============================================================================
# Fallback Strategy
# ============================================================================

class FallbackStrategy:
    """Handles unsupported technology stacks with fallback strategies."""

    # Fallback mappings: unsupported → fallback (similar tech)
    FALLBACKS = {
        "frontend": {
            "angular": "react",  # Both are component-based
            "ember": "react",
            "backbone": "vue",
        },
        "backend": {
            "flask": "fastapi",  # Both are Python
            "pyramid": "fastapi",
            "rails": "django",   # Both are full-featured
            "laravel": "nodejs",
        }
    }

    @staticmethod
    def get_fallback(
        agent_type: str,
        technology: str
    ) -> Optional[str]:
        """
        Get fallback technology for unsupported stack.

        Args:
            agent_type: "frontend" or "backend"
            technology: Unsupported technology name

        Returns:
            Fallback technology name or None
        """
        fallbacks = FallbackStrategy.FALLBACKS.get(agent_type, {})
        return fallbacks.get(technology.lower())

    @staticmethod
    def should_require_approval(
        agent_type: str,
        technology: str
    ) -> bool:
        """
        Check if unsupported tech should require human approval.

        Rationale:
        - Use fallback if very similar (same language)
        - Require approval if different paradigm
        """
        return FallbackStrategy.get_fallback(agent_type, technology) is not None


# ============================================================================
# Tech Stack Manager
# ============================================================================

class TechStackManager:
    """Manages technology stack detection and selection for projects."""

    @staticmethod
    def analyze_project(
        user_request: str,
        context: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Analyze project and return complete tech stack information.

        Args:
            user_request: User's project description
            context: Optional additional context

        Returns:
            {
                "tech_stack": {"frontend": "...", "backend": "..."},
                "complexity_score": int,
                "complexity_factors": [...],
                "detected_from": "explicit" | "implicit",
                "requires_specializations": bool
            }
        """
        # Detect tech stack
        tech_stack = TechStackDetector.detect_tech_stack(user_request, context)

        # Calculate complexity
        complexity_score, factors = ComplexityScorer.calculate_complexity(
            user_request,
            context
        )

        return {
            "tech_stack": tech_stack,
            "complexity_score": complexity_score,
            "complexity_factors": factors,
            "detected_from": tech_stack["detected_from"],
            "requires_specializations": (
                tech_stack["frontend"] is not None or tech_stack["backend"] is not None
            )
        }

    @staticmethod
    def validate_stack(
        frontend: Optional[str],
        backend: Optional[str]
    ) -> Dict[str, bool]:
        """
        Validate that technologies are supported.

        Returns:
            {
                "frontend_supported": bool,
                "backend_supported": bool,
                "needs_approval": bool
            }
        """
        frontend_valid = (
            frontend is None or
            SpecializationLoader.validate_specialization("frontend", frontend)
        )
        backend_valid = (
            backend is None or
            SpecializationLoader.validate_specialization("backend", backend)
        )

        needs_approval = not (frontend_valid and backend_valid)

        return {
            "frontend_supported": frontend_valid,
            "backend_supported": backend_valid,
            "needs_approval": needs_approval
        }
