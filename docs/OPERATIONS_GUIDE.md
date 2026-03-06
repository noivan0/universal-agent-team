# Operations & Monitoring Guide - Universal Agent Team

Day-to-day operations, monitoring, and maintenance procedures for production deployments.

## Table of Contents
1. [Daily Operations](#daily-operations)
2. [Monitoring](#monitoring)
3. [Performance Tuning](#performance-tuning)
4. [Backup & Recovery](#backup--recovery)
5. [Incident Response](#incident-response)
6. [Cost Optimization](#cost-optimization)

---

## Daily Operations

### Morning Checklist (5 minutes)

```bash
#!/bin/bash
# daily-checklist.sh

echo "=== Universal Agent Team Daily Checklist ==="

# 1. Pod Health
echo "1. Pod Health:"
kubectl get pods -n universal-agents --no-headers | grep -v Running && echo "⚠️  Non-running pods detected!" || echo "✓ All pods running"

# 2. Error Rate
echo "2. Error Rate:"
curl -s http://localhost:8000/metrics | grep 'http_requests_total{status="5' | head -3
echo "✓ Check error rate in Grafana"

# 3. Response Times
echo "3. Response Times (P95):"
curl -s http://localhost:8000/metrics | grep 'http_request_duration_seconds_bucket.*le="0.1"'
echo "✓ Should be > 95% under 100ms"

# 4. Database
echo "4. Database Connections:"
curl -s http://localhost:8000/metrics | grep 'database_connections_active'

# 5. Memory Usage
echo "5. Memory Usage:"
kubectl top pods -n universal-agents | head -5

echo "=== Checklist Complete ==="
```

### Health Monitoring

```bash
# Overall system health
curl http://localhost:8000/health

# Detailed readiness
curl http://localhost:8000/ready | jq '.'

# Expected output:
{
  "ready": true,
  "checks": {
    "database": "connected",
    "redis": "connected",
    "api": "responding"
  }
}
```

### Common Daily Tasks

#### Check Logs
```bash
# Last 100 lines
kubectl logs -n universal-agents deployment/universal-agents-backend --tail=100

# Follow logs
kubectl logs -f deployment/universal-agents-backend -n universal-agents

# Errors only
kubectl logs deployment/universal-agents-backend -n universal-agents | grep ERROR
```

#### Check Resource Usage
```bash
# Memory
kubectl top pods -n universal-agents --sort-by memory

# CPU
kubectl top pods -n universal-agents --sort-by cpu

# Disk
kubectl exec -n universal-agents <pod-name> -- df -h
```

#### Manage Projects
```bash
# List active projects
curl http://localhost:8000/api/projects?status=in_progress

# Check specific project
curl http://localhost:8000/api/projects/{project_id} | jq '.status, .progress'

# Cancel a project
curl -X POST http://localhost:8000/api/projects/{project_id}/cancel
```

---

## Monitoring

### Prometheus Metrics

Key metrics to monitor:

```
# Request performance
http_request_duration_seconds_bucket  # Latency distribution
http_requests_total                    # Total requests

# Cache performance
cache_hit_rate                        # % of cache hits
cache_size_bytes                      # Memory usage

# Database performance
database_query_duration_seconds       # Query latency
database_connections_active           # Connection pool usage

# Agent performance
agent_execution_time_seconds          # Agent processing time
agent_retry_count                     # Retry attempts

# System health
up                                    # Service up/down
process_resident_memory_bytes         # Process memory
process_cpu_seconds_total             # CPU usage
```

### Grafana Dashboards

#### Create Custom Dashboard

```json
{
  "dashboard": {
    "title": "Universal Agent Team Overview",
    "panels": [
      {
        "title": "API Response Time (P95)",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))"
          }
        ]
      },
      {
        "title": "Error Rate",
        "targets": [
          {
            "expr": "rate(http_requests_total{status=~\"5..\"}[5m])"
          }
        ]
      },
      {
        "title": "Cache Hit Rate",
        "targets": [
          {
            "expr": "cache_hit_rate"
          }
        ]
      }
    ]
  }
}
```

### Alerting Rules

Create alert rules in Prometheus:

```yaml
groups:
- name: universal_agents_alerts
  rules:
  - alert: HighErrorRate
    expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
    for: 5m
    annotations:
      summary: "High error rate detected"

  - alert: DatabaseDown
    expr: up{job="database"} == 0
    for: 1m
    annotations:
      summary: "Database is down"

  - alert: HighMemoryUsage
    expr: (container_memory_usage_bytes / container_spec_memory_limit_bytes) > 0.9
    for: 5m
    annotations:
      summary: "Memory usage above 90%"

  - alert: CacheHitRateDown
    expr: cache_hit_rate < 0.80
    for: 10m
    annotations:
      summary: "Cache hit rate below 80%"
```

---

## Performance Tuning

### Database Optimization

#### Check Slow Queries
```bash
# Enable slow query logging
kubectl exec -n universal-agents <postgres-pod> -- psql -U postgres -d universal_agents -c "
  CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
  SELECT query, calls, mean_exec_time
  FROM pg_stat_statements
  ORDER BY mean_exec_time DESC
  LIMIT 10;
"
```

#### Add Missing Indexes
```bash
# Common indexes to add
kubectl exec -n universal-agents <postgres-pod> -- psql -U postgres -d universal_agents -c "
  CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
  CREATE INDEX IF NOT EXISTS idx_projects_user_id ON projects(user_id);
  CREATE INDEX IF NOT EXISTS idx_agents_project_id ON agents(project_id);
  CREATE INDEX IF NOT EXISTS idx_cache_expiry ON cache_entries(expiry_time);
"
```

### Cache Optimization

#### Monitor Cache Effectiveness
```python
# In your monitoring code
cache_metrics = metrics.collector.cache_metrics

print(f"Cache Hit Rate: {cache_metrics.hit_rate * 100:.1f}%")
print(f"Cache Size: {cache_metrics.size_bytes / 1024 / 1024:.1f}MB")
print(f"Cache Items: {cache_metrics.item_count}")

# If hit rate < 80%, consider:
# 1. Increasing cache size
# 2. Increasing TTL
# 3. Analyzing query patterns
```

#### Tune Cache Settings
```python
# config/settings.py
class ProductionSettings(Settings):
    # Cache configuration
    cache_size_limit = 10000  # Max items
    cache_ttl_seconds = 3600  # 1 hour
    cache_eviction_policy = "lru"  # Least Recently Used

    # For high-traffic scenarios
    redis_pool_size = 20
    redis_max_connections = 30
```

### Redis Optimization

```bash
# Check Redis memory
redis-cli info memory

# Analyze slow operations
redis-cli slowlog get 10

# Check eviction policy
redis-cli config get maxmemory-policy
# Should be: allkeys-lru

# Set eviction policy
redis-cli config set maxmemory-policy allkeys-lru
```

### Connection Pool Tuning

```python
# Monitor pool usage
kubectl exec -n universal-agents <pod> -- python -c "
from sqlalchemy import event, pool

@event.listens_for(pool.Pool, 'connect')
def receive_connect(dbapi_conn, connection_record):
    print(f'Active connections: {pool.size}')
"

# Adjust pool size based on workload
# config/settings.py:
DATABASE_POOL_SIZE = 20         # Default connections
DATABASE_MAX_OVERFLOW = 40      # Max additional connections
DATABASE_POOL_TIMEOUT = 30      # Timeout waiting for connection
```

---

## Backup & Recovery

### Database Backups

#### Automated Daily Backup
```bash
#!/bin/bash
# backup-database.sh

BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/universal_agents_$DATE.sql.gz"

pg_dump \
  --host=$DB_HOST \
  --user=$DB_USER \
  --password=$DB_PASSWORD \
  --database=$DB_NAME \
  | gzip > $BACKUP_FILE

# Verify backup
gunzip -t $BACKUP_FILE && echo "✓ Backup valid"

# Upload to cloud storage
aws s3 cp $BACKUP_FILE s3://backups/

# Keep local copies for 7 days
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete
```

#### Restore from Backup
```bash
# List available backups
aws s3 ls s3://backups/

# Download backup
aws s3 cp s3://backups/universal_agents_20260306_100000.sql.gz /tmp/

# Restore database
gunzip < /tmp/universal_agents_20260306_100000.sql.gz | \
  psql --host=$DB_HOST \
       --user=$DB_USER \
       --password=$DB_PASSWORD \
       --database=$DB_NAME

echo "✓ Restore complete"
```

### Redis Backups

```bash
# Manual snapshot
redis-cli BGSAVE

# Verify backup
ls -lh /var/lib/redis/dump.rdb

# Restore
redis-cli SHUTDOWN
cp /backups/dump.rdb /var/lib/redis/
redis-cli

# In Redis CLI:
> FLUSHDB         # Clear existing data
> BGREWRITEAOF   # Rewrite AOF file
```

### Application State Backup

```bash
# Backup project artifacts
kubectl exec -n universal-agents <pod> -- \
  tar -czf /tmp/artifacts_backup.tar.gz /data/artifacts/

# Download backup
kubectl cp universal-agents/<pod>:/tmp/artifacts_backup.tar.gz \
  ./artifacts_backup.tar.gz
```

---

## Incident Response

### Incident: High Error Rate

**Symptom**: Error rate > 5% for 5+ minutes

```bash
# 1. Check error types
kubectl logs deployment/universal-agents-backend -n universal-agents | grep ERROR | head -20

# 2. Check resource usage
kubectl top pods -n universal-agents

# 3. Check database
kubectl exec postgres-0 -- psql -c "SELECT datname, numbackends FROM pg_stat_database WHERE datname='universal_agents';"

# 4. Immediate actions
# - Scale up deployment: kubectl scale deployment universal-agents-backend --replicas=5
# - Restart pods: kubectl rollout restart deployment/universal-agents-backend
# - Check logs for specific error patterns
```

### Incident: Redis Unavailable

**Symptom**: "Redis unavailable" in logs, fallback cache in use

```bash
# 1. Check Redis health
redis-cli ping

# 2. Check connectivity
kubectl logs deployment/universal-agents-backend | grep redis

# 3. Restart Redis
kubectl rollout restart statefulset/redis -n universal-agents

# 4. Check circuit breaker
curl http://localhost:8000/metrics | grep circuit_breaker_state

# 5. Reset connection pool
kubectl scale deployment universal-agents-backend --replicas=0
kubectl scale deployment universal-agents-backend --replicas=3
```

### Incident: Database Connection Pool Exhausted

**Symptom**: "Cannot acquire connection" errors

```bash
# 1. Check active connections
psql -U postgres -h localhost -c "
  SELECT datname, numbackends FROM pg_stat_database WHERE datname='universal_agents';"

# 2. Check for long-running queries
psql -U postgres -h localhost -c "
  SELECT pid, usename, query, query_start
  FROM pg_stat_activity
  WHERE state = 'active' AND query_start < now() - interval '5 minutes';"

# 3. Kill long-running queries
psql -U postgres -h localhost -c "
  SELECT pg_terminate_backend(pid)
  FROM pg_stat_activity
  WHERE datname = 'universal_agents'
  AND query_start < now() - interval '10 minutes';"

# 4. Increase pool size
# Edit config/settings.py:
# DATABASE_POOL_SIZE = 40  # Increase from default 20
# Restart: kubectl rollout restart deployment/universal-agents-backend
```

### Incident: Memory Leak

**Symptom**: Memory steadily increases over time

```bash
# 1. Check memory trend
kubectl top pod <pod-name> -n universal-agents --containers
# Watch for 15+ minutes to confirm trend

# 2. Check for cache unbounded growth
curl http://localhost:8000/metrics | grep cache_size_bytes

# 3. Identify what's consuming memory
kubectl exec -n universal-agents <pod> -- python -c "
import tracemalloc
import sys
tracemalloc.start()

# Run some operations

current, peak = tracemalloc.get_traced_memory()
print(f'Current: {current / 1024 / 1024:.1f}MB; Peak: {peak / 1024 / 1024:.1f}MB')
"

# 4. Immediate mitigation
# - Reduce cache size: cache_size_limit = 1000  # Reduce from default 10000
# - Reduce connection pool: database_pool_size = 10
# - Restart pod: kubectl delete pod <pod-name> -n universal-agents
```

---

## Cost Optimization

### Analyze API Usage

```bash
# Count API calls per endpoint
curl -s http://localhost:8000/metrics | grep 'http_requests_total' | \
  awk -F'[{}"]' '{print $9, $NF}' | \
  awk '{print $1, $2}' | \
  sort | uniq -c | sort -rn

# Estimate monthly costs
# Claude 3.5 Sonnet: $3 per 1M input tokens, $15 per 1M output tokens
# If using 500K tokens/month: ~$7.50
```

### Optimize Token Usage

```python
# 1. Enable context compression
from context_compaction import ContextCompactor

state = {...}
compressed = ContextCompactor.compress_context(state, next_agent="frontend")

# 2. Reduce token count
# Before: ~500K tokens/month = $15/month
# After: ~150K tokens/month = $4.50/month
# Savings: 70%
```

### Right-size Infrastructure

```bash
# Current: 3 backend pods, 512MB each = $50/month
# Recommendation: Auto-scale between 1-5 based on load

# Use Kubernetes HPA
kubectl autoscale deployment universal-agents-backend \
  --min=1 --max=5 --cpu-percent=70

# Estimated savings: $30-40/month
```

### Database Optimization

```bash
# Remove unused indexes
psql -U postgres -h localhost -c "
  SELECT schemaname, tablename, indexname, idx_scan
  FROM pg_stat_user_indexes
  WHERE idx_scan = 0
  ORDER BY pg_relation_size(indexrelid) DESC;"

# Add connection pooling (PgBouncer)
# Reduces database connections from 100+ to <20
# Estimated savings: 30% less DB resources
```

### Monitoring & Cost

```yaml
# prometheus.yml - Track usage metrics
scrape_configs:
  - job_name: 'cost-tracking'
    metrics_path: '/metrics'
    static_configs:
      - targets: ['localhost:8000']
```

---

## Maintenance Schedule

### Daily (Automated)
- [ ] Health checks (every 1 minute)
- [ ] Metrics collection (every 15 seconds)
- [ ] Log aggregation (continuous)

### Weekly
- [ ] Database vacuum and analyze
- [ ] Review error logs
- [ ] Check resource trends
- [ ] Cache effectiveness review

### Monthly
- [ ] Database backup verification
- [ ] Disaster recovery drill
- [ ] Performance baseline comparison
- [ ] Cost analysis and optimization
- [ ] Security audit

### Quarterly
- [ ] Full system capacity planning
- [ ] Architecture review
- [ ] Dependency updates
- [ ] Performance profiling

---

## Useful Commands Quick Reference

```bash
# System health
kubectl get pods,svc,pvc -n universal-agents

# Logs
kubectl logs -f deployment/universal-agents-backend -n universal-agents
kubectl logs -f statefulset/postgres -n universal-agents

# Resource usage
kubectl top pods -n universal-agents --sort-by memory

# Database
kubectl exec postgres-0 -- psql -c "SELECT COUNT(*) FROM projects;"

# Redis
kubectl exec redis-0 -- redis-cli INFO stats

# Metrics
curl http://localhost:8000/metrics | head -20

# Health
curl http://localhost:8000/ready | jq '.'
```

---

**Last Updated**: 2026-03-06
**Status**: Production Ready ✓
