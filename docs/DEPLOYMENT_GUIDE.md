# Deployment Guide - Universal Agent Team

Complete guide for deploying to development, staging, and production environments.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Local Development](#local-development)
3. [Docker Deployment](#docker-deployment)
4. [Kubernetes Deployment](#kubernetes-deployment)
5. [Configuration Management](#configuration-management)
6. [Health Checks](#health-checks)
7. [Scaling](#scaling)
8. [Monitoring](#monitoring)

---

## Prerequisites

### Minimum System Requirements
- **CPU**: 2 cores (4+ recommended for production)
- **Memory**: 4GB (8GB+ recommended)
- **Disk**: 20GB (fast SSD recommended)
- **Network**: Stable internet connection

### Required Software
- **Python**: 3.11 or later
- **Docker**: 20.10+ (for containerized deployment)
- **Docker Compose**: 1.29+ (for local development)
- **Git**: For repository management
- **curl** or **Postman**: For API testing

### Required Accounts/Keys
- **Anthropic API Key**: Get from https://console.anthropic.com/account/keys
- **Docker Hub Account** (optional, for pushing images)

### External Services
- **PostgreSQL**: 14+ (can be containerized)
- **Redis**: 6.2+ (can be containerized)

---

## Local Development

### Quick Setup (5 minutes)

```bash
# 1. Clone repository
git clone <repo-url>
cd universal-agent-team

# 2. Create Python environment
python3.11 -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Setup environment
cp .env.example .env
# Edit .env with your configuration
```

### Environment Configuration

Create `.env` file with the following:

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...
DATABASE_URL=postgresql://postgres:password@localhost:5432/universal_agents
REDIS_URL=redis://localhost:6379

# Optional (defaults shown)
ENVIRONMENT=development
LOG_LEVEL=INFO
DEBUG=false
WORKER_COUNT=4
MAX_AGENT_RETRIES=3
AGENT_TIMEOUT_SECONDS=300
```

### Start Infrastructure Services

```bash
# Start PostgreSQL
docker run -d \
  --name postgres-dev \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=password \
  -p 5432:5432 \
  postgres:16

# Start Redis
docker run -d \
  --name redis-dev \
  -p 6379:6379 \
  redis:7-alpine

# Verify connections
psql -U postgres -h localhost -d postgres -c "SELECT 1"
redis-cli ping  # Should return PONG
```

### Run the Application

```bash
# Terminal 1: Start backend
python -m uvicorn backend.main:app --reload --port 8000

# Terminal 2: Monitor logs
tail -f /tmp/universal-agents.log
```

### Verify It's Working

```bash
# Health check
curl http://localhost:8000/health
# Expected: {"status": "healthy"}

# API docs
curl http://localhost:8000/api/docs
```

---

## Docker Deployment

### Using Docker Compose (Recommended)

#### Development Environment

```bash
# Start all services
docker-compose -f docker-compose.yml up -d

# View logs
docker-compose logs -f

# Check status
docker-compose ps

# Stop services
docker-compose down
```

#### Production-like Environment

```bash
# Start with production configuration
docker-compose -f docker-compose.prod.yml up -d

# Scale backend to 3 replicas
docker-compose up -d --scale backend=3

# View logs
docker-compose logs -f backend
```

### Building Images Manually

```bash
# Build backend image
docker build -f Dockerfile.backend \
  -t universal-agent-team:backend-latest \
  .

# Build frontend image (if applicable)
docker build -f Dockerfile.frontend \
  -t universal-agent-team:frontend-latest \
  ./frontend

# Tag for registry
docker tag universal-agent-team:backend-latest \
  myregistry.azurecr.io/universal-agent-team:backend-1.0.0

# Push to registry
docker push myregistry.azurecr.io/universal-agent-team:backend-1.0.0
```

### Running Individual Containers

```bash
# Backend
docker run -d \
  --name universal-agents-backend \
  -p 8000:8000 \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  -e DATABASE_URL=postgresql://... \
  -e REDIS_URL=redis://... \
  universal-agent-team:backend-latest

# Check logs
docker logs -f universal-agents-backend

# Stop
docker stop universal-agents-backend
```

---

## Kubernetes Deployment

### Prerequisites

```bash
# Install Kubernetes CLI
kubectl version --client

# Verify cluster connection
kubectl cluster-info

# Create namespace
kubectl create namespace universal-agents
kubectl config set-context --current --namespace=universal-agents
```

### Deploy Using kubectl

```bash
# Apply configuration manifests
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secrets.yaml  # Configure API keys
kubectl apply -f k8s/postgres-pvc.yaml
kubectl apply -f k8s/postgres-deployment.yaml
kubectl apply -f k8s/redis-deployment.yaml
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/service.yaml

# Verify deployment
kubectl get deployments -n universal-agents
kubectl get pods -n universal-agents
kubectl get services -n universal-agents
```

### Deploy Using Helm (Recommended)

```bash
# Add Helm repository
helm repo add universal-agents https://charts.example.com
helm repo update

# Install
helm install universal-agents universal-agents/universal-agent-team \
  --namespace universal-agents \
  --values helm-values.yaml

# Upgrade
helm upgrade universal-agents universal-agents/universal-agent-team \
  --namespace universal-agents \
  --values helm-values.yaml

# Rollback
helm rollback universal-agents 1
```

### Kubernetes Configuration Example

```yaml
# k8s/backend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: universal-agents-backend
  namespace: universal-agents
spec:
  replicas: 3
  selector:
    matchLabels:
      app: universal-agents-backend
  template:
    metadata:
      labels:
        app: universal-agents-backend
    spec:
      containers:
      - name: backend
        image: universal-agent-team:backend-latest
        imagePullPolicy: Always
        ports:
        - containerPort: 8000
        env:
        - name: ANTHROPIC_API_KEY
          valueFrom:
            secretKeyRef:
              name: api-keys
              key: anthropic
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: database-config
              key: url
        - name: REDIS_URL
          value: "redis://redis-service:6379"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
```

---

## Configuration Management

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | Yes | - | Claude API key |
| `DATABASE_URL` | Yes | - | PostgreSQL connection string |
| `REDIS_URL` | Yes | - | Redis connection URL |
| `ENVIRONMENT` | No | development | dev/staging/production |
| `LOG_LEVEL` | No | INFO | DEBUG/INFO/WARNING/ERROR |
| `DEBUG` | No | false | Enable debug mode |
| `WORKER_COUNT` | No | 4 | Number of worker processes |
| `MAX_AGENT_RETRIES` | No | 3 | Max retry attempts |
| `AGENT_TIMEOUT_SECONDS` | No | 300 | Agent timeout |

### Configuration Files

**Development** (`config/settings.py`):
```python
class DevelopmentSettings(Settings):
    debug = True
    log_level = "DEBUG"
    database_pool_size = 5
    redis_pool_size = 2
    enable_metrics = False
```

**Production** (`config/settings.py`):
```python
class ProductionSettings(Settings):
    debug = False
    log_level = "WARNING"
    database_pool_size = 20
    redis_pool_size = 10
    enable_metrics = True
    cache_ttl_seconds = 3600
```

### Secrets Management

```bash
# Kubernetes secrets
kubectl create secret generic api-keys \
  --from-literal=anthropic=sk-ant-...

# Docker secrets
docker secret create api_key -
# Paste the key and press Ctrl+D
```

---

## Health Checks

### Liveness Probe
Indicates if the application is running.

```bash
curl http://localhost:8000/health
# Returns: {"status": "healthy"}
```

### Readiness Probe
Indicates if the application is ready to accept requests.

```bash
curl http://localhost:8000/ready
# Returns: {"ready": true, "checks": {...}}
```

### Metrics
Prometheus-format metrics for monitoring.

```bash
curl http://localhost:8000/metrics
```

### Kubernetes Health Configuration

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 10
  timeoutSeconds: 5

readinessProbe:
  httpGet:
    path: /ready
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
  timeoutSeconds: 3
```

---

## Scaling

### Horizontal Scaling (Add More Instances)

**Docker Compose:**
```bash
docker-compose up -d --scale backend=3
```

**Kubernetes:**
```bash
kubectl scale deployment universal-agents-backend --replicas=5
```

### Vertical Scaling (Increase Resources)

**Kubernetes resource limits:**
```yaml
resources:
  requests:
    memory: "1Gi"
    cpu: "500m"
  limits:
    memory: "4Gi"
    cpu: "2000m"
```

### Auto-scaling (Kubernetes)

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: universal-agents-autoscale
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: universal-agents-backend
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

---

## Monitoring

### Prometheus Setup

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'universal-agents'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

### Grafana Dashboard

```bash
# Import dashboard
# JSON file: dashboards/universal-agent-team.json
# Data source: Prometheus
# Refresh interval: 30s
```

### Key Metrics to Monitor

- `http_request_duration_seconds` - Request latency
- `http_requests_total` - Total requests
- `cache_hit_rate` - Cache effectiveness
- `database_query_duration_seconds` - DB performance
- `agent_execution_time_seconds` - Agent performance
- `memory_usage_bytes` - Memory consumption
- `cpu_usage_percent` - CPU usage

---

## Troubleshooting Deployments

### Container won't start

```bash
# View logs
docker logs <container-id>

# Check resources
docker stats

# Verify environment variables
docker exec <container-id> env | grep ANTHROPIC
```

### Database connection fails

```bash
# Check PostgreSQL
psql -U postgres -h postgres-service -d universal_agents -c "SELECT 1"

# Check connection string
echo $DATABASE_URL

# Verify firewall rules
# Ensure 5432 is accessible from backend pod
```

### Redis unavailable

```bash
# Check Redis
redis-cli -h redis-service ping

# Check circuit breaker state
curl http://localhost:8000/metrics | grep circuit_breaker

# Reset circuit breaker
# Restart backend pods
kubectl rollout restart deployment/universal-agents-backend
```

### High memory usage

```bash
# Check memory limits
kubectl describe pod <pod-name>

# Reduce cache sizes
# Edit config/settings.py:
# cache_size_limit = 100  # Reduce from default

# Restart pods
kubectl rollout restart deployment/universal-agents-backend
```

---

## Deployment Checklist

- [ ] All environment variables configured
- [ ] Database created and migrations applied
- [ ] Redis is accessible
- [ ] API key is valid and has appropriate quota
- [ ] TLS certificates configured (if needed)
- [ ] Logging configured and accessible
- [ ] Monitoring and alerting setup
- [ ] Backup strategy documented
- [ ] Disaster recovery plan in place
- [ ] Load balancer configured
- [ ] Auto-scaling policies configured
- [ ] Health checks passing
- [ ] Performance tests passing

---

**Last Updated**: 2026-03-06
**Status**: Production Ready ✓
