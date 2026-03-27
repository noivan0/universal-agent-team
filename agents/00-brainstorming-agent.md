# Brainstorming Agent — Collective Pre-Brainstorming Phase

## Purpose

The Brainstorming Phase runs **before** the main workflow (Planning → Architecture → ...).
Six domain agents execute **in parallel**, each providing a full preliminary design from
their domain's perspective. A Synthesis agent then consolidates all six perspectives into
`BrainstormingArtifacts` that every subsequent main-workflow agent reads as context.

**Goal**: Surface design conflicts and risks early, before Planning locks in decisions,
reducing Self-Healing loop frequency and improving overall output quality.

---

## Execution Model

```
[BRAINSTORMING — 6 agents run in parallel]
  brainstorming_planning      ←  requirements scope, ambiguities, constraints
  brainstorming_architecture  ←  system patterns, tech stack candidates
  brainstorming_frontend      ←  UI/UX patterns, component structure, state management
  brainstorming_backend       ←  API design, data models, auth, scalability
  brainstorming_qa            ←  test strategy, testability, coverage targets
  brainstorming_documentation ←  documentation scope, format, maintenance

[SYNTHESIS — 1 agent, serial, runs after all 6 complete]
  brainstorming_synthesis     ←  consolidates all perspectives into consensus
```

---

## Scope Constraint (Critical)

**Brainstorming agents produce DESIGN SKETCHES only — not working code.**

- ✅ Propose approaches, patterns, considerations
- ✅ Identify risks and cross-agent dependencies
- ✅ Suggest preferred libraries and architectural patterns
- ❌ Do NOT generate full implementation code
- ❌ Do NOT make binding final decisions (that is Planning/Architecture's job)
- ❌ Do NOT duplicate the full specification of subsequent agents

---

## Role-Specific Prompts

### `brainstorming_planning`

Focus on:
- Scope boundaries — what is explicitly requested vs. implied
- Ambiguities that could derail implementation
- Feature prioritization (MVP vs. nice-to-have)
- Non-functional requirements (performance, security, scalability)
- Success criteria and acceptance conditions

### `brainstorming_architecture`

Focus on:
- Architecture pattern candidates (monolith, microservices, serverless, etc.)
- Technology stack recommendations with rationale
- Data flow and component boundaries
- Integration points and external dependencies
- Scalability and deployment considerations

### `brainstorming_frontend`

Focus on:
- UI framework selection (React, Vue, Svelte, etc.)
- Component decomposition and state management strategy
- API integration patterns (REST, GraphQL, WebSocket)
- Routing structure and page hierarchy
- Accessibility and responsiveness requirements

### `brainstorming_backend`

Focus on:
- API design style (REST, GraphQL, gRPC)
- Data model sketches (entities, relationships)
- Authentication and authorization strategy
- Business logic structure (services, repositories)
- Performance bottlenecks and caching needs

### `brainstorming_qa`

Focus on:
- Test pyramid strategy (unit / integration / e2e ratios)
- Critical paths requiring 100% coverage
- Testability concerns (mocking, dependency injection)
- CI pipeline structure and quality gates
- Performance and security testing needs

### `brainstorming_documentation`

Focus on:
- Documentation audience (developers, end users, operators)
- Required document types (README, API reference, ADRs, runbooks)
- Maintenance burden and doc-as-code feasibility
- Onboarding sequence for new team members
- Versioning and changelog strategy

---

## JSON Output Schema

### Domain Agents (`brainstorming_*` except synthesis)

```json
{
  "agent_role": "<role name>",
  "domain_concerns": [
    "<concern 1>",
    "<concern 2>"
  ],
  "preliminary_design": {
    "<section>": "<design sketch or key decisions>"
  },
  "recommended_approaches": [
    "<approach 1>",
    "<approach 2>"
  ],
  "risks_and_challenges": [
    "<risk 1>",
    "<risk 2>"
  ],
  "dependencies_on_others": [
    "<dependency on another agent's output>"
  ]
}
```

**Rules**:
- `domain_concerns`: minimum 2 items, maximum 8
- `preliminary_design`: at least 1 key with meaningful content
- `recommended_approaches`: minimum 1 item
- Response MUST be valid, complete JSON

### Synthesis Agent (`brainstorming_synthesis`)

```json
{
  "collective_consensus": "<500-1000 word synthesis of all perspectives, covering agreed decisions, trade-offs, and key insights each agent should know>",
  "agreed_tech_stack": {
    "frontend": "<framework>",
    "backend": "<framework>",
    "database": "<db technology>",
    "auth": "<auth mechanism>",
    "deployment": "<deployment target>"
  },
  "critical_decisions": [
    "<decision 1 requiring explicit attention>",
    "<decision 2>"
  ],
  "early_risks": [
    "<risk 1 identified across multiple perspectives>",
    "<risk 2>"
  ]
}
```

**Rules**:
- `collective_consensus`: 200 words minimum, captures cross-cutting themes
- `agreed_tech_stack`: include at minimum `frontend` and `backend` keys
- `critical_decisions`: minimum 2 items
- Response MUST be valid, complete JSON

---

## Context Available to Brainstorming Agents

Each domain agent receives:
1. **User Request** — the original natural-language project description
2. **Optional Tech Stack Hint** — if the user specified technology preferences
3. **Domain Role** — which perspective to take (injected via system prompt)

Synthesis agent additionally receives:
- All 6 domain perspectives (as structured JSON)

---

## How Main Agents Use Brainstorming Output

After the brainstorming phase completes, `state.brainstorming_artifacts` is populated.
Every subsequent agent (Planning, Architecture, Frontend, Backend, QA, Documentation)
receives this in their context via `_build_project_context()`:

```
## Collective Brainstorming Insights
<collective_consensus text>

Agreed Tech Stack: {frontend: React, backend: FastAPI, ...}
Critical Decisions: [...]
Early Risks: [...]
```

This ensures all agents start from a shared understanding rather than each
independently re-discovering the same design constraints.
