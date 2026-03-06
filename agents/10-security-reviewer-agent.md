# Security Reviewer Agent Specification

## Overview

The Security Reviewer Agent is an optional specialist agent that conducts comprehensive security reviews of system design, identifying vulnerabilities, compliance gaps, and recommending security hardening. It focuses on authentication, authorization, data protection, secure communications, and regulatory compliance (GDPR, HIPAA, SOC2, etc.).

**Agent Type:** Optional Specialist (Phase 4+)
**Invocation Trigger:** Complexity score ≥ 55 + ("auth" OR "security" OR "gdpr" OR "compliance" OR "sensitive" in factors)
**Typical Invocation:** After Architecture Agent, before Development Agents

---

## Role and Responsibilities

### Primary Responsibility

Conduct comprehensive security reviews by analyzing system design for vulnerabilities, compliance gaps, and recommending security hardening measures across authentication, authorization, data protection, and operations.

### Secondary Responsibilities

- Review authentication and authorization design
- Assess data protection and encryption requirements
- Identify OWASP Top 10 vulnerabilities
- Review API security patterns
- Assess compliance requirements (GDPR, HIPAA, SOC2, etc.)
- Review secret management strategy
- Assess infrastructure security
- Design security incident response
- Plan security testing strategy
- Review audit logging requirements

### What This Agent Does NOT Do

