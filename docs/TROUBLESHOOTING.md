# Troubleshooting Guide - Universal Agent Team

Comprehensive guide to diagnose and fix common issues.

## Table of Contents
1. [System Won't Start](#system-wont-start)
2. [Database Issues](#database-issues)
3. [Cache & Redis Issues](#cache--redis-issues)
4. [API Issues](#api-issues)
5. [Performance Issues](#performance-issues)
6. [Memory Issues](#memory-issues)
7. [Network Issues](#network-issues)
8. [Debug Techniques](#debug-techniques)

---

## System Won't Start

### Issue: "Cannot connect to database"

**Symptom**: Backend pod crashes with connection error

```
ERROR: Cannot connect to database at postgresql://...
FATAL: Server exited with code 1
```

**Diagnosis**:
```bash
# Check if PostgreSQL is running
kubectl get pod postgres-0 -n universal-agents

# Check pod logs
kubectl logs postgres-0 -n universal-agents

# Check database service
kubectl get svc postgres-service -n universal-agents

# Test connection from backend pod
kubectl exec -n universal-agents <backend-pod> -- \
  psql -h postgres-service -U postgres -c "SELECT 1"
```

**Solutions**:

1. **Database pod not started**
```bash
# Check pod status
kubectl describe pod postgres-0 -n universal-agents

# Restart database
kubectl rollout restart statefulset/postgres -n universal-agents

# Wait for it to be ready
kubectl wait --for=condition=ready pod/postgres-0 -n universal-agents --timeout=300s
```

2. **Wrong connection string**
```bash
# Verify DATABASE_URL in secret
kubectl get secret api-config -n universal-agents -o jsonpath='{.data.DATABASE_URL}' | base64 -d

# Should be: postgresql://postgres:password@postgres-service:5432/universal_agents
# Check:
#   - Host: postgres-service (Kubernetes DNS name)
#   - Port: 5432 (default PostgreSQL port)
#   - Database: universal_agents (must exist)
```

3. **Database doesn't exist**
```bash
# Create database
kubectl exec postgres-0 -n universal-agents -- \
  psql -U postgres -c "CREATE DATABASE universal_agents IF NOT EXISTS;"

# Run migrations
kubectl exec -n universal-agents <backend-pod> -- \
  alembic upgrade head
```

4. **Connection pool exhausted**
```bash
# Check connections
kubectl exec postgres-0 -n universal-agents -- \
  psql -U postgres -c "SELECT sum(numbackends) FROM pg_stat_database;"

# Increase connection limit
kubectl exec postgres-0 -n universal-agents -- \
  psql -U postgres -c "ALTER SYSTEM SET max_connections = 200;"

# Restart database
kubectl exec postgres-0 -n universal-agents -- pg_ctl reload
```

---

### Issue: "Redis unavailable"

**Symptom**: Backend crashes when connecting to Redis

```
ERROR: Cannot connect to redis://redis-service:6379
redis.ConnectionError: Connection refused
```

**Diagnosis**:
```bash
# Check Redis pod
kubectl get pod redis-0 -n universal-agents

# Check Redis logs
kubectl logs redis-0 -n universal-agents

# Test Redis connection
kubectl exec -n universal-agents <backend-pod> -- \
  redis-cli -h redis-service ping

# Check Redis service
kubectl get svc redis-service -n universal-agents
```

**Solutions**:

1. **Redis not running**
```bash
# Check pod status
kubectl describe pod redis-0 -n universal-agents

# Restart Redis
kubectl rollout restart statefulset/redis -n universal-agents
```

2. **Wrong Redis URL**
```bash
# Verify REDIS_URL
kubectl get secret api-config -n universal-agents -o jsonpath='{.data.REDIS_URL}' | base64 -d

# Should be: redis://redis-service:6379
# Or for cluster: redis+cluster://redis-service:6379
```

3. **Redis out of memory**
```bash
# Check memory usage
kubectl exec redis-0 -n universal-agents -- redis-cli INFO memory

# Check eviction policy
kubectl exec redis-0 -n universal-agents -- redis-cli CONFIG GET maxmemory-policy

# Set eviction
kubectl exec redis-0 -n universal-agents -- \
  redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

---

### Issue: "API key not valid"

**Symptom**: All Claude API calls fail with authentication error

```
ERROR: Invalid API key
AuthenticationError: Unauthorized
```

**Diagnosis**:
```bash
# Verify API key is set
echo $ANTHROPIC_API_KEY

# Check if key is in environment
kubectl exec -n universal-agents <pod> -- env | grep ANTHROPIC

# Verify key format (should be sk-ant-...)
echo $ANTHROPIC_API_KEY | grep -E '^sk-ant-'
```

**Solutions**:

1. **API key missing**
```bash
# Create secret with key
kubectl create secret generic api-keys \
  -n universal-agents \
  --from-literal=anthropic=sk-ant-YOUR_KEY_HERE

# Update deployment to use secret
# In k8s/backend-deployment.yaml:
env:
- name: ANTHROPIC_API_KEY
  valueFrom:
    secretKeyRef:
      name: api-keys
      key: anthropic
```

2. **API key expired**
```bash
# Get new key from https://console.anthropic.com/account/keys

# Update secret
kubectl patch secret api-keys \
  -n universal-agents \
  -p '{"data":{"anthropic":"'$(echo -n 'sk-ant-NEW_KEY' | base64 -w0)'"}}'

# Restart backend
kubectl rollout restart deployment/universal-agents-backend -n universal-agents
```

3. **Quota exceeded**
```bash
# Check usage in Anthropic console
# https://console.anthropic.com/usage

# If over quota:
# - Add payment method
# - Increase monthly quota
# - Or reduce token usage with compression
```

---

## Database Issues

### Issue: "Slow queries" degrading performance

**Symptom**: API responses taking >500ms, high database CPU

**Diagnosis**:
```bash
# Find slow queries
kubectl exec postgres-0 -n universal-agents -- psql -U postgres -c "
SELECT query, calls, mean_exec_time, total_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;"

# Check query plan
EXPLAIN ANALYZE SELECT * FROM projects WHERE user_id = 'xyz' ORDER BY created_at DESC;

# Check table sizes
SELECT schemaname, tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

**Solutions**:

1. **Missing indexes**
```sql
-- Add missing indexes
CREATE INDEX idx_projects_user_created ON projects(user_id, created_at DESC);
CREATE INDEX idx_artifacts_project_type ON artifacts(project_id, artifact_type);
CREATE INDEX idx_cache_expiry ON cache_entries(expiry_time);

-- Verify indexes
SELECT schemaname, tablename, indexname FROM pg_indexes ORDER BY tablename;
```

2. **Unused indexes**
```sql
-- Find unused indexes
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
WHERE idx_scan = 0
ORDER BY pg_relation_size(indexrelid) DESC;

-- Drop unused indexes
DROP INDEX idx_old_unused_index;
```

3. **Query optimization**
```python
# Original: N+1 query problem
projects = db.query(Project).all()
for project in projects:
    agents = db.query(Agent).filter_by(project_id=project.id).all()  # ❌ N queries

# Optimized: Join in single query
projects = db.query(Project)\
    .options(joinedload(Project.agents))\
    .all()  # ✓ 1 query

# Or use batch loading
from sqlalchemy.orm import batchload
projects = db.query(Project).options(batchload(Project.agents)).all()
```

---

### Issue: "Disk full" - Database storage maxed

**Symptom**: Database stops accepting writes, error: "No space left on device"

**Diagnosis**:
```bash
# Check disk usage
kubectl exec postgres-0 -n universal-agents -- df -h

# Check PVC usage
kubectl get pvc postgres-data -n universal-agents

# Find large tables
kubectl exec postgres-0 -n universal-agents -- psql -U postgres -c "
SELECT schemaname, tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename))
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;"
```

**Solutions**:

1. **Increase PVC size**
```bash
# Get current PVC
kubectl get pvc postgres-data -n universal-agents

# Increase size (AWS EBS example)
kubectl patch pvc postgres-data -n universal-agents -p \
  '{"spec":{"resources":{"requests":{"storage":"100Gi"}}}}'

# Restart database
kubectl rollout restart statefulset/postgres -n universal-agents
```

2. **Vacuum database**
```bash
# Remove dead rows
kubectl exec postgres-0 -n universal-agents -- \
  psql -U postgres -d universal_agents -c "VACUUM ANALYZE;"

# This can free 20-40% space
```

3. **Archive old data**
```bash
# Export old projects (>30 days)
kubectl exec postgres-0 -n universal-agents -- psql -U postgres -c "
COPY (SELECT * FROM projects WHERE created_at < now() - interval '30 days')
TO '/tmp/old_projects.csv';"

# Delete old projects
DELETE FROM projects WHERE created_at < now() - interval '90 days';

# Vacuum again
VACUUM ANALYZE;
```

---

## Cache & Redis Issues

### Issue: "Cache hit rate low" (< 80%)

**Symptom**: Cache_hit_rate metric shows < 80%

**Diagnosis**:
```bash
# Check cache statistics
curl http://localhost:8000/metrics | grep cache

# Check what's being cached
kubectl exec -n universal-agents <pod> -- python -c "
from backend.services.cache_service import CacheService
cache = CacheService()
print(f'Items: {len(cache._fallback_cache)}')
print(f'Hit rate: {cache.hit_rate}')
print(f'Memory: {sum(len(str(v)) for v in cache._fallback_cache.values())} bytes')
"
```

**Solutions**:

1. **Increase cache size**
```python
# config/settings.py
MAX_CACHE_SIZE = 10000  # Increase from default 1000

# Restart pods
kubectl rollout restart deployment/universal-agents-backend -n universal-agents
```

2. **Increase cache TTL**
```python
# Keep items longer
CACHE_TTL_SECONDS = 7200  # 2 hours instead of 1 hour

# Restart pods
kubectl rollout restart deployment/universal-agents-backend -n universal-agents
```

3. **Use Redis instead of in-memory cache**
```python
# Switch to Redis (distributed cache)
from backend.services.redis_cache import RedisCache
cache = RedisCache(redis_url="redis://redis-service:6379")

# Redis survives restarts, better for distributed systems
```

---

### Issue: "Redis running out of memory"

**Symptom**: Redis dropping keys, "OOM command not allowed"

```
MISCONF Redis is configured to save RDB snapshots, but is currently not able
```

**Diagnosis**:
```bash
# Check Redis memory
kubectl exec redis-0 -n universal-agents -- redis-cli INFO memory

# Expected output:
# used_memory: 500000000  (500MB)
# maxmemory: 1000000000   (1GB)

# Check what's consuming memory
redis-cli --bigkeys

# Top keys by size
redis-cli --bigvalues
```

**Solutions**:

1. **Increase Redis memory limit**
```bash
# Edit Redis configuration
kubectl edit configmap redis-config -n universal-agents

# Change:
# maxmemory 1gb

# Restart Redis
kubectl delete pod redis-0 -n universal-agents
```

2. **Set eviction policy**
```bash
# Use Least Recently Used
kubectl exec redis-0 -n universal-agents -- \
  redis-cli CONFIG SET maxmemory-policy allkeys-lru

# Or volatile-lru (only expire keys with TTL)
redis-cli CONFIG SET maxmemory-policy volatile-lru

# Persistent change
redis-cli CONFIG REWRITE
```

3. **Enable compression**
```python
# Compress values before caching
import json
import gzip

def compress_cache_value(value):
    serialized = json.dumps(value).encode()
    return gzip.compress(serialized)

def decompress_cache_value(compressed):
    return json.loads(gzip.decompress(compressed).decode())
```

---

## API Issues

### Issue: "API returning 500 errors"

**Symptom**: Requests return HTTP 500, no clear error in logs

```
HTTP/1.1 500 Internal Server Error
Content-Type: application/json

{"detail": "Internal server error"}
```

**Diagnosis**:
```bash
# Check application logs
kubectl logs -f deployment/universal-agents-backend -n universal-agents | grep -A 5 ERROR

# Enable debug logging
kubectl set env deployment/universal-agents-backend \
  -n universal-agents \
  LOG_LEVEL=DEBUG

# Check the full error
curl -v http://localhost:8000/api/projects
```

**Solutions**:

1. **Database error**
```python
# Add error logging
import logging
logger = logging.getLogger(__name__)

try:
    projects = db.query(Project).all()
except Exception as e:
    logger.exception(f"Database error: {e}")
    raise

# Check logs
kubectl logs deployment/universal-agents-backend -n universal-agents | grep "Database error"
```

2. **Memory exhaustion**
```bash
# Check memory
kubectl top pod <pod-name> -n universal-agents

# If at limit:
kubectl set resources deployment universal-agents-backend \
  -n universal-agents \
  --limits memory=2Gi \
  --requests memory=1Gi
```

3. **Timeout**
```bash
# Check if request is timing out
# Add timeout configuration
# config/settings.py:
AGENT_TIMEOUT_SECONDS = 600  # Increase from 300

# Restart
kubectl rollout restart deployment/universal-agents-backend -n universal-agents
```

---

### Issue: "CORS errors" when calling from frontend

**Symptom**:
```
Access to XMLHttpRequest blocked by CORS policy:
No 'Access-Control-Allow-Origin' header
```

**Diagnosis**:
```bash
# Check CORS configuration
curl -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: GET" \
  -I http://localhost:8000/api/projects

# Should include Access-Control-Allow-Origin header
```

**Solution**:
```python
# backend/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",       # Development
        "https://example.com",          # Production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Performance Issues

### Issue: "API responses slow" (> 100ms)

**Symptom**: `curl` shows long response times

```bash
$ time curl http://localhost:8000/api/projects
real    0m0.523s  # ❌ 523ms - too slow!
```

**Diagnosis**:
```bash
# Check API latency percentiles
curl -s http://localhost:8000/metrics | \
  grep 'http_request_duration_seconds_bucket' | head -10

# Check database query times
# Enable slow query logging in PostgreSQL
docker exec <postgres-container> psql -U postgres -c "
ALTER SYSTEM SET log_min_duration_statement = 100;"
```

**Solutions**:

1. **Add database indexes**
```sql
-- Identify slow queries first
EXPLAIN ANALYZE SELECT * FROM projects WHERE user_id = 'xyz';

-- Add missing index
CREATE INDEX idx_projects_user ON projects(user_id);
```

2. **Enable caching**
```python
# Cache frequently accessed data
from functools import lru_cache

@lru_cache(maxsize=100)
def get_user_projects(user_id: str):
    return db.query(Project).filter_by(user_id=user_id).all()
```

3. **Profile the code**
```python
# Use cProfile to find bottlenecks
python -m cProfile -s cumulative backend/main.py

# Look for functions with high cumulative time
```

---

## Memory Issues

### Issue: "Pod gets OOMKilled"

**Symptom**: Pod restarts unexpectedly
```
Error: OOMKilled - Container memory exceeded limit
```

**Diagnosis**:
```bash
# Check memory usage over time
kubectl top pod <pod-name> -n universal-agents --containers

# Check current limits
kubectl describe pod <pod-name> -n universal-agents | grep -A 5 "Limits\|Requests"

# Check memory leaks
# Monitor for steady growth
for i in {1..10}; do
  kubectl top pod <pod-name> -n universal-agents
  sleep 10
done
```

**Solutions**:

1. **Increase pod memory limit**
```bash
kubectl set resources deployment universal-agents-backend \
  -n universal-agents \
  --limits memory=4Gi
```

2. **Find memory leaks**
```python
# Add memory tracking
import tracemalloc

tracemalloc.start()

# ... run some operations ...

current, peak = tracemalloc.get_traced_memory()
print(f"Current: {current / 1024 / 1024:.1f}MB")
print(f"Peak: {peak / 1024 / 1024:.1f}MB")

# Find top allocators
snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')
for stat in top_stats[:10]:
    print(stat)
```

3. **Reduce cache size**
```python
# config/settings.py
MAX_CACHE_SIZE = 1000  # Reduce from default 10000
```

---

## Network Issues

### Issue: "Connection refused" between pods

**Symptom**: Pod can't reach another service
```
connection refused
Unable to connect to postgres-service
```

**Diagnosis**:
```bash
# Test DNS resolution
kubectl exec -n universal-agents <pod> -- nslookup postgres-service

# Test connectivity
kubectl exec -n universal-agents <pod> -- \
  nc -zv postgres-service 5432

# Check service endpoints
kubectl get endpoints postgres-service -n universal-agents

# Check network policies
kubectl get networkpolicies -n universal-agents
```

**Solutions**:

1. **Service doesn't exist**
```bash
# Check service
kubectl get svc postgres-service -n universal-agents

# If missing, create it
kubectl expose statefulset postgres --port=5432 --target-port=5432 \
  -n universal-agents
```

2. **Network policy blocking traffic**
```bash
# Check policies
kubectl get networkpolicies -n universal-agents

# Allow all traffic (development only!)
kubectl delete networkpolicies --all -n universal-agents

# Or adjust policy
kubectl edit networkpolicy <policy-name> -n universal-agents
```

---

## Debug Techniques

### Enable Debug Logging

```bash
# Set log level to DEBUG
kubectl set env deployment/universal-agents-backend \
  -n universal-agents \
  LOG_LEVEL=DEBUG

# Follow debug logs
kubectl logs -f deployment/universal-agents-backend -n universal-agents | grep DEBUG
```

### Execute Debug Commands in Pod

```bash
# Interactive shell
kubectl exec -it <pod-name> -n universal-agents -- /bin/bash

# Check environment
env | sort

# Check Python version
python --version

# Check installed packages
pip list | grep -E "fastapi|sqlalchemy|redis"

# Run Python interactively
python
>>> from backend.services.cache_service import CacheService
>>> cache = CacheService()
>>> len(cache._fallback_cache)
42
```

### Capture Network Traffic

```bash
# Install tcpdump if needed
kubectl exec <pod> -n universal-agents -- apt-get install -y tcpdump

# Capture traffic to Redis
kubectl exec <pod> -n universal-agents -- \
  tcpdump -i any dst redis-service and port 6379 -w /tmp/redis.pcap

# View captured traffic
tcpdump -r /tmp/redis.pcap
```

### Profile CPU Usage

```bash
# Install profiler
kubectl exec <pod> -n universal-agents -- pip install py-spy

# Profile running process
kubectl exec <pod> -n universal-agents -- \
  py-spy record -o /tmp/profile.svg -d 30 -p 1

# Download and view
kubectl cp universal-agents/<pod>:/tmp/profile.svg .
# Open in browser
```

---

**Last Updated**: 2026-03-06
**Status**: Production Ready ✓
