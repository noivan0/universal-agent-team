# Performance Reviewer Agent Specification

## Overview

The Performance Reviewer Agent is an optional specialist agent that reviews system architecture for performance optimization opportunities, identifying bottlenecks, and recommending scaling strategies. It focuses on response times, throughput, resource utilization, and end-user experience metrics, particularly important for high-load, real-time, or latency-sensitive systems.

**Agent Type:** Optional Specialist (Phase 4+)
**Invocation Trigger:** Complexity score ≥ 70 + ("real-time" OR "high-load" OR "scalable" OR "performance" in factors)
**Typical Invocation:** After Architecture Agent, before Development Agents

---

## Role and Responsibilities

### Primary Responsibility

Review system architecture for performance, identifying bottlenecks and recommending optimization strategies across frontend, backend, database, and infrastructure layers.

### Secondary Responsibilities

- Analyze frontend performance (Core Web Vitals, bundle size)
- Review backend performance (API response times, throughput)
- Assess database performance (query patterns, indexing)
- Identify caching opportunities
- Plan load testing strategy
- Design auto-scaling policies
- Optimize network and CDN usage
- Profile and optimize critical paths
- Plan capacity planning
- Review monitoring and alerting

### What This Agent Does NOT Do

- ❌ Implement optimizations (Development Agents' role)
- ❌ Run load tests (QA Agent's role)
- ❌ Design system architecture (Architecture Agent's role)
- ❌ Write performance tests (QA Agent's role)
- ❌ Configure infrastructure (DevOps role)
- ❌ Make business decisions

---

## Input Requirements

### Required Inputs

From `AgentState`:

| Field | Type | Description |
|-------|------|-------------|
| `artifacts` | `dict[str, Any]` | Architecture artifacts with system design |
| `architecture_doc` | `str` | Architecture document with tech stack decisions |
| `requirements` | `str` | Project requirements, especially performance needs |

**Required Context:**
```python
artifacts["api_specs"] or artifacts["component_specs"]  # To analyze
artifacts["database_schema"]                            # For query analysis
```

### Optional Inputs

| Field | Type | Description |
|-------|------|-------------|
| `performance_requirements` | `dict` | Target response times, throughput, SLAs |
| `traffic_estimates` | `dict` | Expected user counts, request rates |
| `infrastructure_budget` | `dict` | Budget constraints |
| `monitoring_tools` | `list[str]` | Available monitoring solutions |

**Optional Context:**
```python
{
    "expected_users": 1000000,
    "peak_rps": 10000,              # requests per second
    "latency_target_p99": "200ms",  # 99th percentile
    "uptime_target": "99.99%",
    "real_time_required": true,
    "analytics_heavy": true,
    "batch_processing_enabled": true,
    "cdn_budget": "available",
    "cache_infrastructure": "available"
}
```

### Validation Rules

```python
def validate_input(self, state: AgentState) -> bool:
    """
    Validate that state contains architecture for performance review.

    Returns:
        True if architecture exists for analysis, False otherwise
    """
    # Check architecture exists
    if not state.artifacts or not state.architecture_doc:
        self.logger.error("Architecture required for performance review")
        return False

    # Performance review can proceed with just architecture
    return True
```

---

## Output Specifications

### Primary Outputs

The Performance Reviewer Agent returns a dictionary with these fields:

| Field | Type | Description |
|-------|------|-------------|
| `performance_review_report` | `str` | Markdown report with findings |
| `optimization_recommendations` | `list[dict]` | Specific performance improvements |
| `bottleneck_analysis` | `dict` | Identified bottlenecks and impact |
| `scaling_strategy` | `dict` | Horizontal/vertical scaling approach |
| `capacity_plan` | `dict` | Infrastructure sizing and growth |
| `monitoring_strategy` | `dict` | Metrics and alerting recommendations |
| `message` | `str` | Summary of performance review |

### Artifacts

The Performance Reviewer Agent produces detailed performance artifacts:

```python
artifacts = {
    "performance_review": {
        "review_timestamp": str,
        "critical_bottlenecks": int,
        "optimization_opportunities": int,
        "estimated_improvement_factor": float,
        "performance_score": float,  # 0-100, higher is better
        "sla_compliance_risk": "low|medium|high"
    },

    "detailed_findings": {
        "frontend_issues": [
            {
                "issue": str,
                "impact": str,
                "root_cause": str,
                "optimization": str,
                "estimated_improvement": str,
                "implementation_effort": "low|medium|high"
            }
        ],
        "backend_bottlenecks": [
            {
                "endpoint": str,
                "issue": str,
                "current_latency": str,
                "target_latency": str,
                "root_cause": str,
                "optimization": str
            }
        ],
        "database_issues": [
            {
                "issue": str,
                "affected_queries": list[str],
                "impact": str,
                "optimization": str
            }
        ],
        "caching_opportunities": [
            {
                "cache_type": "http|database|application|cdn",
                "what_to_cache": str,
                "estimated_hit_rate": float,
                "benefit": str,
                "ttl": str
            }
        ],
        "infrastructure_concerns": [
            {
                "concern": str,
                "risk": str,
                "mitigation": str
            }
        ]
    },

    "performance_targets": {
        "frontend": {
            "core_web_vitals": {
                "lcp": "2.5 seconds",  # Largest Contentful Paint
                "fid": "100ms",        # First Input Delay
                "cls": "0.1"           # Cumulative Layout Shift
            },
            "bundle_size": str,
            "time_to_interactive": str
        },
        "backend": {
            "api_response_time_p50": str,
            "api_response_time_p99": str,
            "throughput_rps": int,
            "error_rate": float
        },
        "database": {
            "query_latency_p99": str,
            "connection_pool_size": int,
            "slow_query_threshold": str
        }
    },

    "scaling_strategy": {
        "horizontal_scaling": {
            "enabled": bool,
            "auto_scale_trigger": str,
            "min_instances": int,
            "max_instances": int,
            "metric": "cpu|memory|rps|custom"
        },
        "vertical_scaling": {
            "initial_size": str,
            "growth_plan": list[dict]
        },
        "database_scaling": {
            "read_replicas": int,
            "connection_pooling": bool,
            "caching_layer": str
        },
        "cost_optimization": {
            "reserved_capacity": float,
            "spot_instances": bool,
            "cdn_usage": bool
        }
    },

    "capacity_planning": {
        "current_capacity": {
            "requests_per_second": int,
            "concurrent_users": int,
            "data_volume_gb": float
        },
        "projected_growth": [
            {
                "timeframe": "3 months|6 months|1 year",
                "requests_per_second": int,
                "users": int,
                "data_volume_gb": float
            }
        ],
        "infrastructure_roadmap": list[str]
    },

    "monitoring_and_alerting": {
        "metrics_to_track": {
            "frontend": list[str],
            "backend": list[str],
            "database": list[str],
            "infrastructure": list[str]
        },
        "alerting_thresholds": {
            "p99_latency": str,
            "error_rate": float,
            "cpu_utilization": float,
            "memory_utilization": float
        },
        "tools_recommended": list[str]
    }
}
```

### State Updates

Fields modified in `AgentState`:

```python
{
    "performance_review_report": "<performance report markdown>",
    "artifacts": {
        ...existing artifacts...,
        "performance_review": {...},
        "performance_targets": {...},
        "scaling_strategy": {...}
    },
    "messages": [..., AgentMessage(agent_id="performance_001", artifacts={...})],
    "current_phase": "performance_review",
    "next_agent": "backend"
}
```

---

## Performance Review Checks

### Frontend Performance Analysis

**Checks Performed:**
1. Core Web Vitals (LCP, FID, CLS)
2. Bundle size and code splitting
3. Time to Interactive (TTI)
4. Asset optimization (images, fonts)
5. CSS and JavaScript efficiency
6. Rendering performance
7. Third-party script impact

**Core Web Vitals:**

| Metric | Target | Poor | Good |
|--------|--------|------|------|
| LCP (Largest Contentful Paint) | < 2.5s | > 4s | ≤ 2.5s |
| FID (First Input Delay) | < 100ms | > 300ms | ≤ 100ms |
| CLS (Cumulative Layout Shift) | < 0.1 | > 0.25 | ≤ 0.1 |

**Example Issues:**

```
Frontend Performance Issue (CRITICAL):
  Issue: Large JavaScript bundle
  Current: 500KB uncompressed for app.js
  Impact: 3+ seconds for bundle download on 4G
  Root Cause: No code splitting, importing entire library
  Optimization:
    1. Implement route-based code splitting (React.lazy)
    2. Split vendor bundles (React, deps separate)
    3. Remove unused dependencies
  Expected Improvement: 500KB → 150KB, 50x faster load
  Implementation: 1-2 days

Frontend Performance Issue (HIGH):
  Issue: Unoptimized images
  Current: Full-resolution images (2MB each)
  Impact: Slow page load, high bandwidth
  Optimization:
    1. Use WebP format with fallbacks
    2. Create responsive images (srcset)
    3. Lazy load images below fold
    4. Use image CDN (Cloudinary, imgix)
  Expected Improvement: 2MB → 100KB per image, 20x faster
  Implementation: 1 week

Frontend Performance Issue (MEDIUM):
  Issue: Synchronous third-party scripts
  Current: <script src="analytics.js"></script> blocks rendering
  Impact: 500ms+ delay if analytics slow
  Optimization: Load asynchronously
  Implementation: <script async src="..."></script>
  Expected Improvement: Eliminates analytics blocking
  Implementation: 1 day

Performance Opportunity (QUICK WIN):
  Issue: Missing gzip compression
  Current: Serving uncompressed assets
  Impact: 3x larger file size
  Fix: Enable gzip in web server
  Expected Improvement: 500KB → 150KB (70% reduction)
  Implementation: 1 hour
```

### Backend Performance Analysis

**Checks Performed:**
1. API endpoint response times
2. Database query efficiency
3. Connection pool sizing
4. Caching strategy
5. Async operation handling
6. Batch processing opportunities
7. Resource utilization (CPU, memory)

**Example Issues:**

```
Backend Performance Issue (CRITICAL):
  Endpoint: GET /api/v1/users/{id}/orders
  Current Latency: 500ms
  Target Latency: 100ms
  Root Cause: N+1 query problem
  Current Query:
    SELECT * FROM users WHERE id = ?
    FOR EACH ORDER:
      SELECT * FROM orders WHERE user_id = ?
  Issue: 1 user query + N order queries (slow)
  Optimization:
    SELECT u.*, o.* FROM users u
    LEFT JOIN orders o ON u.id = o.user_id
    WHERE u.id = ?
  Expected Improvement: 500ms → 50ms (10x faster)
  Implementation: 1 day

Backend Performance Issue (HIGH):
  Endpoint: POST /api/v1/send-email
  Current Latency: 3000ms (blocking)
  Problem: Waits for email service to complete
  Impact: User waits 3 seconds for response
  Optimization: Queue email job, return immediately
    1. Add job to Redis queue
    2. Return 202 Accepted immediately
    3. Background worker sends email
  Expected Improvement: 3000ms → 50ms (60x faster)
  Implementation: 1 week

Backend Performance Issue (MEDIUM):
  Issue: No connection pooling
  Current: Creating new DB connection per request
  Impact: Connection overhead, limited concurrency
  Optimization: Use connection pool (PgBouncer, HikariCP)
  Expected Improvement:
    - Fewer failed connections
    - 2-3x more concurrent capacity
    - Reduced memory per request
  Implementation: 1-2 days

Database Performance Issue (HIGH):
  Table: Orders (100M rows)
  Issue: Slow list query (5 seconds)
  Query: SELECT * FROM orders WHERE created_at > ? ORDER BY created_at DESC
  Root Cause: No index on created_at
  Fix: CREATE INDEX idx_orders_created_at ON orders(created_at DESC)
  Expected Improvement: 5000ms → 100ms (50x faster)
  Index Cost: 50GB storage (acceptable)
  Implementation: 1 day
```

### Caching Strategy Analysis

**Cache Types:**

| Type | Use Case | TTL | Hit Rate |
|------|----------|-----|----------|
| HTTP/CDN | Static assets, API responses | 24 hours | 80-90% |
| Database | Expensive queries | 1 hour | 70-80% |
| Application | API calls, computed data | 5-60 min | 60-70% |
| Full-page | Static pages | 1 hour+ | 90%+ |

**Example Caching Opportunities:**

```
Caching Opportunity #1: Product List
Query: SELECT * FROM products WHERE category = ?
Current Latency: 500ms (DB query)
Cache Strategy: Redis with 1-hour TTL
  Key: product_list:{category}
  Hit Rate: ~90% (popular categories)
  Benefit: 500ms → 5ms (100x faster)
  Invalidation: On product create/update

Caching Opportunity #2: User Session
Current: 3 DB queries per request
Session Cache: Redis session store
  Store: user_id → {user_data}
  TTL: 24 hours (or session duration)
  Benefit: 300ms → 5ms database time
  Implementation: Use libraries like express-session

Caching Opportunity #3: Static Content
Current: 50 requests/sec for same CSS/JS
Strategy: CloudFront CDN
  Cache static assets at edge
  TTL: 1 year (with fingerprinting)
  Benefit: 90% requests cached at edge, not origin
  Cost: Low (cloudfront tier pricing)

Full-Page Caching (Blog Example):
Path: GET /blog/posts/{id}
Current: 5 queries, 100ms generation
Cache Strategy: Redis full-page cache
  TTL: 1 hour (or manual invalidation)
  Hit Rate: 90%+
  Benefit: 100ms → 5ms (20x faster)
  Trade-off: Manual invalidation on post update
```

### Scalability Assessment

**Scaling Dimensions:**

| Dimension | Strategy | Cost |
|-----------|----------|------|
| Compute | Horizontal (more servers) | Medium |
| Database | Read replicas + caching | Medium |
| Storage | Sharding, archival | Medium-High |
| Network | CDN, edge locations | Low-Medium |

**Example Assessment:**

```
Current Capacity Analysis:
- Single server: 100 requests/sec
- Expected peak: 10,000 requests/sec
- Gap: 100x scale required

Scaling Strategy:
1. Horizontal scaling (compute)
   - Load balancer + 10+ servers
   - Cost: ~$1000/month
   - Capacity: 1000+ RPS

2. Database scaling
   - Read replicas (3 for HA)
   - Redis cache (2 instances for HA)
   - Cost: ~$500/month
   - Capacity: 5000+ RPS with cache

3. CDN for static assets
   - CloudFront or Cloudflare
   - Cost: Low (pay per GB)
   - Benefit: 90% cache hit rate

4. Database optimization
   - Indexes, query optimization
   - Caching strategies
   - Cost: Minimal
   - Benefit: 10-50x faster queries

Projected Capacity:
- Optimized single server: 500 RPS (10x baseline)
- With 2 app servers + cache: 5000 RPS
- With 5+ servers + cache: 10,000+ RPS

Cost: ~$1500/month for target capacity
Timeline: 2-3 months for full optimization
```

### Load Testing Strategy

**Load Test Types:**

| Type | Purpose | Example |
|------|---------|---------|
| Baseline | Establish current performance | 1000 concurrent users |
| Ramp | Gradual increase | 1000→10000 users over 10min |
| Spike | Sudden spike | 1000→50000 users instantly |
| Stress | Until failure | Keep increasing until fails |
| Soak | Long duration | 1000 users for 24 hours |

**Example Load Testing Plan:**

```
Load Testing Roadmap:
1. Baseline Test (Week 1)
   - 100 concurrent users
   - Measure: P50, P95, P99 latencies
   - Baseline: ~100ms P99
   - Establish performance baseline

2. Ramp Test (Week 1)
   - Increase from 100 to 1000 concurrent users over 10 min
   - Identify scaling bottleneck
   - Expected: latency increases to 500ms at 1000 users

3. Spike Test (Week 2)
   - Sudden jump to 5000 concurrent users
   - Test auto-scaling response
   - Expected: Recovery in < 60 seconds

4. Soak Test (Week 3)
   - 1000 concurrent users for 24 hours
   - Identify memory leaks
   - Monitor for: Connection leaks, memory growth

5. Optimization + Retest (Week 4)
   - Apply optimizations (caching, indexing)
   - Re-run baseline
   - Target: 200 concurrent users at P99 < 100ms

Tools: Apache JMeter, Locust, K6, or cloud solutions (LoadRunner)
```

---

## LLM Configuration

### Model

```python
{
    "provider": "anthropic",
    "model": "claude-3-5-sonnet-20241022",
    "temperature": 0.15,
    "max_tokens": 7500,
    "timeout": 150
}
```

### Rationale

- **Low temperature (0.15)**: Performance analysis requires precision
- **Claude 3.5 Sonnet**: Strong at bottleneck analysis and system optimization
- **7500 tokens**: Sufficient for detailed performance analysis
- **150s timeout**: Performance analysis is technical; standard time

---

## System Prompt

```
You are a senior performance engineer and systems architect with deep knowledge of
application performance, scalability, caching strategies, and load testing.

Your responsibilities:
1. Analyze system architecture for performance bottlenecks
2. Review frontend performance (Core Web Vitals, bundle size)
3. Assess backend performance (API latency, throughput)
4. Identify database query inefficiencies
5. Recommend caching strategies
6. Plan load testing and stress testing
7. Design auto-scaling policies
8. Plan capacity growth
9. Recommend monitoring and alerting

Performance Optimization Hierarchy (prioritize in this order):
1. Eliminate work: Don't do unnecessary operations
2. Cache results: Avoid re-computing
3. Optimize algorithms: Better complexity
4. Scale resources: Add more capacity
5. Parallelize: Async, threading
6. Distribute: Sharding, replicas

Frontend Performance Best Practices:
- Core Web Vitals: LCP < 2.5s, FID < 100ms, CLS < 0.1
- Code splitting: Route-based, vendor bundles
- Image optimization: WebP, responsive images, lazy loading
- CSS/JS optimization: Minification, unused code removal
- Critical path rendering: Above-fold content first
- Third-party script management: Async, deferred loading
- Monitoring: Real-user monitoring (RUM), synthetic monitoring

Backend Performance Best Practices:
- Connection pooling: Reduce connection overhead
- Query optimization: Proper indexes, avoid N+1
- Caching strategy: Redis, memcached, application level
- Async operations: Don't block on I/O
- Batch processing: Group operations
- Resource pooling: Thread pools, connection pools
- Profiling: Identify actual bottlenecks
- Monitoring: Response time, throughput, error rate

Database Optimization:
- Indexing: Create indexes on filtered columns
- Query optimization: Use EXPLAIN to understand
- Connection pooling: Limit connections per app
- Read replicas: Scale reads separately from writes
- Caching: Cache expensive queries
- Denormalization: Trade storage for query speed
- Partitioning: Divide large tables
- Monitoring: Track slow queries

Caching Strategy:
- HTTP/CDN: Static assets, API responses
- Database: Query result caching
- Application: Object caching, computed results
- Full-page: Static pages, cacheable content
- Cache keys: Include version, user ID, locale
- TTL strategy: Short (5min) for volatile, long (24h) for static
- Invalidation: Proactive (TTL) or reactive (events)
- Hit rate: Track and optimize (target 70-90%)

Scaling Strategy:
- Horizontal: More servers (load balancing)
- Vertical: Bigger servers (limited by cost)
- Database: Read replicas, write sharding
- Async: Job queues, background workers
- Cache: Reduce database load
- CDN: Distribute static content
- Microservices: Scale independent services

Load Testing:
- Baseline: Current performance
- Ramp: Gradual increase (identify bottleneck)
- Spike: Sudden increase (test auto-scaling)
- Stress: Until failure (capacity limits)
- Soak: Long duration (memory leaks)
- Goals: Measure latency, throughput, errors

Output Requirements:
1. Performance review report (markdown) with:
   - Executive summary of performance gaps
   - Frontend performance analysis
   - Backend bottleneck identification
   - Database performance assessment
   - Caching opportunities
   - Scalability risks
2. Optimization recommendations:
   - Specific improvements with impact estimates
   - Priority and effort assessment
   - Implementation order
3. Performance targets:
   - Frontend (Core Web Vitals, bundle size)
   - Backend (latency SLOs, throughput)
   - Database (query latency, connection pool)
4. Scaling and capacity strategy:
   - Current vs projected capacity
   - Infrastructure roadmap
   - Cost estimates
5. Monitoring recommendations:
   - Key metrics to track
   - Alerting thresholds
   - Recommended tools

Example Performance Issue:
System: E-commerce checkout
Current: 2000ms from click to confirmation
Target: 500ms
Analysis:
  1. Frontend (400ms) - shipping calculation JS
  2. API request (100ms) - validation, inventory check
  3. Payment processor (1400ms) - external service
  4. Response rendering (100ms) - render confirmation

Optimizations:
  1. Pre-calculate shipping before checkout (save 400ms)
  2. Parallelize payment + inventory checks (save 300ms)
  3. Show optimistic confirmation (render 50ms, verify async)
  Result: ~50ms perceived latency (40x improvement)

Remember: Most performance issues are in architecture, not code.
Focus on identifying the root causes and recommending systemic improvements.
```

---

## When to Invoke This Agent

### Complexity Thresholds

| Complexity | Threshold | Invocation Logic |
|-----------|-----------|------------------|
| Low (1-50) | N/A | ❌ Not invoked |
| Medium (51-70) | 70 | ❌ Not invoked |
| Medium-High (71-85) | ≥70 | ✅ Invoked if performance-critical |
| High (86-95) | ≥70 | ✅ Always invoked |
| Very High (96-100) | ≥70 | ✅ Always invoked |

### Invocation Conditions

The Performance Reviewer Agent is triggered when:

1. **Complexity score ≥ 70** AND
2. **At least one factor present:**
   - "real-time" or "real time" in requirements
   - "high-load" or "high load" or "high traffic" in requirements
   - "scalable" or "scalability" or "scale" mentioned
   - "performance" explicitly mentioned
   - "latency" requirements specified
   - 100+ expected concurrent users
   - API responses expected < 200ms
   - Analytics/reporting heavy system

3. **Optional: Boost triggers:**
   - Mobile app performance critical
   - Global user base (latency concerns)
   - Real-time data requirements
   - High-frequency analytics
   - Batch processing at scale

### Decision Logic (Pseudo-code)

```python
def should_invoke_performance_reviewer(state: AgentState) -> bool:
    """Determine if Performance Reviewer should run."""

    # Check complexity threshold
    if not state.complexity_score or state.complexity_score < 70:
        return False

    # Check for performance-related factors
    perf_factors = [
        "real-time", "high-load", "high-traffic", "scalable",
        "performance", "latency", "throughput"
    ]
    combined_text = (
        state.requirements +
        state.architecture_doc +
        str(state.artifacts)
    ).lower()

    has_perf_factor = any(factor in combined_text for factor in perf_factors)
    return has_perf_factor
```

---

## Workflow Integration

### Prerequisites

**Must be completed before Performance Reviewer runs:**
- Architecture Agent has completed
- System architecture defined
- Tech stack decisions made
- Complexity score ≥ 70

### Execution Context

The Performance Reviewer is executed:
- **When:** After Architecture Agent, before Development Agents
- **Why:** To identify performance issues early before implementation
- **Cost:** 1 API call (LLM) per project
- **Duration:** ~1-2 minutes

### Output Routing

After Performance Reviewer completes:

**Success Path:**
```
Performance Reviewer
       ↓
  Backend/Frontend Agent
```

**With Critical Issues:**
```
Performance Reviewer
       ↓
  Human Review (if SLA risks)
```

---

## Integration Examples

### Example 1: Simple CRUD App (Not Triggered)

**Input Scenario:**
- Complexity: 45
- 100 expected users
- No real-time requirements
- Result: Performance Reviewer NOT invoked

### Example 2: Real-Time Collaboration App (Triggered)

**Input Scenario:**
- Complexity: 78
- Factors: ["real-time", "high-load", "performance"]
- Expected: 50,000 concurrent users
- Latency target: < 100ms

**Performance Findings:**

```
PERFORMANCE BOTTLENECKS IDENTIFIED:

1. WebSocket Connection Management (CRITICAL)
   Current: Single connection per user to single server
   Bottleneck: Connection limits per server (~10K)
   Impact: Cannot scale to 50K users
   Solution: Use message queue (Redis Pub/Sub, RabbitMQ)
   Architecture:
     WebSocket server → Redis Pub/Sub → Broadcast to clients
   Expected Capacity: 50K+ concurrent users

2. Database Write Bottleneck (HIGH)
   Current: Every document change written to DB immediately
   Issue: 50K users = 50K potential DB writes/sec
   Bottleneck: Database can't handle that throughput
   Solution: Use write-ahead log + batch writes
   Implementation:
     1. Write to Redis log (fast)
     2. Batch writes to DB every 100ms
     3. Sync to DB in background
   Expected Improvement: 50x throughput increase

3. Client-Side Performance (MEDIUM)
   Current: Full collaboration state loaded at startup
   Issue: 50MB state object, takes 10 seconds to load
   Bottleneck: Initial load + memory
   Solution:
     1. Lazy load collaboration features
     2. Stream state incrementally
     3. Virtual scrolling for large documents
   Expected Improvement: 10s → 1s initial load

4. Network Latency (MEDIUM)
   Current: All traffic routed through single region
   Issue: Users in Australia get 300ms latency
   Solution: Use global CDN + regional servers
   Implementation:
     1. CloudFlare or AWS CloudFront for static assets
     2. Regional WebSocket servers
     3. Geo-routing to nearest server
   Expected Improvement: 300ms → 50ms for far regions

OPTIMIZATION ROADMAP:

Phase 1 (Week 1-2): Database Optimization
- Implement write-ahead log
- Batch database writes
- Expected improvement: 10x throughput

Phase 2 (Week 2-3): Message Queue
- Deploy Redis or RabbitMQ
- Implement Pub/Sub for broadcasts
- Expected improvement: 100x concurrent users

Phase 3 (Week 3-4): Client Optimization
- Implement lazy loading
- Add virtual scrolling
- Expected improvement: 10x faster startup

Phase 4 (Week 5-6): Global Distribution
- Deploy regional servers
- Implement geo-routing
- Expected improvement: 6x faster latency

PERFORMANCE TARGETS:

Frontend:
- Initial load: 1 second (was 10s, 10x improvement)
- Message delivery: < 50ms p99 (real-time feel)
- Bundle size: < 200KB (was 2MB)

Backend:
- API latency: < 10ms p99 (excluding network)
- WebSocket message latency: < 50ms p99
- Throughput: 50K+ concurrent users

Database:
- Write throughput: 10K writes/sec (batched)
- Query latency: < 5ms p99
- Connection pool: 100 connections (shared across servers)

MONITORING STRATEGY:

Frontend Metrics (RUM):
- LCP: Track time to first document render
- FID: Track collaboration interaction latency
- CLS: Monitor layout shifts during updates
- Custom: Message delivery latency

Backend Metrics:
- WebSocket connection count (p50, p99)
- Message latency (p50, p95, p99)
- Database write latency (p50, p95, p99)
- CPU/memory utilization

Alerting Thresholds:
- WebSocket latency > 200ms p99 → Page
- Message queue depth > 10K → Page
- DB write latency > 100ms → Warning
- CPU > 80% → Scale up
- Memory > 85% → Investigate leak

Tools:
- Datadog or New Relic for infrastructure
- Sentry for error tracking
- Custom metrics via StatsD
- CloudWatch for AWS infrastructure
```

**Scaling Strategy Output:**

```python
artifacts["scaling_strategy"] = {
    "horizontal_scaling": {
        "enabled": True,
        "auto_scale_trigger": "WebSocket connection count",
        "min_instances": 3,
        "max_instances": 50,
        "scale_up_threshold": "8000 connections per instance",
        "scale_down_threshold": "2000 connections per instance"
    },
    "message_queue": {
        "technology": "Redis Pub/Sub or RabbitMQ",
        "purpose": "Fan-out messages to all servers",
        "instances": 3,  # HA setup
        "capacity": "50K messages/sec"
    },
    "database_scaling": {
        "read_replicas": 3,
        "write_optimization": "Batched writes via queue",
        "connection_pooling": True,
        "max_connections": 100
    },
    "cache_strategy": {
        "user_state": "Redis (1 hour TTL)",
        "document_meta": "Redis (10 min TTL)",
        "cdn": "CloudFlare for static assets"
    },
    "load_testing": {
        "baseline": "1000 concurrent users",
        "ramp": "1000 → 50000 over 10 minutes",
        "spike": "Sudden jump to 30000 concurrent",
        "soak": "10000 users for 24 hours",
        "stress": "Increase until failure"
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
        "errors": ["Cannot review performance without architecture"],
        "message": "Architecture required for performance analysis",
        "next_agent": "architecture"
    }
```

### Recovery Strategies

1. **Missing Performance Requirements**: Use industry standards
2. **Unclear Architecture**: Work with available information
3. **Complex System**: Focus on critical path
4. **LLM Timeout**: Prioritize top bottlenecks

---

## Tools and Capabilities

### Available Tools

| Tool | Purpose | Usage |
|------|---------|-------|
| `bottleneck_analyzer` | Find performance bottlenecks | Analyze system |
| `cache_advisor` | Recommend caching | Identify opportunities |
| `capacity_calculator` | Project growth | Estimate needs |
| `benchmark_tool` | Compare optimizations | Before/after |

### Permissions

- ✅ Read: `artifacts`, `architecture_doc`, `requirements`
- ✅ Write: `performance_review_report`, `artifacts` (performance_* fields)
- ✅ Modify: None (read-only analysis)
- ❌ Code execution: Not required
- ❌ External API calls: Not required

---

## Success Criteria

The Performance Reviewer Agent has succeeded when:

1. ✅ Frontend performance analyzed
2. ✅ Backend bottlenecks identified
3. ✅ Database issues assessed
4. ✅ Caching opportunities identified
5. ✅ Scaling strategy defined
6. ✅ Capacity planning completed
7. ✅ Monitoring recommendations provided
8. ✅ Detailed report with metrics generated

**Metrics:**
- Bottlenecks identified: All critical + high priority
- Optimization opportunities: Major paths covered
- Scaling plan: Complete with timelines
- Report completeness: All sections present

---

## Phase Integration

**Belongs to:** Phase 4 - Optional Specialist Agents
**Invoked by:** Complexity-based Specialist Agent Selector
**Supports:** Backend/Frontend Development Agents (implement optimizations)

**Timeline:**
- After: Architecture Design Agent
- Before: Backend/Frontend Development Agents
- Parallel: All other specialists

---

## References and External Links

- [Web Vitals](https://web.dev/vitals/)
- [Performance Best Practices](https://developer.chrome.com/docs/lighthouse/performance/)
- [Database Optimization](https://use-the-index-luke.com/)
- [Caching Patterns](https://martinfowler.com/bliki/CacheAsidePattern.html)
- [Load Testing](https://locust.io/)
- [Scalability](https://en.wikipedia.org/wiki/Scalability)
- [Capacity Planning](https://en.wikipedia.org/wiki/Capacity_planning)

---

**Last Updated:** 2026-03-06
**Status:** Phase 4 - Optional Specialist
**Version:** 1.0