- ❌ Implement security code (Backend Agent's role)
- ❌ Design system architecture (Architecture Agent's role)
- ❌ Conduct penetration testing (specialized security role)
- ❌ Write security tests (QA Agent's role)
- ❌ Make compliance decisions (Legal/Compliance role)
- ❌ Execute security incidents (Ops/Security team role)

---

## Input Requirements

### Required Inputs

From `AgentState`:

| Field | Type | Description |
|-------|------|-------------|
| `artifacts` | `dict[str, Any]` | Architecture artifacts containing security design |
| `architecture_doc` | `str` | Architecture document with security decisions |
| `requirements` | `str` | Project requirements, especially security/compliance needs |

**Required Artifacts:**
```python
artifacts["api_specs"] or artifacts["component_specs"]  # To analyze
artifacts["database_schema"]                            # To check data handling
```

### Optional Inputs

| Field | Type | Description |
|-------|------|-------------|
| `compliance_requirements` | `dict` | GDPR, HIPAA, SOC2, PCI-DSS requirements |
| `security_guidelines` | `str` | Organization security policies |
| `threat_model` | `dict` | Identified threats and assets |
| `sensitive_data_types` | `list[str]` | Types of sensitive data handled |

**Optional Context:**
```python
{
    "compliance_frameworks": ["GDPR", "SOC2"],
    "sensitive_data": ["PII", "Payment cards", "Health records"],
    "threat_level": "high",
    "deployment_target": "AWS",
    "user_base": "global",
    "data_residency": "EU",
    "require_encryption_at_rest": true,
    "require_encryption_in_transit": true,
    "require_audit_logging": true,
    "penetration_testing_planned": true
}
```

### Validation Rules

```python
def validate_input(self, state: AgentState) -> bool:
    """
    Validate that state contains sufficient info for security review.

    Returns:
        True if architecture exists for review, False otherwise
    """
    # Check artifacts exist
    if not state.artifacts or not state.architecture_doc:
        self.logger.error("Architecture information required for security review")
        return False

    # Check for API or component specs to analyze
    has_specs = (
        "api_specs" in state.artifacts or
        "component_specs" in state.artifacts or
        "database_schema" in state.artifacts
    )

    if not has_specs:
        self.logger.warning("No specifications found for security review")
        return False

    return True
```

---

## Output Specifications

### Primary Outputs

The Security Reviewer Agent returns a dictionary with these fields:

| Field | Type | Description |
|-------|------|-------------|
| `security_review_report` | `str` | Markdown report with security findings |
| `security_recommendations` | `list[dict]` | Detailed security improvements |
| `compliance_checklist` | `dict` | Compliance framework coverage |
| `threat_model_analysis` | `dict` | Identified threats and mitigations |
| `security_architecture` | `dict` | Recommended security architecture |
| `message` | `str` | Summary of security review |

### Artifacts

The Security Reviewer Agent produces detailed security artifacts:

```python
artifacts = {
    "security_review": {
        "review_timestamp": str,
        "review_depth": "shallow|standard|comprehensive",
        "critical_issues": int,
        "high_issues": int,
        "medium_issues": int,
        "low_issues": int,
        "security_score": float,  # 0-100, higher is better
        "compliance_coverage": float  # % of requirements addressed
    },

    "detailed_findings": {
        "authentication_issues": [
            {
                "severity": "critical|high|medium|low",
                "issue": str,
                "details": str,
                "recommendation": str,
                "implementation_effort": "low|medium|high",
                "security_impact": str
            }
        ],
        "authorization_issues": [...],
        "data_protection_issues": [...],
        "api_security_issues": [...],
        "infrastructure_issues": [...],
        "compliance_gaps": [
            {
                "framework": "GDPR|HIPAA|SOC2|PCI-DSS",
                "requirement": str,
                "gap": str,
                "remediation": str,
                "deadline": str
            }
        ],
        "owasp_top_10": [
            {
                "vulnerability": str,
                "risk_level": "critical|high|medium",
                "presence": bool,
                "mitigation": str
            }
        ]
    },

    "threat_model": {
        "assets": [
            {
                "asset": str,
                "classification": "public|internal|confidential|restricted",
                "value": str,
                "threats": list[str]
            }
        ],
        "threat_scenarios": [
            {
                "scenario": str,
                "threat_actor": str,
                "impact": str,
                "likelihood": "low|medium|high",
                "mitigation": str
            }
        ],
        "attack_surface": list[str]  # Entry points for attackers
    },

    "security_architecture": {
        "authentication": {
            "method": "oauth2|jwt|saml|mfa|...",
            "flow": str,
            "token_expiry": str,
            "refresh_strategy": str,
            "mfa_required": bool
        },
        "authorization": {
            "model": "rbac|abac|pbac",
            "scope_strategy": str,
            "permission_enforcement": str
        },
        "data_protection": {
            "encryption_at_rest": bool,
            "algorithm": str,
            "key_management": str,
            "encryption_in_transit": bool,
            "tls_version": str
        },
        "network_security": {
            "firewalls": bool,
            "network_segmentation": bool,
            "ddos_protection": bool,
            "waf_needed": bool
        },
        "secret_management": {
            "strategy": "env_vars|vault|hsm",
            "rotation_policy": str,
            "access_control": str
        },
        "logging_and_monitoring": {
            "audit_logging": bool,
            "centralized_logging": bool,
            "alerting": bool,
            "incident_response_plan": bool
        }
    },

    "implementation_roadmap": [
        {
            "phase": "immediate|short-term|long-term",
            "items": list[str],
            "timeline": str,
            "effort": str,
            "risk_reduction": float
        }
    ]
}
```

### State Updates

Fields modified in `AgentState`:

```python
{
    "security_review_report": "<security report markdown>",
    "artifacts": {
        ...existing artifacts...,
        "security_review": {...},
        "threat_model": {...},
        "security_architecture": {...}
    },
    "messages": [..., AgentMessage(agent_id="security_001", artifacts={...})],
    "current_phase": "security_review",
    "next_agent": "backend",  # or "frontend", depends on workflow
}
```

---

## Security Review Checks

### Authentication Assessment

**Checks Performed:**
1. Authentication method appropriateness
2. Password policy strength
3. Multi-factor authentication (MFA) requirements
4. Session management and timeouts
5. Credential storage security
6. OAuth2/OpenID Connect implementation
7. JWT token security
8. SAML/SSO integration

**Example Issues:**

```
Authentication Issue (CRITICAL):
  Problem: Passwords stored in plaintext
  Current: User table stores passwords directly
  Risk: Complete compromise if database breached
  Recommendation: Use bcrypt with salt and work factor
  Implementation: Add password hashing to user model

Authentication Issue (HIGH):
  Problem: No MFA for sensitive operations
  Current: Admin login requires only password
  Risk: Credential compromise enables admin access
  Recommendation: Require MFA for admin accounts
  Implementation: Integrate TOTP (Google Authenticator)

Authentication Issue (MEDIUM):
  Problem: Session tokens never expire
  Current: JWT tokens valid indefinitely
  Risk: Compromised token always valid
  Recommendation: Set token expiry to 1 hour
  Implementation: Add exp claim to JWT, refresh mechanism

Authentication Best Practice (MISSING):
  Issue: No account lockout on failed login
  Impact: Enables brute force attacks
  Recommendation: Lock account after 5 failed attempts
  Implementation: Add failed_login_count, locked_until timestamp
```

**Recommended Authentication Flow:**
```
1. User enters email + password
2. Backend validates credentials (bcrypt verify)
3. If valid, generate JWT tokens:
   - Access token (short-lived, 15-60 minutes)
   - Refresh token (long-lived, 7-30 days)
4. Return tokens to frontend
5. Frontend stores refresh token securely (httpOnly cookie)
6. Frontend uses access token in Authorization header
7. On access token expiry, use refresh token to get new one
8. On MFA required, redirect to MFA verification
```

### Authorization Assessment

**Checks Performed:**
1. Authorization model appropriateness (RBAC, ABAC, PBAC)
2. Role definition clarity
3. Permission enforcement consistency
4. Privilege escalation risks
5. Scope limitations
6. Cross-tenant isolation
7. Resource-level authorization

**Authorization Models:**

| Model | Use Case | Complexity |
|-------|----------|-----------|
| RBAC | Role-Based | Simple (admin, user) |
| ABAC | Attribute-Based | Complex (attribute-driven) |
| PBAC | Policy-Based | Very Complex (policy engine) |
| IBAC | Identity-Based | Medium (identity + context) |

**Example Issues:**

```
Authorization Issue (CRITICAL):
  Problem: No authorization check on data access
  Current: Users can access any todo by ID
  Risk: Users can view/modify other users' data
  Recommendation: Enforce ownership check
  Implementation:
    @require_auth
    def get_todo(todo_id):
        todo = db.get_todo(todo_id)
        if todo.user_id != current_user.id:
            raise Forbidden()
        return todo

Authorization Issue (HIGH):
  Problem: Admin flag bypass possible
  Current: Client sends admin=true, server accepts
  Risk: Non-admin users can elevate privileges
  Recommendation: Only check server-side role
  Implementation: Store role in JWT, verify server-side

Authorization Issue (MEDIUM):
  Problem: No permission inheritance for sub-resources
  Current: Can create resources but can't list own resources
  Recommendation: Implement recursive permission checks
  Implementation: parent_id checks in authorization middleware

Best Practice (MISSING):
  Issue: No role-based rate limiting
  Impact: Users can abuse API regardless of role
  Recommendation: Different limits for different roles
  Implementation: Rate limit based on user.role
```

### Data Protection Assessment

**Checks Performed:**
1. Encryption at rest (database, backups)
2. Encryption in transit (TLS/HTTPS)
3. Sensitive data handling (PII, payment info)
4. Data retention policies
5. Data deletion/anonymization
6. Backup security
7. Key management

**Example Issues:**

```
Data Protection Issue (CRITICAL):
  Problem: No encryption at rest for sensitive data
  Current: Passwords, SSNs stored in plaintext database
  Risk: Database breach exposes sensitive data
  Recommendation: Enable database encryption at rest
  Implementation:
    - PostgreSQL: Use pgcrypto for column encryption
    - AWS RDS: Enable encryption at rest with KMS

Data Protection Issue (HIGH):
  Problem: Passwords not hashed
  Current: SELECT password FROM users WHERE email=?
  Risk: Password reuse across services compromised
  Recommendation: Use bcrypt/Argon2
  Implementation:
    bcrypt.hashpw(password.encode(), bcrypt.gensalt())

Data Protection Issue (HIGH):
  Problem: No HTTPS enforcement
  Current: API accepts both HTTP and HTTPS
  Risk: Man-in-the-middle attacks possible
  Recommendation: Redirect all HTTP to HTTPS
  Implementation:
    - Add HSTS header: Strict-Transport-Security: max-age=31536000
    - Configure web server to force HTTPS
    - Get TLS certificate (Let's Encrypt free)

Data Protection Issue (MEDIUM):
  Problem: API keys sent in URL
  Current: ?api_key=secret123
  Risk: Logged in access logs, browser history
  Recommendation: Use Authorization header
  Implementation:
    Authorization: Bearer <api_key>
    # Do not log Authorization header value

Best Practice (MISSING):
  Issue: No field-level encryption
  Current: All database columns encrypted uniformly
  Recommendation: Extra encryption for PII fields
  Implementation:
    - Encrypt SSN, date_of_birth, payment_methods separately
    - Use different keys for different data sensitivity
```

### API Security Assessment

**Checks Performed:**
1. Input validation completeness
2. Rate limiting implementation
3. CORS configuration
4. SQL injection prevention
5. XSS prevention
6. CSRF protection
7. API authentication on all endpoints

**Example Issues:**

```
API Security Issue (CRITICAL):
  Problem: No input validation on create endpoints
  Current: POST /api/users { email: user_input }
  Risk: SQL injection, invalid data in database
  Recommendation: Validate and sanitize all inputs
  Implementation:
    from pydantic import BaseModel, validator
    class CreateUserRequest(BaseModel):
        email: EmailStr
        password: str = Field(min_length=8)

        @validator('password')
        def password_strength(cls, v):
            if not any(c.isupper() for c in v):
                raise ValueError('Must include uppercase')
            return v

API Security Issue (HIGH):
  Problem: No rate limiting
  Current: Attackers can spam API endpoints
  Risk: Denial of service, brute force attacks
  Recommendation: Implement rate limiting
  Implementation:
    - Basic: 100 requests per minute per IP
    - Advanced: Different limits by endpoint type
    - Use Redis for distributed rate limiting

API Security Issue (HIGH):
  Problem: Overly permissive CORS
  Current: Access-Control-Allow-Origin: *
  Risk: Any website can access API
  Recommendation: Restrict to known origins
  Implementation:
    Access-Control-Allow-Origin: https://trusted.com

API Security Issue (MEDIUM):
  Problem: Sensitive errors revealed
  Current: 500 error shows full stack trace
  Risk: Information disclosure about infrastructure
  Recommendation: Generic error messages in production
  Implementation:
    try:
        ...
    except Exception as e:
        logger.error(f"Error: {e}")
        return {"error": "Internal server error"}

OWASP Top 10 Assessment:
✓ A1: Broken Access Control - ✅ Implemented
✗ A2: Cryptographic Failures - ⚠️ Partial (no field encryption)
✓ A3: Injection - ✅ Implemented (ORM + validation)
✓ A4: Insecure Design - ✅ Threat model reviewed
✓ A5: Security Misconfiguration - ✅ Reviewed
✓ A6: Vulnerable Components - ✅ Deps scanned
✓ A7: Auth Failures - ✅ MFA implemented
⚠️ A8: Software/Data Integrity - ⚠️ No signing
✓ A9: Logging/Monitoring Failures - ✅ Audit logging
✓ A10: SSRF - ✅ Input validation
```

### Compliance Assessment

**Frameworks:**
- **GDPR**: EU data protection (user consent, data deletion, privacy)
- **HIPAA**: Health insurance (encryption, audit trails, business associate agreements)
- **SOC2**: Service organization controls (access, monitoring, incident response)
- **PCI-DSS**: Payment card industry (encryption, secure transmission, assessment)

**Example Findings:**

```
GDPR Compliance Assessment:
✓ Requirement: User consent for data processing
  Status: ✅ IMPLEMENTED
  Evidence: Consent form with opt-in checkboxes

✗ Requirement: Right to be forgotten (data deletion)
  Status: ❌ NOT IMPLEMENTED
  Gap: No mechanism to delete user data
  Remediation:
    1. Create soft-delete on users table
    2. Implement DELETE /api/v1/users/me endpoint
    3. Cascade delete to all user data (orders, preferences, etc.)
    Timeline: 2 weeks

✗ Requirement: Data portability
  Status: ❌ NOT IMPLEMENTED
  Gap: Users cannot download their data
  Remediation:
    1. Create GET /api/v1/users/me/export endpoint
    2. Return JSON/CSV of all user data
    3. Timeline: 3 weeks

✗ Requirement: Privacy by design
  Status: ⚠️ PARTIAL
  Gap: No data minimization, collect too much data
  Remediation:
    1. Remove unnecessary fields (phone_number not needed)
    2. Implement data retention limits (delete after 90 days)
    3. Timeline: 4 weeks

SOC2 Type II Compliance Gap:
Requirement: Change management process
Status: ❌ NOT IMPLEMENTED
Gap: No formal process for approving code changes
Remediation:
  1. Implement code review requirement (2 reviewers)
  2. Create change log documentation
  3. Test changes before production
  Timeline: 1 week
```

---

## LLM Configuration

### Model

```python
{
    "provider": "anthropic",
    "model": "claude-3-5-sonnet-20241022",
    "temperature": 0.1,
    "max_tokens": 8000,
    "timeout": 180
}
```

### Rationale

- **Very low temperature (0.1)**: Security requires precision, no creative risks
- **Claude 3.5 Sonnet**: Excellent at threat analysis and pattern recognition
- **8000 tokens**: Sufficient for comprehensive security findings
- **180s timeout**: Security analysis is thorough; more time needed

---

## System Prompt

```
You are a senior security architect and cybersecurity expert with deep knowledge of
application security, data protection, compliance frameworks, and threat modeling.

Your responsibilities:
1. Conduct comprehensive security reviews of system design
2. Identify vulnerabilities and security gaps
3. Assess compliance with regulations (GDPR, HIPAA, SOC2, PCI-DSS)
4. Review authentication and authorization design
5. Assess data protection and encryption strategy
6. Identify OWASP Top 10 vulnerabilities
7. Create threat models
8. Design security architecture and hardening measures
9. Create incident response recommendations

Security Principles:
- Defense in depth: Multiple security layers
- Least privilege: Users have minimum necessary permissions
- Fail securely: Defaults deny, explicit allow
- Security by design: Not an afterthought
- Assume breach: Design for compromise detection
- Zero trust: Verify every access request

Authentication Best Practices:
- Password security: Bcrypt/Argon2, salt, work factor
- Multi-factor authentication: For sensitive operations
- Session management: Short-lived tokens, secure storage
- Token security: Signed JWTs, expiration, refresh mechanism
- Credential storage: Never plaintext, use secure hashing

Authorization Best Practices:
- Role-Based Access Control (RBAC): Simple, role-based
- Attribute-Based (ABAC): Complex, attribute-driven
- Principle of least privilege: Minimum access needed
- Separation of duties: No single person has all permissions
- Regular access reviews: Periodic permission audits

Data Protection:
- Encryption at rest: Database encryption + key management
- Encryption in transit: TLS 1.3, HTTPS everywhere
- Sensitive data handling: PII, payment info, health records
- Data retention: Periodic deletion, compliance with regulations
- Backup security: Encrypt backups, test restore procedures

API Security:
- Input validation: Whitelist allowed, reject invalid
- Rate limiting: Prevent abuse, differentiate by role
- CORS configuration: Restrict to known origins only
- SQL injection prevention: Use parameterized queries/ORM
- XSS prevention: Escape output, Content-Security-Policy
- CSRF protection: Same-site cookies, CSRF tokens

Network Security:
- Firewalls: Restrict traffic, default deny
- Network segmentation: Isolate services, VPCs
- DDoS protection: Rate limiting, CDN protection
- Web Application Firewall (WAF): Detect/block attacks
- VPN/TLS: Encrypted inter-service communication

Secret Management:
- Never hardcode: Use environment variables or vault
- Rotation policy: Regular credential rotation
- Access control: Restrict secret access to services needing it
- Audit trail: Log secret access attempts
- Tools: Vault, AWS Secrets Manager, HashiCorp Consul

Compliance Frameworks:
- GDPR: User consent, data deletion, privacy by design
- HIPAA: Encryption, audit trails, BAA agreements
- SOC2: Access controls, monitoring, incident response
- PCI-DSS: Payment card data protection standards

OWASP Top 10 (2021):
1. Broken Access Control
2. Cryptographic Failures
3. Injection
4. Insecure Design
5. Security Misconfiguration
6. Vulnerable and Outdated Components
7. Authentication Failures
8. Software and Data Integrity Failures
9. Logging and Monitoring Failures
10. Server-Side Request Forgery (SSRF)

Output Requirements:
1. Security review report (markdown) with:
   - Executive summary with critical issues
   - Authentication/authorization assessment
   - Data protection analysis
   - API security evaluation
   - Compliance gap analysis
   - OWASP Top 10 assessment
2. Threat model:
   - Asset identification
   - Threat scenarios
   - Attack surface analysis
   - Risk assessment
3. Security architecture recommendations:
   - Authentication/authorization design
   - Data protection strategy
   - Network security measures
   - Secret management
   - Logging and monitoring
4. Implementation roadmap:
   - Immediate critical fixes
   - Short-term improvements
   - Long-term hardening
   - Timeline and effort estimates

Remember: Security is not 100% possible, but defense in depth and risk management
minimize vulnerabilities. Be thorough, specific, and actionable in recommendations.
```

---

## When to Invoke This Agent

### Complexity Thresholds

| Complexity | Threshold | Invocation Logic |
|-----------|-----------|------------------|
| Low (1-40) | N/A | ❌ Not invoked (unless auth required) |
| Medium (41-55) | 55 | ⚠️ Invoked if security factors present |
| Medium-High (56-70) | ≥55 | ✅ Invoked if security/auth required |
| High (71-85) | ≥55 | ✅ Always invoked |
| Very High (86-100) | ≥55 | ✅ Always invoked |

### Invocation Conditions

The Security Reviewer Agent is triggered when:

1. **Complexity score ≥ 55** AND
2. **At least one factor present:**
   - "auth" or "authentication" in requirements
   - "security" mentioned explicitly
   - "gdpr" or "gdpr compliance" mentioned
   - "sensitive data" or "pii" mentioned
   - "payment" or "payment processing" mentioned
   - "healthcare" or "hipaa" mentioned
   - "compliance" mentioned
   - API endpoints exposed (api_specs exists)
   - User authentication required

3. **Optional: Boost triggers:**
   - Regulatory compliance required
   - Sensitive data handling
   - Public API exposure
   - High-risk application domain
   - Multi-tenant system
   - Data crossing borders

### Decision Logic (Pseudo-code)

```python
def should_invoke_security_reviewer(state: AgentState) -> bool:
    """Determine if Security Reviewer should run."""

    # Check complexity threshold
    if not state.complexity_score or state.complexity_score < 55:
        return False

    # Check for security-related factors
    security_factors = [
        "auth", "security", "gdpr", "compliance",
        "sensitive", "pii", "payment", "healthcare", "hipaa"
    ]
    combined_text = (
        state.requirements +
        state.architecture_doc +
        str(state.artifacts)
    ).lower()

    has_security_factor = any(factor in combined_text for factor in security_factors)

    # If explicit security factors, invoke
    if has_security_factor:
        return True

    # If API exists and complexity > 55, invoke
    if state.artifacts.get("api_specs") and state.complexity_score > 55:
        return True

    return False
```

---

## Workflow Integration

### Prerequisites

**Should be completed before Security Reviewer runs:**
- Architecture Agent has completed
- System design artifacts available
- API or component specifications present
- Complexity score ≥ 55

### Triggers

The Security Reviewer Agent is triggered when:
1. Architecture Agent completes with security factors detected
2. Orchestrator selector identifies Security Reviewer as applicable
3. `current_phase == "design"` OR `current_phase == "architecture"`

### Execution Context

The Security Reviewer is executed:
- **When:** After Architecture Agent, before Development Agents
- **Why:** To identify security issues before implementation
- **Cost:** 1 API call (LLM) per project
- **Duration:** ~2-3 minutes (comprehensive analysis)

### Output Routing

After Security Reviewer completes:

**Success Path:**
```
Security Reviewer
      ↓
  Frontend/Backend Agent
```

**With Critical Issues:**
```
Security Reviewer
      ↓
  Human Review (requires_human_approval = true)
      ↓
  Architecture Agent (if major redesign needed)
```

---

## Integration Examples

### Example 1: Simple Todo App (Not Triggered)

**Input Scenario:**
- Project: Simple todo app
- Complexity: 40
- No authentication required
- No sensitive data
- Result: Security Reviewer NOT invoked

### Example 2: E-Commerce with Payments (Triggered)

**Input Scenario:**
- Project: E-commerce platform
- Complexity: 75
- Factors: ["payment", "security", "sensitive_data"]
- Stores: payment card tokens, user PII

**Security Findings:**

```
CRITICAL SECURITY ISSUES (5):
1. PCI-DSS Violation: Storing payment card data
   Current: Saving card numbers in database
   Risk: Massive compliance violation + liability
   Fix: Use payment processor (Stripe, Square)
   Timeline: 1-2 weeks

2. No encryption of sensitive data
   Current: Storing SSN, phone in plaintext
   Risk: Database breach exposes PII
   Fix: Encrypt SSN, DOB, phone at field level
   Timeline: 1 week

3. Authentication not enforced on API
   Current: /api/users/{id} accessible without auth
   Risk: Users can access other users' data
   Fix: Add JWT auth check to all endpoints
   Timeline: 1 day

4. Passwords not hashed
   Current: Stored as plaintext
   Risk: Complete user account compromise
   Fix: Use bcrypt.hashpw() with 12+ rounds
   Timeline: 1 day

5. No HTTPS
   Current: API accepts HTTP
   Risk: Man-in-the-middle attacks
   Fix: Enable TLS 1.3, redirect HTTP to HTTPS
   Timeline: 1 day

HIGH SEVERITY ISSUES (4):
1. No MFA for admin accounts
   Fix: Implement TOTP-based MFA
   Timeline: 1 week

2. CORS allows all origins
   Current: Access-Control-Allow-Origin: *
   Fix: Restrict to known domains
   Timeline: 1 day

3. No rate limiting
   Risk: Brute force attacks, DoS
   Fix: Implement Redis-based rate limiting
   Timeline: 1 week

4. Audit logging missing
   Current: No log of sensitive operations
   Fix: Log all auth events, data access
   Timeline: 1 week

COMPLIANCE GAPS:
GDPR:
  ✗ No data deletion mechanism (Right to be forgotten)
    Timeline: 3 weeks
  ✗ No consent recording
    Timeline: 1 week
  ✗ No data export (Data portability)
    Timeline: 2 weeks

PCI-DSS:
  ✗ Entire framework not addressed
    Action: Use payment processor, not store cards
    Timeline: 2 weeks (implementation)

THREAT MODEL:
Attack Surface:
- User login endpoint (brute force)
- Payment endpoint (injection, fraud)
- Admin dashboard (privilege escalation)
- Database (SQL injection if unsanitized inputs)

Threat Scenarios:
1. Attacker brute forces user password
   Mitigation: Rate limiting, account lockout
   Priority: CRITICAL

2. Admin account compromised
   Mitigation: MFA, session monitoring
   Priority: CRITICAL

3. Payment card theft
   Mitigation: Use payment processor, never store
   Priority: CRITICAL

4. GDPR violation fine
   Mitigation: Implement deletion, consent, export
   Priority: HIGH (legal liability)
```

**Security Architecture Recommendations:**

```python
artifacts["security_architecture"] = {
    "authentication": {
        "method": "JWT + Refresh Token",
        "mfa_required": "admin only",
        "flow": "Email+password → JWT + refresh token",
        "token_expiry": "15 minutes",
        "refresh_strategy": "7-day rotating refresh tokens"
    },
    "authorization": {
        "model": "RBAC",
        "roles": ["admin", "seller", "customer"],
        "enforcement": "Middleware on all endpoints"
    },
    "data_protection": {
        "encryption_at_rest": True,
        "algorithm": "AES-256-GCM",
        "key_management": "AWS KMS",
        "encryption_in_transit": True,
        "tls_version": "1.3"
    },
    "payment_handling": {
        "strategy": "Never store cards",
        "processor": "Stripe or Square",
        "tokenization": "Use processor tokens",
        "pci_compliance": "Fully delegated to processor"
    },
    "gdpr_compliance": {
        "consent_mechanism": "Explicit opt-in",
        "data_deletion": "Soft-delete with purge schedule",
        "data_export": "JSON export endpoint",
        "data_residency": "EU servers for EU users"
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
        "errors": ["Cannot review security without architecture"],
        "message": "Architecture required for security assessment",
        "next_agent": "architecture"
    }
```

### Recovery Strategies

1. **Insufficient Specifications**: Continue with available information
2. **Invalid Compliance Requirements**: Use common frameworks (GDPR, SOC2)
3. **Missing Threat Model**: Generate from architecture analysis
4. **LLM Timeout**: Focus on OWASP Top 10 + basic security

---

## Tools and Capabilities

### Available Tools

| Tool | Purpose | Usage |
|------|---------|-------|
| `threat_modeler` | Create threat models | STRIDE analysis |
| `compliance_checker` | Check frameworks | GDPR, HIPAA, SOC2 |
| `vulnerability_scanner` | Find known vulns | CVE databases |
| `encryption_recommender` | Recommend encryption | Algorithm selection |

### Permissions

- ✅ Read: `artifacts`, `architecture_doc`, `requirements`, `messages`
- ✅ Write: `security_review_report`, `artifacts` (security_* fields)
- ✅ Modify: None (read-only review)
- ❌ Code execution: Not required
- ❌ External API calls: Not required

---

## Success Criteria

The Security Reviewer Agent has succeeded when:

1. ✅ Authentication/authorization design reviewed
2. ✅ Data protection gaps identified
3. ✅ OWASP Top 10 vulnerabilities assessed
4. ✅ Compliance requirements mapped (if applicable)
5. ✅ Threat model created
6. ✅ Detailed security findings documented
7. ✅ Security architecture recommended
8. ✅ Implementation roadmap created

**Metrics:**
- Issues identified: All critical + high priority
- Compliance coverage: % of applicable frameworks
- Recommendations: Specific and actionable
- Report quality: Complete with context

---

## Phase Integration

**Belongs to:** Phase 4 - Optional Specialist Agents
**Invoked by:** Complexity-based Specialist Agent Selector
**Supports:** Backend/Frontend Development Agents (implement recommendations)

**Timeline:**
- After: Architecture Design Agent
- Before: Backend/Frontend Development Agents
- Parallel: Contract Validator, Component Designer, Data Modeler

---

## References and External Links

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [GDPR Compliance](https://gdpr-info.eu/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [CWE/SANS Top 25](https://cwe.mitre.org/top25/)
- [CERT Secure Coding](https://wiki.sei.cmu.edu/confluence/display/seccode/)
- [Threat Modeling](https://threatdragon.org/)
- [Security Headers](https://securityheaders.com/)

---

**Last Updated:** 2026-03-06
**Status:** Phase 4 - Optional Specialist
**Version:** 1.0
