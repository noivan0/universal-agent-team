"""
Complexity Scoring System

Calculates project complexity based on multiple factors.
Ranges from 0-100 with justifications for each score.
"""

from typing import List, Tuple
from dataclasses import dataclass


@dataclass
class ComplexityFactors:
    """Breakdown of complexity factors."""
    base_score: int = 50
    real_time_bonus: int = 0
    multi_tenant_bonus: int = 0
    payment_bonus: int = 0
    high_load_bonus: int = 0
    authentication_bonus: int = 0
    api_integration_bonus: int = 0
    ml_bonus: int = 0
    visualization_bonus: int = 0
    deployment_bonus: int = 0

    def total(self) -> int:
        """Calculate total complexity score (capped at 100)."""
        total = (
            self.base_score +
            self.real_time_bonus +
            self.multi_tenant_bonus +
            self.payment_bonus +
            self.high_load_bonus +
            self.authentication_bonus +
            self.api_integration_bonus +
            self.ml_bonus +
            self.visualization_bonus +
            self.deployment_bonus
        )
        return min(100, total)  # Cap at 100

    def factor_names(self) -> List[str]:
        """Get names of all factors that contributed to score."""
        factors = []
        if self.real_time_bonus > 0:
            factors.append("real-time")
        if self.multi_tenant_bonus > 0:
            factors.append("multi-tenant")
        if self.payment_bonus > 0:
            factors.append("payment")
        if self.high_load_bonus > 0:
            factors.append("high-load")
        if self.authentication_bonus > 0:
            factors.append("authentication")
        if self.api_integration_bonus > 0:
            factors.append("api-integration")
        if self.ml_bonus > 0:
            factors.append("machine-learning")
        if self.visualization_bonus > 0:
            factors.append("visualization")
        if self.deployment_bonus > 0:
            factors.append("advanced-deployment")
        return factors


class ComplexityScorer:
    """Scores project complexity based on features and requirements."""

    # Keywords for each complexity factor
    REAL_TIME_KEYWORDS = ['real-time', 'live', 'websocket', 'streaming', 'instant', 'realtime', 'inventory update']
    MULTI_TENANT_KEYWORDS = ['multi-tenant', 'multitenant', 'multi tenant', 'saas', 'white-label']
    PAYMENT_KEYWORDS = ['payment', 'stripe', 'paypal', 'billing', 'subscription', 'checkout']
    HIGH_LOAD_KEYWORDS = ['scalable', 'concurrent', '1000+', 'high load', 'high-load', '100+', 'millions', 'thousands']
    AUTH_KEYWORDS = ['oauth', 'oauth2', 'authentication', 'auth', 'jwt', 'session', 'login']
    API_KEYWORDS = ['stripe', 'paypal', 'third-party', 'external api', 'api integration', 'webhook']
    ML_KEYWORDS = ['machine learning', 'ml', 'neural', 'recommendation', 'ai', 'prediction']
    VIZ_KEYWORDS = ['visualization', 'd3', 'chart', 'dashboard', 'graph', 'analytics']
    DEPLOY_KEYWORDS = ['kubernetes', 'k8s', 'microservice', 'docker swarm', 'orchestration']

    def calculate_complexity(self, user_request: str) -> Tuple[int, List[str]]:
        """
        Calculate complexity score for a project.

        Args:
            user_request: Natural language project description

        Returns:
            Tuple of (score: 0-100, contributing_factors: list of strings)
        """
        request_lower = user_request.lower()
        factors = ComplexityFactors()

        # Check each factor
        if self._contains_keywords(request_lower, self.REAL_TIME_KEYWORDS):
            factors.real_time_bonus = 20

        if self._contains_keywords(request_lower, self.MULTI_TENANT_KEYWORDS):
            factors.multi_tenant_bonus = 15

        if self._contains_keywords(request_lower, self.PAYMENT_KEYWORDS):
            factors.payment_bonus = 15

        if self._contains_keywords(request_lower, self.HIGH_LOAD_KEYWORDS):
            factors.high_load_bonus = 20

        if self._contains_keywords(request_lower, self.AUTH_KEYWORDS):
            factors.authentication_bonus = 10

        if self._contains_keywords(request_lower, self.API_KEYWORDS):
            factors.api_integration_bonus = 10

        if self._contains_keywords(request_lower, self.ML_KEYWORDS):
            factors.ml_bonus = 15

        if self._contains_keywords(request_lower, self.VIZ_KEYWORDS):
            factors.visualization_bonus = 10

        if self._contains_keywords(request_lower, self.DEPLOY_KEYWORDS):
            factors.deployment_bonus = 10

        total_score = factors.total()
        factor_names = factors.factor_names()

        return total_score, factor_names

    def _contains_keywords(self, text: str, keywords: List[str]) -> bool:
        """Check if text contains any of the keywords."""
        return any(keyword in text for keyword in keywords)

    def get_complexity_level(self, score: int) -> str:
        """Get human-readable complexity level."""
        if score <= 30:
            return "Very Simple"
        elif score <= 50:
            return "Simple"
        elif score <= 70:
            return "Moderate"
        elif score <= 85:
            return "Complex"
        else:
            return "Highly Complex"

    def get_team_size_recommendation(self, score: int) -> int:
        """Recommend team size based on complexity."""
        if score <= 30:
            return 1
        elif score <= 50:
            return 1
        elif score <= 70:
            return 2
        elif score <= 85:
            return 3
        else:
            return 4
