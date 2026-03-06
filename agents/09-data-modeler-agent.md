# Data Modeler Agent Specification

## Overview

The Data Modeler Agent is an optional specialist agent that reviews and enhances database schema design, data models, and data flow. It specializes in projects with complex data requirements, ensuring optimal performance, data integrity, and scalability. This agent validates normalization, identifies optimization opportunities, and designs data access patterns.

**Agent Type:** Optional Specialist (Phase 4+)
**Invocation Trigger:** Complexity score ≥ 65 + ("database" OR "data" OR "complex" in factors)
**Typical Invocation:** After Architecture Agent, before Backend Agent

---

## Role and Responsibilities

### Primary Responsibility

Review and enhance database schema design by validating normalization, optimizing for query performance, ensuring data integrity, and recommending data access patterns.

### Secondary Responsibilities

- Validate database normalization (3NF minimum)
- Optimize indexes and query patterns
- Design data access layer strategies
- Identify denormalization opportunities
- Plan data migration strategies
- Review data retention policies
- Design audit and versioning strategies
- Optimize for specific use cases (OLTP, analytical, etc.)
- Plan database scaling strategies
- Review referential integrity constraints

### What This Agent Does NOT Do

- ❌ Implement database code (Backend Agent's role)
- ❌ Design system architecture (Architecture Agent's role)
- ❌ Select technologies (Architecture Agent's role)
- ❌ Write migrations (Backend Agent's role)
- ❌ Write tests (QA Agent's role)
- ❌ Make business logic decisions

---

## Input Requirements

### Required Inputs

From `AgentState`:

| Field | Type | Description |
|-------|------|-------------|
| `artifacts` | `dict[str, Any]` | Architecture artifacts containing `database_schema` |
| `architecture_doc` | `str` | Architecture document with data design decisions |
| `requirements` | `str` | Project requirements, especially data requirements |

**Database Schema Structure (Required):**
```python
artifacts["database_schema"] = {
    "tables": {
        "<table_name>": {
            "columns": {
                "<column_name>": {
                    "type": str,              # "VARCHAR", "INTEGER", "UUID", etc.
                    "nullable": bool,
                    "default": Any,           # Optional
                    "unique": bool,           # Optional
                    "primary_key": bool       # Optional
                }
            },
            "indexes": [
                {
                    "name": str,
                    "columns": list[str],
                    "unique": bool
                }
            ],
            "constraints": [
                {
                    "type": "PRIMARY_KEY|FOREIGN_KEY|UNIQUE|CHECK",
                    "columns": list[str],
                    "references": dict        # For foreign keys
                }
            ],
            "relationships": {
                "<foreign_key_column>": {
                    "references_table": str,
                    "references_column": str,
                    "on_delete": "CASCADE|SET_NULL|RESTRICT"
                }
            }
        }
    },
    "migrations": list[str]                   # Migration steps
}
```

### Optional Inputs

| Field | Type | Description |
|-------|------|-------------|
| `data_volume_estimates` | `dict` | Expected row counts per table |
| `query_patterns` | `list[dict]` | Typical queries and access patterns |
| `performance_targets` | `dict` | Query performance requirements |
| `data_governance` | `dict` | GDPR, data retention, compliance |

**Optional Context:**
```python
{
    "database_type": "postgresql",           # "postgresql", "mysql", "mongodb"
    "expected_scale": "millions",            # "thousands", "millions", "billions"
    "data_growth_rate": "1GB/month",
    "query_complexity": "high",
    "read_write_ratio": "10:1",
    "analytics_required": true,
    "real_time_analytics": false,
    "data_warehouse": false,
    "gdpr_compliance": true,
    "audit_trail_required": true
}
```

### Validation Rules

```python
def validate_input(self, state: AgentState) -> bool:
    """
    Validate that state contains database schema to model.

    Returns:
        True if schema is present and valid, False otherwise
    """
    # Check artifacts contain database_schema
    if not state.artifacts or "database_schema" not in state.artifacts:
        self.logger.error("No database schema found in artifacts")
        return False

    schema = state.artifacts["database_schema"]
    if not schema or "tables" not in schema:
        self.logger.error("database_schema missing tables definition")
        return False

    tables = schema["tables"]
    if not tables or not isinstance(tables, dict):
        self.logger.error("tables is empty or not a dict")
        return False

    # Validate each table has columns
    for table_name, table_def in tables.items():
        if "columns" not in table_def or not table_def["columns"]:
            self.logger.error(f"Table {table_name} has no columns")
            return False

    return True
```

---

## Output Specifications

### Primary Outputs

The Data Modeler Agent returns a dictionary with these fields:

| Field | Type | Description |
|-------|------|-------------|
| `data_modeling_report` | `str` | Markdown report with modeling findings |
| `optimized_schema` | `dict` | Enhanced database schema with improvements |
| `query_patterns` | `list[dict]` | Recommended query patterns and access patterns |
| `migration_strategy` | `str` | Data migration and initialization strategy |
| `performance_recommendations` | `list[str]` | Index and query optimization recommendations |
| `message` | `str` | Summary of data modeling work |

### Artifacts

The Data Modeler Agent produces detailed data modeling artifacts:

```python
artifacts = {
    "data_modeling": {
        "tables_analyzed": int,
        "normalization_issues": int,
        "index_opportunities": int,
        "denormalization_candidates": int,
        "modeling_score": float,  # 0-100, higher is better
        "modeling_timestamp": str
    },

    "detailed_findings": {
        "normalization_issues": [
            {
                "table": str,
                "severity": "critical|warning|info",
                "issue": str,
                "current_state": str,
                "recommended_state": str,
                "impact": str
            }
        ],
        "index_recommendations": [
            {
                "table": str,
                "columns": list[str],
                "type": "btree|hash|gist|gin",
                "benefit": str,
                "estimated_improvement": str
            }
        ],
        "denormalization_opportunities": [
            {
                "reason": str,
                "tables_affected": list[str],
                "trade_offs": str,
                "benefit": str
            }
        ],
        "data_integrity_issues": [
            {
                "table": str,
                "issue": str,
                "impact": str,
                "solution": str
            }
        ],
        "scalability_concerns": [
            {
                "concern": str,
                "tables_affected": list[str],
                "mitigation": str
            }
        ]
    },

    "optimized_specs": {
        # Enhanced database_schema with improvements
        "tables": {...},
        "views": {...},                # Recommended materialized views
        "partitioning_strategy": {...}, # For large tables
        "archival_strategy": {...}      # For old data
    },

    "access_patterns": {
        "<pattern_name>": {
            "description": str,
            "primary_query": str,
            "tables_involved": list[str],
            "indexes_needed": list[str],
            "estimated_latency": str,
            "caching_strategy": str
        }
    },

    "performance_targets": {
        "query_benchmarks": {
            "<query_name>": {
                "target_latency": str,
                "expected_rows": int,
                "indexes": list[str]
            }
        },
        "scaling_plan": {
            "sharding_strategy": str,
            "read_replicas": bool,
            "connection_pooling": bool
        }
    }
}
```

### State Updates

Fields modified in `AgentState`:

```python
{
    "data_modeling_report": "<modeling report markdown>",
    "artifacts": {
        ...existing artifacts...,
        "data_modeling": {...},
        "optimized_schema": {...},
        "access_patterns": {...}
    },
    "messages": [..., AgentMessage(agent_id="modeler_001", artifacts={...})],
    "current_phase": "data_modeling",
    "next_agent": "backend"
}
```

---

## Data Modeling Review Checks

### Normalization Analysis

**Checks Performed:**
1. First Normal Form (1NF): No repeating groups
2. Second Normal Form (2NF): No partial dependencies
3. Third Normal Form (3NF): No transitive dependencies
4. BCNF analysis for complex dependencies

**Issue Examples:**

```
Normalization Issue (CRITICAL):
  Table: UserPreferences
  Problem: Violates 1NF - repeating column group
  Current: contact_phone_1, contact_phone_2, contact_phone_3
  Issue: Multiple phone numbers in single row
  Recommendation: Extract to separate ContactPhone table
  Structure:
    Users (user_id, email, name)
    ContactPhone (phone_id, user_id, phone_number, type)

Normalization Issue (WARNING):
  Table: Orders
  Problem: Transitive dependency (violates 3NF)
  Current: order_id, customer_id, customer_name, customer_email
  Issue: customer_name and customer_email depend on customer_id, not order_id
  Recommendation: Move to separate Customer table or use FK reference
```

### Index Optimization

**Checks Performed:**
1. Missing indexes on foreign keys
2. Missing indexes on frequently filtered columns
3. Redundant indexes
4. Over-indexing (too many indexes)
5. Missing composite indexes for common queries

**Indexing Strategy:**

| Scenario | Index Type | Benefit | Cost |
|----------|-----------|---------|------|
| Frequent equality filter | B-tree | Fast lookups | Write overhead |
| Range queries | B-tree | Efficient scans | Write overhead |
| Full-text search | GIN | Fast text matching | Larger index |
| JSON fields | GIN/JSONB | Fast JSON queries | Storage |
| Geospatial | GIST | Spatial queries | Complex |

**Example Finding:**
```
Index Recommendations:
1. CREATE INDEX idx_users_email ON users(email);
   Reason: email used in WHERE clauses, login queries
   Query Impact: 10x faster user lookup
   Estimated Size: 50MB for 10M users

2. CREATE INDEX idx_orders_user_created ON orders(user_id, created_at DESC);
   Reason: Composite for "user's recent orders"
   Query Impact: Eliminates sequential scan
   Estimated Size: 200MB for 100M orders

3. CREATE INDEX idx_messages_recipient_read ON messages(recipient_id, is_read);
   Reason: Unread message counts
   Query Impact: 100x faster for unread counts
   Estimated Size: 150MB for 500M messages

Missing Indexes Detected: 5
Redundant Indexes: 2
  - idx_user_id_created (subset of above composite)
  - idx_created_at (rarely used without user_id filter)

Recommendation: Add 5 new, remove 2 redundant
Net impact: +300MB storage, 10-100x faster queries
```

### Data Integrity Analysis

**Checks Performed:**
1. Primary key presence on all tables
2. Foreign key constraints completeness
3. Unique constraints on appropriate columns
4. Check constraints for data validation
5. NOT NULL constraints logic

**Example Issue:**
```
Data Integrity Issue (CRITICAL):
  Table: UserAccounts
  Problem: No foreign key constraint on user_id
  Current: user_id column, no FK reference to Users table
  Issue: Risk of orphaned records if user deleted
  Impact: Data inconsistency, query issues
  Solution: ALTER TABLE UserAccounts ADD CONSTRAINT fk_user_id
           FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE CASCADE

Data Integrity Issue (WARNING):
  Table: Orders
  Problem: order_status has no CHECK constraint
  Current: VARCHAR allowing any value
  Issue: Invalid statuses could be inserted (typos, etc)
  Solution: ALTER TABLE Orders ADD CONSTRAINT check_status
           CHECK (status IN ('pending', 'processing', 'shipped', 'delivered', 'cancelled'))
```

### Query Pattern Analysis

**Common Patterns:**
1. Lookup by ID: Simple equality
2. List with filters: Multiple equality + ordering
3. Search: Contains/LIKE + ordering
4. Aggregation: GROUP BY + HAVING
5. Time-series: Date range + ordering
6. Relationships: Joins across tables

**Example Pattern Analysis:**
```
Query Pattern Identified: "Recent User Orders"
Pattern: SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC LIMIT 20

Current Performance: 500ms (sequential scan)
Root Cause: No index on (user_id, created_at)

Recommendation: CREATE INDEX idx_orders_user_recent
               ON orders(user_id, created_at DESC)

Expected After: 5ms (covered query with index)
Index Size: 200MB for 100M rows
Write Overhead: +2% on INSERT/UPDATE

Decision: ✅ Highly recommended (100x improvement)
```

### Scalability Assessment

**Checks Performed:**
1. Table size projections
2. Index growth implications
3. Query performance at scale
4. Connection pool adequacy
5. Replication strategy needs
6. Sharding candidates

**Example Assessment:**
```
Scalability Concern: User table growth
Current Rows: 1M
Projected (2 years): 100M
Growth Rate: 4x

Impact Analysis:
- Table Size: 1GB → 100GB (manageable)
- Index Size: 500MB → 50GB (manageable)
- Sequential Scans: OK → NOT ACCEPTABLE
- Write TPS: 100 → 10,000 (connection pool needed)

Recommendations:
1. Implement connection pooling (PgBouncer)
2. Add read replicas (1 primary + 2 read replicas)
3. Implement caching layer (Redis)
4. Partition by user_id (sharding) if reaching 1B rows

Timeline: Implement now for headroom
Cost: Low (connection pooling), Medium (replicas), High (sharding)
```

### Denormalization Opportunities

**When to Denormalize:**
1. Aggregation queries expensive (SUM, COUNT)
2. Join-heavy queries slow
3. Real-time analytics needed
4. Caching invalidation complex

**Example Opportunity:**
```
Denormalization Candidate: User statistics
Current: Calculate count(*) from Orders WHERE user_id = ?
Problem: Expensive aggregation query on large table
Solution: Add order_count to Users table
Trade-off: Must update on every order INSERT/DELETE

Benefits:
- User profile query: 1 index lookup (5ms) vs aggregation (500ms)
- 100x faster user statistics

Costs:
- Extra storage: 8 bytes per user (8MB for 1M users)
- Extra write on order creation: +1 UPDATE on users table
- Must maintain consistency

Recommendation: ✅ Implement
Pattern: Trigger-based update on order insert/delete
```

---

## LLM Configuration

### Model

```python
{
    "provider": "anthropic",
    "model": "claude-3-5-sonnet-20241022",
    "temperature": 0.15,
    "max_tokens": 7000,
    "timeout": 150
}
```

### Rationale

- **Low temperature (0.15)**: Data modeling requires precision and consistency
- **Claude 3.5 Sonnet**: Excellent at structured thinking and pattern analysis
- **7000 tokens**: Sufficient for detailed schema analysis and recommendations
- **150s timeout**: Data analysis can be detailed; more time needed

---

## System Prompt

```
You are an expert database architect and data modeler with deep knowledge of
relational database design, normalization, performance tuning, and data architecture.

Your responsibilities:
1. Review database schemas for proper normalization
2. Identify indexes and optimization opportunities
3. Assess data integrity and constraint completeness
4. Analyze query patterns and access paths
5. Recommend denormalization where beneficial
6. Plan scaling and replication strategies
7. Design data archival and retention policies
8. Review data consistency and ACID properties

Database Design Best Practices:
- Normalization: Aim for 3NF minimum, BCNF when possible
- Constraints: Use primary keys, foreign keys, unique constraints
- Indexes: Strategic placement for common query patterns
- Performance: Balance normalization against query efficiency
- Scalability: Design for growth, plan sharding early
- Data Integrity: Referential integrity, cascading updates/deletes
- Archival: Strategy for old data (archive, compress, delete)
- Audit Trail: Track changes, maintain history when needed

Normalization Levels:
- 1NF: Atomic values, no repeating groups
- 2NF: 1NF + no partial dependencies (all non-key attrs depend on whole key)
- 3NF: 2NF + no transitive dependencies (non-key attrs depend only on key)
- BCNF: Every determinant is a candidate key

Index Strategy:
- Primary Key: Unique index, required
- Foreign Key: Index for referential integrity performance
- Filtering: Index columns used in WHERE clauses
- Ordering: Index columns used in ORDER BY
- Covering: Composite index covering full query
- Selective: Indexes on high-cardinality columns

Query Optimization:
- Use EXPLAIN to understand execution plans
- Ensure selective WHERE clauses use indexes
- Avoid OR conditions in WHERE (use UNION instead)
- Push down filters and aggregations to database
- Use appropriate JOIN types (INNER, LEFT, etc.)
- Window functions for analytical queries

Scaling Strategy:
- Vertical: More powerful hardware (limited)
- Horizontal: Read replicas, connection pooling
- Sharding: Partition by key when 100GB+ tables
- Caching: Redis for hot queries
- CQRS: Separate read/write models if needed

Output Requirements:
1. Data modeling report (markdown) with:
   - Normalization assessment (current level achieved)
   - Index analysis and recommendations
   - Performance benchmarks and projections
   - Data integrity validation results
   - Scalability assessment
2. Optimized schema:
   - Enhanced table definitions
   - Recommended indexes
   - Denormalization recommendations
   - Migration path
3. Access patterns:
   - Common query patterns identified
   - Recommended indexes per pattern
   - Expected performance
   - Caching opportunities
4. Performance targets:
   - Query benchmarks
   - Index strategy
   - Scaling plan

Example Schema Review:
Input table:
{
  "Users": {
    "columns": {
      "id": {"type": "UUID", "primary_key": true},
      "email": {"type": "VARCHAR"},
      "name": {"type": "VARCHAR"},
      "country": {"type": "VARCHAR"}
    },
    "constraints": []
  },
  "Orders": {
    "columns": {
      "id": {"type": "UUID", "primary_key": true},
      "user_id": {"type": "UUID"},
      "amount": {"type": "DECIMAL"},
      "created_at": {"type": "TIMESTAMP"}
    },
    "constraints": []
  }
}

Findings might include:
1. No foreign key constraint (Orders.user_id → Users.id)
2. No index on Orders.user_id (FKs should be indexed)
3. No index on Orders.created_at (common filter)
4. No unique constraint on Users.email
5. No composite index on (user_id, created_at) for recent orders query
6. Missing created_at index on Users for analytics

Recommendations:
- Add FK constraint with ON DELETE CASCADE
- Add indexes: user_id, created_at, (user_id, created_at DESC)
- Add unique constraint on email
- Consider materialized view for user_order_count
- Add soft-delete column (is_active) if needed for audit

Remember: Great data modeling is the foundation of scalable, performant systems.
Focus on normalization, proper constraints, and strategic indexing.
```

---

## When to Invoke This Agent

### Complexity Thresholds

| Complexity | Threshold | Invocation Logic |
|-----------|-----------|------------------|
| Low (1-50) | N/A | ❌ Not invoked |
| Medium (51-65) | 65 | ❌ Not invoked |
| Medium-High (66-80) | ≥65 | ✅ Invoked if data-heavy |
| High (81-95) | ≥65 | ✅ Always invoked |
| Very High (96-100) | ≥65 | ✅ Always invoked |

### Invocation Conditions

The Data Modeler Agent is triggered when:

1. **Complexity score ≥ 65** AND
2. **At least one factor present:**
   - "database" or "databases" in requirements
   - "data" or "data-heavy" in requirements
   - "complex" in requirements or architecture
   - "analytics" or "reporting" mentioned
   - 5+ tables in database_schema
   - Complex relationships detected

3. **Optional: Boost triggers:**
   - Scale requirements (millions of records)
   - Real-time analytics needed
   - Data consistency critical
   - GDPR/compliance requirements

### Decision Logic (Pseudo-code)

```python
def should_invoke_data_modeler(state: AgentState) -> bool:
    """Determine if Data Modeler should run."""

    # Check complexity threshold
    if not state.complexity_score or state.complexity_score < 65:
        return False

    # Check for data-related factors
    data_factors = ["database", "data", "complex", "analytics", "schema"]
    combined_text = (
        state.requirements +
        state.architecture_doc +
        str(state.artifacts)
    ).lower()

    has_data_factor = any(factor in combined_text for factor in data_factors)
    if not has_data_factor:
        return False

    # Check if database_schema exists and is substantial
    if not state.artifacts or "database_schema" not in state.artifacts:
        return False

    schema = state.artifacts["database_schema"]
    if not schema or "tables" not in schema:
        return False

    tables = schema["tables"]
    if not tables or len(tables) < 5:
        return False

    # All checks passed
    return True
```

---

## Workflow Integration

### Prerequisites

**Must be completed before Data Modeler runs:**
- Architecture Agent has completed successfully
- `artifacts["database_schema"]` is populated with table definitions
- At least 5 tables specified
- Complexity score ≥ 65

**State Requirements:**
```python
AgentState(
    complexity_score=70,
    artifacts={
        "database_schema": {
            "tables": {
                "users": {...},
                "orders": {...},
                "products": {...},
                "order_items": {...},
                "reviews": {...},
                ...
            }
        }
    },
    architecture_doc="<architecture including data design>"
)
```

### Triggers

The Data Modeler Agent is triggered when:
1. Architecture Agent completes with complexity ≥ 65 and data factors detected
2. Orchestrator selector identifies Data Modeler as applicable specialist
3. `current_phase == "design"` OR `current_phase == "architecture"`

### Execution Context

The Data Modeler is executed:
- **When:** After Architecture Agent, before Backend Agent
- **Why:** To optimize data layer before implementation
- **Cost:** 1 API call (LLM) per project
- **Duration:** ~1-2 minutes

### Output Routing

After Data Modeler completes:

**Success Path:**
```
Data Modeler
     ↓
  Backend Agent (next_agent = "backend")
```

**With Critical Issues:**
```
Data Modeler
     ↓
  Human Review (requires_human_approval = true)
```

---

## Integration Examples

### Example 1: Simple Blog Database (Not Triggered)

**Input Scenario:**
- Project: Simple blog
- Complexity: 50
- Tables: 3 (posts, comments, users)
- Result: Data Modeler NOT invoked (complexity < 65)

### Example 2: E-commerce Platform (Triggered)

**Input Scenario:**
- Project: E-commerce platform
- Complexity: 78
- Tables: 12 (users, products, orders, payments, reviews, etc.)
- Factors: ["database", "complex", "analytics"]

**Sample Schema Issues Found:**
```
NORMALIZATION ISSUES (3):
1. Table: OrderItem has repeated columns
   Problem: item_name, item_price duplicated from Products
   Cause: Data insertion inefficiency
   Fix: Use FK reference, join on query
   Impact: Reduces schema, ensures consistency

2. Table: UserProfile violates transitive dependency
   Problem: city, state, country in UserProfile (address_id present)
   Cause: Should be in Address table, referenced
   Fix: Extract to Address table
   Impact: Single source of truth for addresses

3. Table: ProductReview has address_id
   Problem: Should not be in ProductReview
   Fix: Remove, use user.address instead
   Impact: Cleaner schema, less redundancy

INDEX RECOMMENDATIONS (7):
1. ✅ CREATE INDEX idx_orders_user_id ON orders(user_id);
   Reason: List user's orders (FK index)
   Expected gain: 100x faster

2. ✅ CREATE INDEX idx_orders_created_at ON orders(created_at DESC);
   Reason: Recent orders query
   Expected gain: 50x faster

3. ✅ CREATE INDEX idx_orders_status ON orders(status)
       WHERE status != 'completed';
   Reason: Pending orders query
   Expected gain: Filter optimization

4. ✅ CREATE INDEX idx_products_category ON products(category_id, name);
   Reason: Browse by category
   Expected gain: Covers query (no table lookup)

5. ✅ CREATE INDEX idx_reviews_product ON reviews(product_id, rating DESC);
   Reason: Top reviews for product page
   Expected gain: Materialization

6. ✅ CREATE INDEX idx_inventory_low ON inventory(product_id)
       WHERE quantity < 10;
   Reason: Low stock alerts
   Expected gain: Quick discovery

7. ✅ CREATE INDEX idx_payments_status ON payments(status, created_at);
   Reason: Payment processing/reconciliation
   Expected gain: Filtering + ordering

DENORMALIZATION OPPORTUNITIES (2):
1. Cache product rating on products table
   Current: SELECT AVG(rating) FROM reviews WHERE product_id = ?
   Problem: Expensive aggregation for every product detail page
   Solution: Add rating_avg, rating_count to products table
   Benefit: Product page loads 100x faster
   Cost: Update on every new review
   Recommendation: ✅ IMPLEMENT with trigger-based update

2. Cache user order count on users table
   Current: SELECT COUNT(*) FROM orders WHERE user_id = ?
   Problem: Slow on users with many orders
   Solution: Add order_count to users table
   Benefit: User profile loads 50x faster
   Cost: Update on order create/delete
   Recommendation: ✅ IMPLEMENT with trigger-based update

DATA INTEGRITY ISSUES (4):
1. CRITICAL: orders.user_id has no FK constraint
   Risk: Orphaned orders if user deleted
   Fix: ALTER TABLE orders ADD CONSTRAINT fk_user_id
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE

2. CRITICAL: payments.order_id has no FK constraint
   Risk: Payments for non-existent orders
   Fix: ALTER TABLE payments ADD CONSTRAINT fk_order_id
        FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE

3. WARNING: order_items.product_id has no constraint
   Risk: Items reference deleted products
   Fix: Add FK, use ON DELETE RESTRICT (don't allow delete)

4. WARNING: reviews.user_id has no unique constraint
   Risk: Multiple reviews per user per product
   Fix: ADD UNIQUE(user_id, product_id) to prevent duplicates

SCALABILITY ASSESSMENT:
Current State:
- Orders table: 10M rows (10GB with indexes)
- Products table: 100K rows
- User base: 1M users

Projections (2 years):
- Orders: 100M rows (100GB) - Manageable
- Users: 10M - Manageable
- Reviews: 100M rows - Need optimization

Concerns Identified:
1. Orders table approaching 100GB - Add read replicas
2. Reviews aggregation expensive - Consider materialized view
3. User_id sharding may be needed at 100M+ orders

Recommendations:
1. Implement connection pooling (PgBouncer) - immediate
2. Add 2 read replicas - 6 months
3. Denormalize rating aggregates - immediate
4. Create materialized view for product_stats - 3 months
5. Plan sharding by user_id - 12 months
```

**Enhanced Schema Output:**
```python
artifacts["optimized_schema"] = {
    "tables": {
        "users": {
            "columns": {...},
            "indexes": [
                "CREATE INDEX idx_users_email ON users(email) UNIQUE",
                "CREATE INDEX idx_users_created_at ON users(created_at)"
            ],
            "constraints": [
                "PRIMARY KEY (id)",
                "UNIQUE (email)",
                "CHECK (age >= 18 OR age IS NULL)"
            ]
        },
        "orders": {
            "columns": {
                ...existing...,
                "rating_avg": {
                    "type": "DECIMAL(3,2)",
                    "nullable": true,
                    "description": "Denormalized for performance"
                }
            },
            "indexes": [
                "CREATE INDEX idx_orders_user_created ON orders(user_id, created_at DESC)",
                "CREATE INDEX idx_orders_status ON orders(status) WHERE status != 'completed'",
                "CREATE INDEX idx_orders_payment_status ON orders(payment_status)"
            ],
            "constraints": [
                "PRIMARY KEY (id)",
                "FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE",
                "FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT",
                "CHECK (total_amount > 0)"
            ]
        },
        ...
    },
    "views": {
        "product_stats": {
            "type": "materialized",
            "query": "SELECT product_id, COUNT(*) as review_count, AVG(rating) as avg_rating FROM reviews GROUP BY product_id",
            "refresh_interval": "1 hour",
            "indexes": ["product_id"]
        }
    },
    "partitioning_strategy": {
        "orders": {
            "type": "range",
            "column": "created_at",
            "interval": "1 month",
            "reason": "Large table, queries typically filtered by date range"
        }
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
        "errors": ["No database schema found in artifacts"],
        "message": "Cannot model data without database_schema",
        "next_agent": "architecture"
    }
```

### Recovery Strategies

1. **Insufficient Tables**: Defer to Backend if < 5 tables
2. **Invalid Schema**: Request clarification from Architecture Agent
3. **Missing Constraints**: Continue with optimization analysis
4. **LLM Timeout**: Analyze subset of critical tables

---

## Tools and Capabilities

### Available Tools

| Tool | Purpose | Usage |
|------|---------|-------|
| `schema_analyzer` | Analyze table structure | Check normalization |
| `query_optimizer` | Analyze query plans | Recommend indexes |
| `denormalization_calculator` | Estimate denormalization benefit | Cost-benefit analysis |
| `scaling_projector` | Project growth impact | Plan for scale |

### Permissions

- ✅ Read: `artifacts`, `architecture_doc`, `requirements`, `messages`
- ✅ Write: `data_modeling_report`, `optimized_schema`, `artifacts`
- ✅ Modify: `database_schema` (enhance with recommendations)
- ❌ Code execution: Not required
- ❌ External API calls: Not required

---

## Success Criteria

The Data Modeler Agent has succeeded when:

1. ✅ All tables reviewed for normalization compliance
2. ✅ Indexes analyzed and recommendations provided
3. ✅ Query patterns identified and optimized
4. ✅ Data integrity constraints documented
5. ✅ Scalability assessment completed
6. ✅ Denormalization opportunities identified
7. ✅ Detailed modeling report generated
8. ✅ Optimized schema provided to Backend Agent

**Metrics:**
- Tables analyzed: 100% of input tables
- Normalization issues found: All critical + warnings
- Index recommendations: Complete
- Query patterns: All major patterns identified
- Report completeness: All sections present

---

## Phase Integration

**Belongs to:** Phase 4 - Optional Specialist Agents
**Invoked by:** Complexity-based Specialist Agent Selector
**Supports:** Backend Development Agent (consumes optimized schema)

**Timeline:**
- After: Architecture Design Agent
- Before: Backend Development Agent
- Parallel: Contract Validator, Component Designer (all after Architecture)

---

## References and External Links

- [Database Normalization](https://www.oracle.com/database/what-is-database-normalization/)
- [PostgreSQL Index Documentation](https://www.postgresql.org/docs/current/indexes.html)
- [Database Scaling Strategies](https://www.postgresql.org/docs/current/runtime-config-resource.html)
- [ACID Properties](https://en.wikipedia.org/wiki/ACID)
- [Query Optimization Guide](https://use-the-index-luke.com/)
- [Denormalization Trade-offs](https://en.wikipedia.org/wiki/Denormalization)

---

**Last Updated:** 2026-03-06
**Status:** Phase 4 - Optional Specialist
**Version:** 1.0
