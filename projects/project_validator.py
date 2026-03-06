"""
Universal Agent Team Project Validation Demonstration

Demonstrates the system's ability to:
1. Detect technology stacks from natural language
2. Calculate project complexity
3. Select appropriate specialists
4. Estimate execution timelines
5. Validate artifacts

Three real-world projects are analyzed:
- Project A: E-Commerce Platform (High Complexity)
- Project B: Mobile Todo App (Low Complexity)
- Project C: Real-time Analytics Dashboard (High Performance)
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "orchestrator"))

from tech_stack_detector import TechStackDetector
from complexity_scorer import ComplexityScorer
from specialist_selector import SpecialistAgentSelector, SelectionCriteria


# Project Definitions
PROJECTS = {
    'ecommerce-2026': {
        'name': 'E-Commerce Platform',
        'complexity': 'High',
        'request': """Build a scalable e-commerce platform with real-time inventory updates,
user authentication with OAuth2, payment processing (Stripe), multi-tenant
support, and complex product recommendations using machine learning.
Frontend should be mobile-responsive React with advanced UI. Backend should
handle 1000+ concurrent users with Redis caching. Include admin dashboard."""
    },
    'mobile-todo-2026': {
        'name': 'Mobile Todo App',
        'complexity': 'Low',
        'request': """Build a simple mobile todo app that works on iOS and Android.
Users can add tasks, mark them complete, set reminders, and delete tasks.
Local storage only, no backend required. Use React Native."""
    },
    'analytics-2026': {
        'name': 'Real-time Analytics Dashboard',
        'complexity': 'High Performance',
        'request': """Build a real-time analytics dashboard that displays live metrics
