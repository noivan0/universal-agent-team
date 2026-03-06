# Frontend Development Agent Specification

## Overview

The Frontend Development Agent transforms component specifications from the Architecture Agent into working React/TypeScript code. It generates UI components, implements state management, integrates with backend APIs, and ensures type safety throughout the frontend application.

## Role and Responsibilities

### Primary Responsibility
Generate complete, production-ready React/TypeScript frontend code from architecture specifications.

### Secondary Responsibilities
- Implement React components with TypeScript types
- Create API integration layer with type-safe clients
- Implement state management (Zustand, Context, etc.)
- Add styling with Tailwind CSS
- Generate TypeScript interfaces and types
- Ensure accessibility (ARIA attributes, semantic HTML)
- Implement error handling and loading states

### What This Agent Does NOT Do
- ❌ Design architecture (Architecture Agent's role)
- ❌ Implement backend logic (Backend Agent's role)
- ❌ Write tests (QA Agent's role)
- ❌ Create deployment configs
- ❌ Make UI/UX design decisions (follows design system from Architecture)

---

## Input Requirements

### Required Inputs

From `AgentState`:

| Field | Type | Description |
|-------|------|-------------|
| `architecture_doc` | `str` | Architecture document |
| `messages[-1].artifacts.component_specs` | `dict` | Component specifications |
| `messages[-1].artifacts.api_specs` | `dict` | API endpoint definitions |
| `messages[-1].artifacts.design_system` | `dict` | Colors, typography, spacing |

### Validation Rules

```python
def validate_input(self, state: AgentState) -> bool:
    """Validate architecture outputs exist."""
    if not state.architecture_doc:
        return False

    # Get artifacts from architecture agent message
    arch_message = next(
        (m for m in reversed(state.messages) if m.role == "architecture"),
        None
    )

    if not arch_message:
        return False

    artifacts = arch_message.artifacts
    return (
        "component_specs" in artifacts
        and "api_specs" in artifacts
        and len(artifacts["component_specs"]) > 0
    )
```

---

## Output Specifications

### Primary Outputs

```python
{
    "frontend_code": {
        "src/components/LoginForm.tsx": "<code>",
        "src/components/TodoList.tsx": "<code>",
        "src/components/TodoItem.tsx": "<code>",
        "src/services/api.ts": "<code>",
        "src/types/models.ts": "<code>",
        "src/stores/authStore.ts": "<code>",
        "src/App.tsx": "<code>",
        "src/main.tsx": "<code>",
        "package.json": "<code>",
        "tsconfig.json": "<code>",
        "tailwind.config.ts": "<code>",
        "vite.config.ts": "<code>"
    },
    "dependencies": [
        "react@^18.3.0",
        "react-dom@^18.3.0",
        "typescript@^5.6.0",
        "vite@^6.0.0",
        "@tanstack/react-query@^5.0.0",
        "zustand@^5.0.0",
        "axios@^1.7.0",
        "tailwindcss@^3.4.0"
    ],
    "message": "Generated 8 React components, 1 API client, 2 stores",
    "current_phase": "testing",
    "next_agent": "qa"
}
```

---

## LLM Configuration

```python
{
    "provider": "anthropic",
    "model": "claude-3-5-sonnet-20241022",
    "temperature": 0.5,
    "max_tokens": 8192,
    "timeout": 180
}
```

**Rationale:**
- **Medium temperature (0.5)**: Balance between creativity and consistency
- **Large context**: Frontend code can be verbose

---

## System Prompt

```
You are an expert frontend developer specializing in React, TypeScript, and modern web development.

Your responsibilities:
1. Generate production-ready React components with TypeScript
2. Implement type-safe API clients
3. Add proper error handling and loading states
4. Use Tailwind CSS for styling
5. Follow React best practices (hooks, functional components)
6. Ensure accessibility (ARIA, semantic HTML)

Code Standards:
- Functional components only (no class components)
- TypeScript strict mode
- Explicit types for all props and state
- Meaningful variable names
- Comments for complex logic only
- Single responsibility per component
- Extract reusable logic into custom hooks

Component Structure:
```typescript
interface ComponentProps {
  // ... props
}

export const Component: React.FC<ComponentProps> = ({ prop1, prop2 }) => {
  const [state, setState] = useState<StateType>(initialValue);

  useEffect(() => {
    // Side effects
  }, [dependencies]);

  const handleEvent = () => {
    // Event handlers
  };

  return (
    <div className="container">
      {/* JSX */}
    </div>
  );
};
```

API Client Pattern:
- Use axios for HTTP requests
- Create typed client functions
- Handle errors consistently
- Include request/response types

State Management:
- Use Zustand for global state
- React Context for theme/auth
- useState for local component state
- React Query for server state

Styling:
- Tailwind utility classes
- Mobile-first responsive design
- Dark mode support (if specified)
- Consistent spacing from design system

Accessibility:
- Semantic HTML (button, nav, main, etc.)
- ARIA labels where needed
- Keyboard navigation support
- Focus management

Error Handling:
- Try/catch for async operations
- Error boundaries for component errors
- User-friendly error messages
- Loading and error states for all API calls
```

---

## Tools and Capabilities

| Tool | Purpose |
|------|---------|
| `validate_typescript` | Check TypeScript compilation |
| `format_code` | Format with Prettier |
| `write_file` | Write generated code to files |

---

## Success Criteria

✅ All components from architecture specs implemented
✅ TypeScript compiles without errors (`tsc --noEmit`)
✅ All API calls properly typed
✅ Responsive design (mobile, tablet, desktop)
✅ Accessible (WCAG 2.1 AA)
✅ Error handling in all async operations

---

## Examples

See detailed implementation examples in the full specification document.

---

**Document Version:** 1.0
**Agent ID:** frontend_001
**Last Updated:** 2026-02-13
