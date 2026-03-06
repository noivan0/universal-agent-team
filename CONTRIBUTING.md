# Contributing to Universal Agent Team

Thank you for your interest in contributing to Universal Agent Team! This document provides guidelines and instructions for contributing.

## Code of Conduct

We are committed to providing a welcoming and inclusive environment. Please:
- Be respectful and constructive in all interactions
- Welcome people from all backgrounds
- Report inappropriate behavior to maintainers
- Focus on what's best for the community

## How to Contribute

### Report Bugs

1. **Check existing issues** - Search [GitHub Issues](https://github.com/yourusername/universal-agent-team/issues)
2. **Provide details** - Include:
   - Python/Node version
   - Steps to reproduce
   - Expected vs actual behavior
   - Error messages and logs
   - Your environment (OS, Docker, etc.)

**Example issue:**
```
Title: Agent state corruption on parallel execution

Steps to reproduce:
1. Run 3+ agents in parallel
2. Each agent makes state updates
3. State file becomes invalid JSON

Expected: All state updates merged correctly
Actual: JSON parse error, cannot recover

Environment: Ubuntu 22.04, Python 3.12, Claude Code v1.5.0

Error:
json.JSONDecodeError: Expecting value: line 1 column 1 (char 0)
```

### Suggest Features

1. **Create an issue** with `[FEATURE]` prefix
2. **Describe the use case** - Why do you need this?
3. **Provide examples** - Show how you'd use it
4. **Discuss tradeoffs** - What are pros/cons?

**Example feature request:**
```
Title: [FEATURE] Support for multi-agent voting on decisions

Use Case:
When multiple architectural approaches are viable, have agents
vote and explain reasoning for their choice.

Example:
Agent A votes for microservices (scalability)
Agent B votes for monolith (simplicity)
Agent C votes for monolith (faster deployment)
Result: Monolith chosen, rationale documented

Would improve: Decision transparency, team collaboration simulation
```

### Development Setup

#### Prerequisites
- Python 3.12+
- Git
- Virtual environment support
- ~2GB free disk space

#### Local Development Environment

```bash
# 1. Clone repository
git clone https://github.com/yourusername/universal-agent-team.git
cd universal-agent-team

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 4. Verify setup
python -c "import pydantic; print(f'Pydantic {pydantic.__version__} installed')"

# 5. Run tests
pytest tests/ -v

# 6. Check code quality
ruff check .
mypy src/

# 7. Generate documentation
python -m mkdocs serve
```

### Code Style Guidelines

#### Python (PEP 8 + Ruff)

**File structure:**
```python
"""Module docstring.

Describe what this module does in 1-2 sentences.
Include any important design decisions.
"""

from __future__ import annotations

# Standard library imports
import json
import logging
from pathlib import Path
from typing import Optional

# Third-party imports
from pydantic import BaseModel, Field

# Local imports
from agents.base import BaseAgent
from state.models import AgentState

logger = logging.getLogger(__name__)
```

**Naming conventions:**
- Classes: `PascalCase` (e.g., `PlanningAgent`)
- Functions: `snake_case` (e.g., `validate_input`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `MAX_RETRIES = 3`)
- Private: `_leading_underscore` (e.g., `_internal_method`)

**Type hints (required):**
```python
def process_agent_state(
    state: AgentState,
    max_retries: int = 3,
    timeout: Optional[float] = None
) -> dict[str, Any]:
    """Process agent state through validation and execution.

    Args:
        state: Current agent state to process
        max_retries: Maximum retry attempts on failure
        timeout: Optional timeout in seconds

    Returns:
        Dictionary of state updates to apply

    Raises:
        ValueError: If state is invalid
        TimeoutError: If execution exceeds timeout
    """
    if not isinstance(max_retries, int) or max_retries < 1:
        raise ValueError("max_retries must be positive integer")

    # Implementation...
    return {}
```

**Docstrings (Google style):**
```python
class AgentOrchestrator:
    """Orchestrates multi-agent collaboration workflow.

    Manages state transitions between agents, handles error recovery,
    and provides checkpointing for resumable execution.

    Attributes:
        agents: Dictionary mapping agent names to agent instances
        state: Current execution state
        checkpoint_dir: Directory for saving state checkpoints

    Example:
        >>> orchestrator = AgentOrchestrator(agents={...})
        >>> result = orchestrator.execute("Build a todo app")
    """
```

**Imports organization:**
```python
# 1. Standard library (alphabetical)
import json
import logging
from pathlib import Path
from typing import Any, Optional

# 2. Third-party packages (alphabetical)
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, validator

# 3. Local imports (alphabetical)
from .models import AgentState
from .services import StateManager
```

#### TypeScript/React

**File structure:**
```typescript
/**
 * AgentStatus component - Displays agent execution status.
 *
 * Shows real-time status updates during agent execution
 * with progress indicators and error messages.
 */

import React, { FC, useState } from 'react';
import { AgentStatusType } from '@/types';
import { useAgentStatus } from '@/hooks/useAgentStatus';

interface AgentStatusProps {
  agentId: string;
  status: AgentStatusType;
  onStatusChange?: (status: AgentStatusType) => void;
}

export const AgentStatus: FC<AgentStatusProps> = ({
  agentId,
  status,
  onStatusChange
}) => {
  const [isLoading, setIsLoading] = useState(false);

  const handleUpdate = (newStatus: AgentStatusType): void => {
    setIsLoading(true);
    onStatusChange?.(newStatus);
    setIsLoading(false);
  };

  return (
    <div className="agent-status">
      <span>{agentId}: {status}</span>
    </div>
  );
};
```

**Naming conventions:**
- Components: `PascalCase` (e.g., `AgentDashboard`)
- Hooks: `usePascalCase` (e.g., `useAgentState`)
- Types: `PascalCase` (e.g., `AgentStatus`)
- Files: `kebab-case.tsx` or `PascalCase.tsx`

**Type safety:**
```typescript
// Good: Explicit types
interface User {
  id: string;
  name: string;
  email: string;
}

const formatUser = (user: User): string => {
  return `${user.name} <${user.email}>`;
};

// Bad: Using any
const formatUser = (user: any): string => {
  return `${user.name} <${user.email}>`;
};
```

### Commit Message Guidelines

Use **conventional commits** format:

```
type(scope): subject

body

footer
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `refactor`: Code refactoring (no behavior change)
- `test`: Tests or test configuration
- `perf`: Performance improvement
- `chore`: Maintenance, dependencies, build

**Examples:**
```
feat(planning-agent): add requirement prioritization

Implement MoSCoW method (Must/Should/Could/Won't) to prioritize
requirements based on impact and effort estimates.

Closes #123

---

fix(state-manager): handle corrupted checkpoint files

Added validation and rollback logic when checkpoint JSON is invalid.
Now gracefully recovers to last valid checkpoint instead of crashing.

Fixes #456

---

docs(readme): clarify installation steps

Updated installation instructions with virtual environment setup
and common troubleshooting issues.

---

refactor(architecture-agent): simplify component spec generation

Extracted common spec patterns into reusable helper functions.
No behavior change, improves maintainability.
```

**Commit message checklist:**
- [ ] Type is appropriate (feat, fix, docs, etc.)
- [ ] Scope is clear and specific
- [ ] Subject is imperative ("add" not "added")
- [ ] Subject is concise (< 50 chars)
- [ ] Body explains why, not what
- [ ] References related issues (#123)
- [ ] Follows project conventions

### Testing Requirements

#### Test Organization

```python
# tests/test_agent.py - One test file per module

import pytest
from agents.planning_agent import PlanningAgent
from state.models import AgentState

class TestPlanningAgent:
    """Tests for PlanningAgent."""

    @pytest.fixture
    def agent(self):
        """Create agent instance for testing."""
        return PlanningAgent()

    @pytest.fixture
    def sample_state(self):
        """Create sample state."""
        return AgentState(
            user_request="Build a todo app",
            current_phase="planning"
        )

    def test_validate_input_accepts_valid_request(self, agent, sample_state):
        """Agent accepts valid user request."""
        assert agent.validate_input(sample_state) is True

    def test_validate_input_rejects_empty_request(self, agent):
        """Agent rejects empty requests."""
        state = AgentState(
            user_request="",
            current_phase="planning"
        )
        assert agent.validate_input(state) is False

    def test_process_creates_tasks(self, agent, sample_state):
        """Agent creates task list from requirements."""
        result = agent.process(sample_state)

        assert "tasks" in result
        assert len(result["tasks"]) > 0
        assert result["next_agent"] == "architecture"
```

#### Coverage Requirements

- **Minimum**: 80% code coverage
- **Critical paths**: 100% coverage
- **Critical paths include**:
  - State transitions
  - Error handling
  - Agent handoffs
  - Data validation

```bash
# Run tests with coverage
pytest tests/ --cov=src --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Pull Request Process

#### Before Creating PR

1. **Run all tests**
   ```bash
   pytest tests/ -v
   ```

2. **Check code quality**
   ```bash
   ruff check .           # Linting
   ruff format .          # Auto-formatting
   mypy src/             # Type checking
   ```

3. **Update documentation**
   - Add/update docstrings
   - Update README if needed
   - Add examples if applicable

4. **Commit with conventional commits**
   ```bash
   git add .
   git commit -m "feat(agent): description"
   ```

#### Creating the PR

1. **Push to your fork**
   ```bash
   git push origin feature/your-feature
   ```

2. **Create PR on GitHub** with:
   - Descriptive title (< 50 chars)
   - Reference to issue (#123)
   - Summary of changes
   - Any breaking changes
   - Testing notes

**PR Template:**
```markdown
## Description
Brief description of changes.

## Related Issues
Fixes #123

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation

## Testing
- [ ] Unit tests added
- [ ] Integration tests added
- [ ] All tests passing
- [ ] Coverage maintained (80%+)

## Checklist
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] No new warnings generated
- [ ] Tests pass locally
- [ ] Commits follow conventional format
```

#### PR Review Process

- **Code review**: At least 1 approval required
- **CI checks**: All automated checks must pass
- **Coverage**: No decrease in coverage
- **Conflicts**: Must resolve merge conflicts
- **Feedback**: Respond to all review comments

## Documentation Contributions

### Improving Documentation

1. **Identify missing docs** - Areas lacking clarity
2. **Update existing docs** - Fix errors, improve examples
3. **Add new docs** - Document new features
4. **Fix typos** - Grammar and spelling

### Documentation Style

- Use clear, concise language
- Include examples for all features
- Use proper markdown formatting
- Add code snippets where helpful
- Include diagrams for complex concepts

**Example documentation:**
```markdown
## Agent Communication Protocol

Agents communicate through a shared state object that is validated
and persisted after each agent execution.

### Message Format

```python
class AgentMessage(BaseModel):
    agent_id: str          # Unique agent identifier
    role: str              # Agent's primary role
    content: str           # Human-readable message
    artifacts: dict        # Structured data for next agent
```

### Example

```python
message = AgentMessage(
    agent_id="planning_001",
    role="planning",
    content="Created requirements and task breakdown",
    artifacts={
        "requirements": "...",
        "tasks": [...]
    }
)
```

See [Agent Specs](agents/) for complete agent documentation.
```

## Recognition

- All contributors acknowledged in CONTRIBUTORS.md
- Regular contributors added to GitHub team
- Major features highlighted in release notes

## Questions or Need Help?

- **Documentation**: Check [docs/](docs/) first
- **Issues**: Search existing issues before opening new one
- **Discussions**: Use GitHub Discussions for questions
- **Email**: contact@example.com

## License

By contributing, you agree that your contributions will be licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

**Thank you for contributing to Universal Agent Team!** 🎉

Your contributions, whether code, documentation, or feedback, help make this project better for everyone.
