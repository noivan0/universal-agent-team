# Component Designer Agent Specification

## Overview

The Component Designer Agent is an optional specialist agent that deeply reviews and enhances component architecture, focusing on reusability, composition patterns, and advanced component features. It specializes in complex UI systems with shared component libraries, design systems, and sophisticated component interactions. This agent ensures components are optimized for reuse, maintainability, and performance.

**Agent Type:** Optional Specialist (Phase 4+)
**Invocation Trigger:** Complexity score ≥ 60 + ("ui" OR "frontend" OR "component" OR "design_system" in factors)
**Typical Invocation:** After Architecture Agent, before Frontend Agent

---

## Role and Responsibilities

### Primary Responsibility

Design and enhance component architecture by reviewing component specifications for reusability, composition patterns, state management optimization, and adherence to modern component best practices.

### Secondary Responsibilities

- Optimize component hierarchy and composition patterns
- Design shared component libraries and design systems
- Review component state management strategy
- Identify reusable patterns and abstract components
- Design component APIs (props, callbacks, events)
- Plan component testing strategies
- Document component usage patterns
- Design theme/styling system
- Plan performance optimizations
- Review accessibility requirements

### What This Agent Does NOT Do

- ❌ Implement component code (Frontend Agent's role)
- ❌ Design system architecture (Architecture Agent's role)
- ❌ Create data models (that's Architecture's job)
- ❌ Write test cases (QA Agent's role)
- ❌ Design UI mockups (Designer's job, not AI's role)
- ❌ Make business logic decisions

---

## Input Requirements

### Required Inputs

From `AgentState`:

| Field | Type | Description |
|-------|------|-------------|
| `artifacts` | `dict[str, Any]` | Architecture artifacts containing `component_specs` |
| `architecture_doc` | `str` | Architecture document with component design decisions |
| `requirements` | `str` | Project requirements, especially UI/UX requirements |

**Component Specs Structure (Required):**
```python
artifacts["component_specs"] = {
    "<ComponentName>": {
        "type": "React.FC" | "Vue" | "Angular",
        "description": str,
        "props": dict,              # Props definition
        "state": list[str],         # Internal state
        "api_calls": list[str],     # External dependencies
        "children": list[str],      # Sub-components
        "events": list[str],        # Emitted events (optional)
        "styling": str,             # CSS class or styled-component ref
        "accessibility": dict       # a11y requirements (optional)
    }
}
```

### Optional Inputs

| Field | Type | Description |
|-------|------|-------------|
| `design_system_spec` | `dict` | Existing design system definitions |
| `ui_guidelines` | `str` | Organization UI/UX guidelines |
| `performance_requirements` | `dict` | Performance targets |
| `accessibility_requirements` | `dict` | WCAG levels, a11y needs |

**Optional Context:**
```python
{
    "component_count": 25,
    "shared_components_required": true,
    "design_system_exists": false,
    "performance_target": "LCP < 2.5s",
    "wcag_level": "AA",
    "responsive_breakpoints": ["mobile", "tablet", "desktop"],
    "theme_support": ["light", "dark"],
    "animation_framework": "framer-motion"
}
```

### Validation Rules

```python
def validate_input(self, state: AgentState) -> bool:
    """
    Validate that state contains component specifications to enhance.

    Returns:
        True if component specs are present and valid, False otherwise
    """
    # Check artifacts contain component_specs
    if not state.artifacts or "component_specs" not in state.artifacts:
        self.logger.error("No component specifications found in artifacts")
        return False

    component_specs = state.artifacts["component_specs"]
    if not component_specs or not isinstance(component_specs, dict):
        self.logger.error("component_specs is empty or not a dict")
        return False

    # Validate each component has required fields
    for component_name, component_spec in component_specs.items():
        required_fields = {"type", "description", "props"}
        if not all(field in component_spec for field in required_fields):
            self.logger.error(f"Component {component_name} missing required fields")
            return False

        if component_spec.get("type") not in ["React.FC", "Vue", "Angular", "Custom"]:
            self.logger.warning(f"Component {component_name} has non-standard type")

    return True
```

---

## Output Specifications

### Primary Outputs

The Component Designer Agent returns a dictionary with these fields:

| Field | Type | Description |
|-------|------|-------------|
| `component_design_report` | `str` | Markdown report with design findings |
| `enhanced_component_specs` | `dict` | Updated component specs with improvements |
| `design_system_spec` | `dict` | Design system/shared components definition |
| `component_patterns` | `list[dict]` | Reusable component patterns identified |
| `optimization_recommendations` | `list[str]` | Performance and architecture improvements |
| `message` | `str` | Summary of design work |

### Artifacts

The Component Designer Agent produces detailed design artifacts:

```python
artifacts = {
    "component_design": {
        "total_components": int,
        "components_designed": list[str],
        "shared_components": int,
        "design_system_scope": str,
        "composition_score": float,  # 0-100, higher = more reusable
        "design_timestamp": str
    },

    "design_findings": {
        "composition_issues": [
            {
                "component": str,
                "severity": "critical|warning|info",
                "issue": str,
                "details": str,
                "recommendation": str,
                "refactored_composition": dict
            }
        ],
        "state_management_issues": [
            {
                "component": str,
                "issue": str,
                "current_approach": str,
                "recommended_approach": str
            }
        ],
        "reusability_opportunities": [
            {
                "pattern": str,
                "components_affected": list[str],
                "estimated_code_reduction": str,
                "abstraction_level": "low|medium|high"
            }
        ],
        "accessibility_gaps": [
            {
                "component": str,
                "gap": str,
                "wcag_criterion": str,
                "fix": str
            }
        ],
        "performance_issues": [
            {
                "component": str,
                "issue": str,
                "impact": str,
                "optimization": str
            }
        ]
    },

    "enhanced_specs": {
        "<ComponentName>": {
            # Enhanced specifications with additional fields
            "composition": str,           # How to compose child components
            "state_management": str,      # Recommended state management
            "memoization": bool,          # Should use React.memo
            "lazy_loadable": bool,        # Can be lazy loaded
            "theme_aware": bool,          # Supports theming
            "accessibility": {
                "role": str,              # ARIA role
                "ariaLabel": str,
                "ariaLabelledBy": str,
                "wcag_compliance": str
            },
            "performance": {
                "render_cost": "low|medium|high",
                "estimated_bundle_impact_kb": float,
                "optimization_tips": list[str]
            },
            "testing_strategy": {
                "unit_tests": list[str],
                "integration_tests": list[str],
                "visual_tests": list[str],
                "accessibility_tests": list[str]
            }
        }
    },

    "design_system": {
        "name": str,
        "version": str,
        "colors": {
            "primary": {...},
            "secondary": {...},
            "semantic": {"success": str, "warning": str, "error": str}
        },
        "typography": {
            "font_families": list[str],
            "scales": {"h1": dict, "body": dict, "small": dict}
        },
        "spacing": {
            "unit": str,               # "4px" or "0.25rem"
            "scales": [0, 4, 8, 12, 16, 24, 32, 48, 64]
        },
        "components": {
            "Button": {...},
            "Card": {...},
            "Input": {...}
        },
        "patterns": {
            "form_validation": str,
            "error_handling": str,
            "loading_states": str
        }
    },

    "composition_patterns": [
        {
            "pattern_name": "Container/Presentation",
            "description": "Separate smart (container) from dumb (presentation) components",
            "components": [list of component names],
            "benefits": ["easier testing", "better reusability"],
            "implementation_details": str
        }
    ]
}
```

### State Updates

Fields modified in `AgentState`:

```python
{
    "component_design_report": "<design report markdown>",
    "artifacts": {
        ...existing artifacts...,
        "component_design": {...},
        "enhanced_component_specs": {...},
        "design_system": {...}
    },
    "messages": [..., AgentMessage(agent_id="designer_001", artifacts={...})],
    "current_phase": "component_design",
    "next_agent": "frontend"  # or previous next_agent if no blocking issues
}
```

---

## Design Review Checks

### Component Reusability Analysis

**Checks Performed:**
1. Similar components that could be unified
2. Parameterizable components for different use cases
3. Composition opportunities vs inheritance
4. Props spreading and prop drilling issues
5. Component API clarity and consistency

**Reusability Scoring:**
```
Reusability Score = (Abstraction × Simplicity × Modularity) / 3

Where:
- Abstraction: Can this component work in multiple contexts?
- Simplicity: Is the component simple and focused?
- Modularity: Is it self-contained and independent?

Score > 80: Highly reusable (good for design system)
Score 60-80: Moderately reusable (specific use cases)
Score < 60: Low reusability (project-specific)
```

**Example Issue:**
```
Reusability Issue (HIGH OPPORTUNITY):
  Components: UserCard, ProductCard, BlogPostCard
  Problem: Three nearly identical components with minor differences
  Details: All three have same layout, just different data displayed
  Recommendation: Abstract into single Card component with configurable slots
  Impact: Reduces code by ~300 lines, easier maintenance
```

### State Management Optimization

**Checks Performed:**
1. Props vs component state (over-localized state)
2. Unnecessary state replication
3. State shape optimization
4. Context usage appropriateness
5. Store integration patterns

**State Management Patterns:**

| Pattern | Use Case | Recommendation |
|---------|----------|---|
| React.useState | Local form state, toggles | Simple and focused |
| useReducer | Complex state with actions | When multiple state vars related |
| Context API | Global theme, user auth | Small-medium shared state |
| Zustand | Client state management | Medium-large shared state |
| React Query | Server state | Data fetching and caching |
| Redux | Complex flows | Large enterprise apps |

**Example Finding:**
```
State Management Issue (WARNING):
  Component: UserDashboard
  Problem: Replicates server data in local useState
  Current: useState for todos, then fetch from /api/todos
  Issue: Manual sync required, risk of stale data
  Recommendation: Use React Query for server state
  Benefit: Automatic caching, deduplication, sync handling
```

### Component Composition Patterns

**Patterns to Identify:**

1. **Container/Presentation** - Smart vs dumb components
2. **Compound Components** - Multiple related components working together
3. **Render Props** - Flexible composition pattern
4. **Higher-Order Components** - Cross-cutting concerns
5. **Custom Hooks** - Stateful logic reuse
6. **Slot/Render Pattern** - Named slots for flexibility

**Example Detection:**
```
Composition Pattern Found:
  Pattern: Compound Components
  Components: Tabs, TabList, Tab, TabPanel
  Benefit: Flexible nesting, clear parent-child relationships
  Structure:
    <Tabs>
      <TabList>
        <Tab name="overview" />
        <Tab name="settings" />
      </TabList>
      <TabPanel name="overview">...</TabPanel>
      <TabPanel name="settings">...</TabPanel>
    </Tabs>
```

### Accessibility Review

**WCAG Compliance Checks:**
1. Semantic HTML usage
2. ARIA attributes (role, label, labelledBy)
3. Keyboard navigation support
4. Color contrast (4.5:1 for text)
5. Focus visible indicators
6. Screen reader compatibility
7. Motion and animation considerations

**Example Finding:**
```
Accessibility Issue (WCAG AA):
  Component: Modal
  Criterion: WCAG 2.1 Level A - 2.4.3 Focus Order
  Issue: Focus trap not implemented in modal
  Current: User can tab out of modal to background
  Fix: Implement focus trap, return focus on close
  Code Hint: Use libraries like focus-trap-react
```

### Performance Optimization

**Checks Performed:**
1. Unnecessary re-renders
2. Props comparison strategy (object literals)
3. Memoization opportunities
4. Bundle size impact
5. Lazy loading candidates
6. Event handler optimization
7. CSS-in-JS performance

**Example Issue:**
```
Performance Issue (MEDIUM):
  Component: UserList
  Issue: Re-renders when parent re-renders (but props unchanged)
  Root Cause: Passed arrow function as callback
  Current: onClick={()=>handleClick(id)}
  Fix: Use useCallback or wrap in secondary component
  Impact: ~15% render time reduction in lists > 100 items
```

### Design System Identification

**What Constitutes a Design System:**
1. Color palette with semantic names
2. Typography scale and font selections
3. Spacing/sizing system
4. Component library (Button, Input, Card, etc.)
5. Patterns for common UX flows
6. Icon system
7. Animation principles
8. Responsive design breakpoints

**Detection Logic:**
```python
def should_extract_design_system(component_specs: dict) -> bool:
    """Determine if components warrant design system extraction."""

    total_components = len(component_specs)

    # Heuristics
    has_shared_components = any(
        len(spec.get("children", [])) > 2
        for spec in component_specs.values()
    )

    has_styling_system = any(
        "styling" in spec and spec["styling"]
        for spec in component_specs.values()
    )

    # Extract if > 10 components and some sharing/styling
    return total_components > 10 and (has_shared_components or has_styling_system)
```

---

## LLM Configuration

### Model

```python
{
    "provider": "anthropic",
    "model": "claude-3-5-sonnet-20241022",
    "temperature": 0.2,
    "max_tokens": 7000,
    "timeout": 150
}
```

### Rationale

- **Low temperature (0.2)**: Component design requires consistency and precision
- **Claude 3.5 Sonnet**: Excellent at architectural thinking and pattern recognition
- **7000 tokens**: Sufficient for detailed component analysis and design recommendations
- **150s timeout**: Component analysis can be detailed; more time needed than validation

---

## System Prompt

```
You are an expert component architect and React/frontend systems designer with deep
knowledge of modern component patterns, design systems, and reusable architecture.

Your responsibilities:
1. Review component specifications for reusability and composition
2. Identify shared components and abstract patterns
3. Optimize component hierarchy and composition
4. Assess and improve state management strategy
5. Review accessibility and performance implications
6. Design or enhance design system
7. Identify component testing strategies
8. Optimize component APIs (props interfaces)

Component Design Best Practices:
- Single Responsibility Principle: One component, one job
- Composition over inheritance: Flexible component combinations
- Clear component APIs: Well-defined, documented props
- Reusable abstractions: Design for multiple use cases
- Performance conscious: Memoization, lazy loading, code splitting
- Accessibility first: WCAG compliance, semantic HTML, keyboard support
- Type-safe: TypeScript for prop safety
- Well-tested: Unit, integration, visual, and accessibility tests
- Performant rendering: Avoid unnecessary re-renders

Composition Patterns:
1. Container/Presentation: Smart vs dumb separation
2. Compound Components: Related components working together
3. Higher-Order Components: Cross-cutting concerns
4. Custom Hooks: Reusable stateful logic
5. Render Props: Flexible composition via function children
6. Slots/Render Pattern: Named insertion points

State Management Strategy:
- Local state: React.useState for component-only state
- Shared client state: Context API or Zustand
- Server state: React Query or SWR
- Complex flows: Redux or Jotai
- Forms: React Hook Form integration
- Async data: React Query with suspense

Design System Components:
- Foundational: Buttons, Inputs, Cards, Icons, Typography
- Layout: Grid, Flexbox, Spacing utilities, Containers
- Forms: Input, Select, Checkbox, Radio, TextArea, Form
- Navigation: Navigation, Tabs, Breadcrumbs, Pagination
- Feedback: Alert, Badge, Progress, Toast, Skeleton
- Modals: Modal, Dialog, Drawer, Tooltip, Popover
- Rich Components: Carousel, Table, DataGrid, DatePicker

Accessibility Principles (WCAG 2.1 AA):
- Semantic HTML: Use correct elements (button, nav, article, etc.)
- Aria Roles: Proper role, label, labelledBy, describedBy
- Keyboard Support: Full keyboard navigation, visible focus
- Focus Management: Logical tab order, trap in modals
- Color Contrast: 4.5:1 for normal text, 3:1 for large text
- Motion: Respect prefers-reduced-motion
- Screen Readers: Proper heading structure, alt text

Performance Optimization:
- Memoization: React.memo, useMemo, useCallback
- Code splitting: Lazy load heavy components
- Bundle analysis: Know component size impact
- Render optimization: Avoid unnecessary re-renders
- Efficient props: Avoid inline objects/functions
- CSS-in-JS: Consider performance cost

Output Requirements:
1. Component design report (markdown) with:
   - Summary of design review
   - Component reusability analysis
   - Composition patterns identified
   - Issues and recommendations
   - Design system recommendations
2. Enhanced component specifications with:
   - Composition guidelines
   - State management strategy
   - Memoization recommendations
   - Accessibility implementation
   - Testing strategy
3. Design system specification (if applicable):
   - Component library definition
   - Colors, typography, spacing
   - Component patterns
   - Usage guidelines
4. Composition patterns documentation

Remember: Great component design leads to maintainable, scalable, and performant
applications. Focus on reusability, clarity, and user experience.
```

---

## When to Invoke This Agent

### Complexity Thresholds

| Complexity | Threshold | Invocation Logic |
|-----------|-----------|------------------|
| Low (1-40) | N/A | ❌ Not invoked |
| Medium (41-60) | 60 | ❌ Not invoked |
| Medium-High (61-75) | ≥60 | ✅ Invoked if UI-heavy |
| High (76-90) | ≥60 | ✅ Invoked if UI-heavy |
| Very High (91-100) | ≥60 | ✅ Always invoked |

### Invocation Conditions

The Component Designer Agent is triggered when:

1. **Complexity score ≥ 60** AND
2. **At least one factor present:**
   - "ui" or "user interface" in requirements
   - "frontend" in architecture decision
   - "component" or "components" in requirements
   - "design_system" or "design system" mentioned
   - 10+ components in component_specs
   - Complex component hierarchy detected

3. **Optional: Boost triggers:**
   - Shared component library needed
   - Design system doesn't exist
   - High accessibility requirements
   - Performance critical application

### Decision Logic (Pseudo-code)

```python
def should_invoke_component_designer(state: AgentState) -> bool:
    """Determine if Component Designer should run."""

    # Check complexity threshold
    if not state.complexity_score or state.complexity_score < 60:
        return False

    # Check for UI-related factors
    ui_factors = ["ui", "frontend", "component", "design_system", "interface"]
    combined_text = (
        state.requirements +
        state.architecture_doc +
        str(state.artifacts)
    ).lower()

    has_ui_factor = any(factor in combined_text for factor in ui_factors)
    if not has_ui_factor:
        return False

    # Check if component_specs exist and are substantial
    if not state.artifacts or "component_specs" not in state.artifacts:
        return False

    component_specs = state.artifacts["component_specs"]
    if not component_specs or len(component_specs) < 5:
        return False

    # All checks passed
    return True
```

---

## Workflow Integration

### Prerequisites

**Must be completed before Component Designer runs:**
- Architecture Agent has completed successfully
- `artifacts["component_specs"]` is populated with component definitions
- At least 5 components specified
- Complexity score ≥ 60

**State Requirements:**
```python
AgentState(
    complexity_score=65,
    artifacts={
        "component_specs": {
            "Button": {...},
            "Card": {...},
            "UserDashboard": {...},
            "TodoList": {...},
            "TodoItem": {...},
            ...
        }
    },
    architecture_doc="<architecture including UI design>"
)
```

### Triggers

The Component Designer Agent is triggered when:
1. Architecture Agent completes with complexity ≥ 60 and UI factors detected
2. Orchestrator selector identifies Component Designer as applicable specialist
3. `current_phase == "design"` OR `current_phase == "architecture"`

### Execution Context

The Component Designer is executed:
- **When:** After Architecture Agent, before Frontend Agent
- **Why:** To optimize component structure before implementation
- **Cost:** 1 API call (LLM) per project
- **Duration:** ~1-2 minutes

### Output Routing

After Component Designer completes:

**Success Path:**
```
Component Designer
      ↓
   Frontend Agent (next_agent = "frontend")
```

**With Design System to Create:**
```
Component Designer
      ↓
   Frontend Agent (uses design_system artifact)
```

---

## Integration Examples

### Example 1: Simple CRUD UI (Not Triggered)

**Input Scenario:**
- Project: Simple todo app
- Complexity: 45
- Components: 5 (Button, Input, List, Item, Form)
- Result: Component Designer NOT invoked (complexity < 60)

### Example 2: Complex Admin Dashboard (Triggered)

**Input Scenario:**
- Project: Enterprise admin dashboard
- Complexity: 72
- Components: 25+
- Factors: ["ui", "frontend", "component", "design_system"]

**Sample Component Specs:**
```python
artifacts["component_specs"] = {
    "DataGrid": {
        "type": "React.FC",
        "description": "Reusable data grid with sorting, filtering, pagination",
        "props": {
            "data": "T[]",
            "columns": "ColumnDef[]",
            "onSelectionChange": "(selected: T[]) => void"
        },
        "state": ["selectedRows", "sortBy", "filterBy", "pageIndex"],
        "children": ["DataGridHeader", "DataGridBody", "DataGridPagination"]
    },
    "Modal": {
        "type": "React.FC",
        "description": "Reusable modal dialog",
        "props": {
            "isOpen": "boolean",
            "onClose": "() => void",
            "title": "string"
        },
        "children": ["Header", "Body", "Footer"]
    },
    ...25 more components
}
```

**Design Findings:**
```
COMPOSITION OPPORTUNITIES (4):
1. Button variations (Primary, Secondary, Danger)
   → Abstract into single Button with variant prop
   → Reduces code by ~100 lines

2. Input variations (Text, Email, Password, Number)
   → Abstract into single Input with type prop
   → Reduces code by ~150 lines

3. Card, Panel, Box similar patterns
   → Extract into Box with configurable appearance
   → Reduces code by ~80 lines

4. Modal, Dialog, Drawer share similar structure
   → Extract into Overlay base component
   → Reduces code by ~120 lines

TOTAL CODE REDUCTION: ~450 lines through abstraction

STATE MANAGEMENT ISSUES (3):
1. DataGrid manages too much state
   → Move pagination/sorting to server (use React Query)
   → Improves performance for large datasets

2. Form state scattered across components
   → Integrate React Hook Form for unified management
   → Better validation, easier testing

3. Theme state passed through too many levels
   → Move to Context API or Zustand
   → Eliminates prop drilling

DESIGN SYSTEM RECOMMENDATION:
✅ SHOULD EXTRACT DESIGN SYSTEM
Reasons:
- 25+ components present
- Multiple component families (buttons, inputs, cards)
- Styling system opportunity
- Reusability across multiple pages/features

Recommended Components:
- Buttons: Button, IconButton, ButtonGroup
- Inputs: Input, Select, Checkbox, Radio, TextArea
- Surfaces: Card, Panel, Box, Container
- Feedback: Alert, Badge, Progress, Toast
- Navigation: Tabs, Breadcrumbs, Pagination
- Overlays: Modal, Drawer, Popover, Tooltip
- Layout: Grid, Flex, Stack, Spacer

ACCESSIBILITY GAPS (5):
1. DataGrid missing keyboard navigation
   → Add arrow key support, Enter to select
   → Implement focus management

2. Modal missing focus trap
   → Use focus-trap library
   → Return focus on close

3. Buttons missing visual focus indicator
   → Add :focus-visible styles
   → Ensure 2px visible outline

4. Form inputs missing labels in some cases
   → Add htmlFor attributes
   → Implement proper aria-labelledBy

5. Modals not announcing to screen readers
   → Add role="alertdialog" or "dialog"
   → Implement aria-modal="true"

PERFORMANCE OPPORTUNITIES (4):
1. UserList component re-renders entire list on any change
   → Implement virtualization for large lists
   → Expected: 50x faster rendering (1000 items)

2. Modal doesn't lazy load heavy content
   → Implement lazy loading of modal contents
   → Reduces initial bundle by ~50KB

3. DataGrid filters cause full table re-renders
   → Implement memoization on row components
   → Move filtering to server side

4. Form inputs not debounced
   → Add debounce on validation
   → Reduces unnecessary re-renders
```

**Enhanced Component Specs Output:**
```python
artifacts["enhanced_component_specs"] = {
    "Button": {
        "type": "React.FC",
        "variants": ["primary", "secondary", "danger"],
        "sizes": ["sm", "md", "lg"],
        "memoization": True,
        "composition": "Simple, single responsibility",
        "state_management": "None (presentation component)",
        "accessibility": {
            "role": "button",
            "ariaLabel": "required if no text content",
            "wcag_compliance": "AA"
        },
        "performance": {
            "render_cost": "low",
            "bundle_impact_kb": 2.5,
            "optimization_tips": ["Use React.memo", "Avoid inline styles"]
        },
        "testing_strategy": {
            "unit_tests": ["renders with text", "calls onClick", "respects disabled"],
            "visual_tests": ["all variants", "all sizes"],
            "accessibility_tests": ["keyboard accessible", "screen reader"]
        }
    },
    "DataGrid": {
        "type": "React.FC",
        "composition": "Container component managing grid state",
        "state_management": "React Query for server state, URL params for UI state",
        "memoization": True,
        "lazy_loadable": False,
        "performance": {
            "render_cost": "high",
            "optimization_tips": [
                "Implement row virtualization",
                "Memoize row components",
                "Move filtering to server"
            ]
        },
        "accessibility": {
            "role": "grid",
            "ariaLabel": "required",
            "keyboard_support": ["arrow keys", "enter to select"],
            "wcag_compliance": "AA"
        }
    },
    ...
}
```

**Design System Output:**
```python
artifacts["design_system"] = {
    "name": "AdminUI Design System",
    "version": "1.0",
    "colors": {
        "primary": {
            "50": "#f0f4ff",
            "500": "#3b82f6",
            "900": "#1e3a8a"
        },
        "semantic": {
            "success": "#10b981",
            "warning": "#f59e0b",
            "error": "#ef4444"
        }
    },
    "typography": {
        "font_families": ["Inter", "Monospace"],
        "scales": {
            "h1": {"size": "32px", "weight": 700},
            "body": {"size": "14px", "weight": 400},
            "small": {"size": "12px", "weight": 400}
        }
    },
    "spacing": {
        "unit": "4px",
        "scales": [0, 4, 8, 12, 16, 24, 32, 48, 64]
    },
    "components": {
        "Button": {...},
        "Input": {...},
        "Card": {...},
        ...
    }
}
```

---

## Error Handling

### Validation Errors

**Input Validation Fails:**
```python
if not self.validate_input(state):
    return {
        "errors": ["No component specifications found in artifacts"],
        "message": "Cannot design components without component_specs",
        "next_agent": "architecture"
    }
```

### Recovery Strategies

1. **Insufficient Components**: Defer to Frontend Agent if < 5 components
2. **Invalid Component Structure**: Request clarification from Architecture Agent
3. **Missing Styling**: Continue with component structure recommendations
4. **LLM Timeout**: Analyze subset of critical components

---

## Tools and Capabilities

### Available Tools

| Tool | Purpose | Usage |
|------|---------|-------|
| `component_analyzer` | Analyze component structure | Identify patterns |
| `design_system_extractor` | Extract design tokens | Generate design system |
| `accessibility_checker` | Check WCAG compliance | Validate a11y |
| `performance_profiler` | Estimate component cost | Identify bottlenecks |

### Permissions

- ✅ Read: `artifacts`, `architecture_doc`, `requirements`, `messages`
- ✅ Write: `component_design_report`, `enhanced_component_specs`, `design_system_spec`
- ✅ Modify: `component_specs` (enhance with recommendations)
- ❌ Code execution: Not required
- ❌ External API calls: Not required

---

## Success Criteria

The Component Designer Agent has succeeded when:

1. ✅ All components reviewed for reusability
2. ✅ Composition patterns identified
3. ✅ State management strategy recommended
4. ✅ Accessibility gaps identified and recommendations provided
5. ✅ Performance optimization opportunities identified
6. ✅ Design system extracted (if applicable)
7. ✅ Detailed design report generated
8. ✅ Enhanced component specs provided to Frontend Agent

**Metrics:**
- Components analyzed: 100% of input components
- Reusability opportunities identified: All major patterns
- Accessibility issues found: All critical gaps
- Design system completeness: All sections present (if created)

---

## Phase Integration

**Belongs to:** Phase 4 - Optional Specialist Agents
**Invoked by:** Complexity-based Specialist Agent Selector
**Supports:** Frontend Development Agent (consumes enhanced specs)

**Timeline:**
- After: Architecture Design Agent
- Before: Frontend Development Agent
- Parallel: Contract Validator (optional, both after Architecture)

---

## References and External Links

- [React Component Best Practices](https://react.dev/learn)
- [Atomic Design Methodology](http://atomicdesign.bradfrost.com/)
- [Storybook Component Stories](https://storybook.js.org/)
- [Design System Best Practices](https://www.designsystems.com/)
- [WCAG 2.1 Accessibility Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [React Query Documentation](https://tanstack.com/query/latest)
- [Component Composition Patterns](https://www.patterns.dev/posts/component-composition/)

---

**Last Updated:** 2026-03-06
**Status:** Phase 4 - Optional Specialist
**Version:** 1.0