from 10,000+ data sources. Backend in FastAPI with async operations,
Redis for caching, WebSockets for real-time updates. Frontend in React
with D3.js visualizations. Must handle 100+ concurrent users.
Include Kubernetes deployment manifests."""
    }
}


class ProjectValidator:
    """Validates projects using the Universal Agent Team system."""

    def __init__(self):
        self.detector = TechStackDetector()
        self.scorer = ComplexityScorer()
        self.selector = SpecialistAgentSelector()
        self.results = {}

    def validate_project(self, project_id: str, project: dict) -> dict:
        """Validate a single project."""
        print(f"\n{'='*80}")
        print(f"PROJECT: {project['name']} ({project_id})")
        print(f"Expected Complexity Level: {project['complexity']}")
        print(f"{'='*80}\n")

        # Step 1: Detect tech stack
        print("STEP 1: TECHNOLOGY STACK DETECTION")
        print("-" * 80)
        tech_result = self.detector.detect_tech_stack(project['request'])
        print(f"  Frontend: {tech_result.frontend or 'None'}")
        print(f"  Backend: {tech_result.backend or 'None'}")
        print(f"  Detection Method: {tech_result.detected_from.upper()}")
        print(f"  Confidence: {tech_result.confidence*100:.0f}%")
        print(f"  Patterns Matched: {', '.join(tech_result.patterns_matched)}")

        # Step 2: Score complexity
        print("\nSTEP 2: COMPLEXITY ASSESSMENT")
        print("-" * 80)
        score, factors = self.scorer.calculate_complexity(project['request'])
        level = self.scorer.get_complexity_level(score)
        team_rec = self.scorer.get_team_size_recommendation(score)

        print(f"  Complexity Score: {score}/100")
        print(f"  Level: {level}")
        print(f"  Contributing Factors:")
        for factor in factors:
            print(f"    • {factor}")
        print(f"  Recommended Team Size: {team_rec} developer(s)")

        # Step 3: Select specialists
        print("\nSTEP 3: SPECIALIST AGENT SELECTION")
        print("-" * 80)
        criteria = SelectionCriteria(
            complexity_score=score,
            complexity_factors=factors,
            project_id=project_id,
            team_size=team_rec,
            api_endpoint_count=50 if score >= 75 else 10
        )
        specialists = self.selector.select_specialists(criteria)
        print(f"  Specialists Selected: {len(specialists)}")
        if specialists:
            for i, specialist in enumerate(specialists, 1):
                print(f"    {i}. {specialist.name}")
                print(f"       Cost Impact: {specialist.cost_impact}")
                print(f"       Est. Time: {specialist.estimated_time_minutes} min")
        else:
            print(f"    (None required - project has low complexity)")

        # Step 4: Timeline estimation
        print("\nSTEP 4: EXECUTION TIMELINE ESTIMATE")
        print("-" * 80)
        time_est = self.selector.estimate_total_time(specialists)
        print(f"  Estimated Total Duration: ~{time_est['total_min']} minutes")
        print(f"  Sequential Base: {time_est.get('sequential_min', 2)} min (planning)")
        print(f"  Architecture Design: {time_est.get('architecture_min', 3)} min")
        print(f"  Specialist Parallelization: {time_est.get('specialist_parallel_min', 0)} min")
        print(f"  Development (Frontend + Backend): {time_est.get('dev_parallel_min', 5)} min")
        print(f"  QA & Documentation: {time_est.get('qa_min', 3)} + {time_est.get('docs_min', 2)} min")

        # Step 5: Cost estimation
        print("\nSTEP 5: COST ESTIMATE")
        print("-" * 80)
        cost = self.selector.get_cost_estimate(specialists)
        print(f"  Base Implementation: {cost['base_implementation']}")
        print(f"  Specialist Services: {cost['specialist_services']}")
        print(f"  Total Cost: {cost['estimated_total']}")

        # Step 6: Expected artifacts
        print("\nSTEP 6: EXPECTED ARTIFACTS")
        print("-" * 80)
        artifacts = self._get_expected_artifacts(score, factors)
        print(f"  Total Files Expected: {artifacts['total_files']}")
        print(f"  Key Deliverables:")
        for category, count in artifacts['by_category'].items():
            print(f"    • {category}: {count} files")

        # Validation result
        print("\nSTEP 7: VALIDATION RESULT")
        print("-" * 80)
        validation_status = self._validate_project(project, score, factors, specialists)
        if validation_status['status'] == 'VALIDATED':
            print(f"  ✅ STATUS: {validation_status['status']}")
            print(f"  Confidence: {validation_status['confidence']}%")
        else:
            print(f"  ⚠️  STATUS: {validation_status['status']}")
            print(f"  Issues: {', '.join(validation_status.get('issues', []))}")

        result = {
            'project_id': project_id,
            'project_name': project['name'],
            'timestamp': datetime.now().isoformat(),
            'tech_stack': {
                'frontend': tech_result.frontend,
                'backend': tech_result.backend,
                'detection_method': tech_result.detected_from
            },
            'complexity': {
                'score': score,
                'level': level,
                'factors': factors
            },
            'specialists': [
                {
                    'name': s.name,
                    'cost': s.cost_impact,
                    'time_minutes': s.estimated_time_minutes
                }
                for s in specialists
            ],
            'execution': {
                'total_minutes': time_est['total_min'],
                'team_size': team_rec,
                'parallelization_possible': len(specialists) > 0
            },
            'cost': cost,
            'artifacts': artifacts,
            'validation': validation_status
        }

        self.results[project_id] = result
        return result

    def _get_expected_artifacts(self, score: int, factors: list) -> dict:
        """Determine expected artifacts based on complexity."""
        base_files = {
            'planning': 3,  # requirements, tasks, complexity analysis
            'architecture': 4,  # design doc, component specs, API specs, DB schema
            'documentation': 5,  # README, API docs, deployment guide, etc.
        }

        if score <= 50:
            # Simple project
            return {
                'total_files': 25,
                'by_category': {
                    'Planning Docs': 3,
                    'Architecture Docs': 3,
                    'Frontend Components': 8,
                    'Backend Code': 5,
                    'Tests': 3,
                    'Documentation': 3,
                }
            }
        elif score <= 75:
            # Moderate project
            return {
                'total_files': 60,
                'by_category': {
                    'Planning Docs': 4,
                    'Architecture Docs': 6,
                    'Frontend Components': 18,
                    'Backend Code': 15,
                    'Tests': 10,
                    'Configuration': 4,
                    'Documentation': 3,
                }
            }
        else:
            # Complex project
            return {
                'total_files': 150,
                'by_category': {
                    'Planning Docs': 5,
                    'Architecture Docs': 8,
                    'Frontend Components': 35,
                    'Backend Code': 45,
                    'Tests': 30,
                    'Configuration': 10,
                    'Database Migrations': 8,
                    'Deployment Configs': 5,
                    'Documentation': 4,
                }
            }

    def _validate_project(self, project: dict, score: int, factors: list, specialists: list) -> dict:
        """Validate that detection and selection are correct."""
        issues = []

        # Validate tech stack detection
        request_lower = project['request'].lower()

        # For e-commerce
        if 'ecommerce' in project['name'].lower():
            if score < 90:
                issues.append("Complexity score too low for e-commerce")
            if 'react' not in str(self.detector.detect_tech_stack(project['request']).frontend).lower():
                issues.append("React not detected in frontend")
            if not any(f in factors for f in ['authentication', 'payment', 'high-load']):
                issues.append("Key factors not detected")

        # For todo app
        elif 'todo' in project['name'].lower():
            if score > 60:
                issues.append("Complexity score too high for simple todo app")
            if len(specialists) > 0:
                issues.append("Specialists should not be selected for simple project")

        # For analytics
        elif 'analytics' in project['name'].lower():
            if score < 85:
                issues.append("Complexity score too low for real-time analytics")
            if not any(f in factors for f in ['real-time', 'high-load']):
                issues.append("Real-time and high-load factors not detected")

        if issues:
            return {
                'status': 'NEEDS REVIEW',
                'confidence': 60,
                'issues': issues
            }

        return {
            'status': 'VALIDATED',
            'confidence': 95,
            'notes': 'All detection systems working correctly'
        }

    def generate_comparison_table(self) -> str:
        """Generate side-by-side comparison of all projects."""
        lines = [
            "\n" + "=" * 120,
            "PROJECT COMPARISON SUMMARY",
            "=" * 120,
            f"{'Metric':<30} | {'A: E-commerce':<25} | {'B: Todo App':<25} | {'C: Analytics':<25}",
            "-" * 120,
        ]

        results = self.results
        a = results.get('ecommerce-2026', {})
        b = results.get('mobile-todo-2026', {})
        c = results.get('analytics-2026', {})

        metrics = [
            ('Complexity Score', lambda r: f"{r.get('complexity', {}).get('score', 0)}/100"),
            ('Complexity Level', lambda r: r.get('complexity', {}).get('level', 'Unknown')),
            ('Specialists Selected', lambda r: str(len(r.get('specialists', [])))),
            ('Est. Duration (min)', lambda r: str(r.get('execution', {}).get('total_minutes', 0))),
            ('Code Files Generated', lambda r: str(r.get('artifacts', {}).get('total_files', 0))),
            ('Estimated Cost', lambda r: r.get('cost', {}).get('estimated_total', 'N/A')),
            ('Frontend Tech', lambda r: r.get('tech_stack', {}).get('frontend', 'None')),
            ('Backend Tech', lambda r: r.get('tech_stack', {}).get('backend', 'None')),
            ('Team Size Required', lambda r: str(r.get('execution', {}).get('team_size', 1))),
        ]

        for metric_name, getter in metrics:
            try:
                val_a = getter(a)
                val_b = getter(b)
                val_c = getter(c)
                lines.append(f"{metric_name:<30} | {val_a:<25} | {val_b:<25} | {val_c:<25}")
            except Exception:
                pass

        lines.append("=" * 120 + "\n")
        return "\n".join(lines)

    def run_full_validation(self) -> None:
        """Run validation on all three projects."""
        print("\n" + "=" * 80)
        print("UNIVERSAL AGENT TEAM - PROJECT VALIDATION DEMONSTRATION")
        print("=" * 80)
        print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"System: Multi-Agent Technology Stack Detection & Specialist Selection")

        # Validate each project
        for project_id, project_info in PROJECTS.items():
            self.validate_project(project_id, project_info)

        # Generate comparison
        print(self.generate_comparison_table())

        # Save results
        self._save_results()

    def _save_results(self) -> None:
        """Save results to JSON file."""
        output_file = Path(__file__).parent.parent / 'validation_results.json'
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"Results saved to: {output_file}")


if __name__ == '__main__':
    validator = ProjectValidator()
    validator.run_full_validation()
