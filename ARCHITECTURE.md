# GitHub Profile Filter — Architecture Documentation

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           GITHUB PROFILE FILTER                              │
│                          (Internal Recruiter Tool)                          │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐     HTTPS      ┌──────────────┐     SQLite      ┌───────────┐
│   Browser    │◀──────────────▶│   FastAPI    │◀───────────────▶│  SQLite   │
│  (React +    │   /api/v1      │   Backend    │   (WAL mode)    │  Cache    │
│   Vite + TS) │                │  (Python)    │                 │           │
└──────┬───────┘                └──────┬───────┘                 └───────────┘
       │                               │
       │                               ▼
       │                      ┌──────────────────┐
       │                      │  GitHub APIs     │
       │                      │  REST v3 + GQL   │
       │                      └──────────────────┘
       │
       ▼
┌──────────────┐
│   Docker     │
│  Compose     │
│  (dev/prod)  │
└──────────────┘
```

---

## Technology Stack

| Layer | Technology | Version | Rationale |
|-------|------------|---------|-----------|
| **Backend Framework** | FastAPI | 0.110+ | Native async, OpenAPI auto-gen, Pydantic validation |
| **Language** | Python | 3.11+ | Async/await, excellent GitHub library ecosystem |
| **Database** | SQLite | 3.45+ | Zero-config, file-based, WAL mode for concurrency |
| **ORM** | SQLAlchemy | 2.0+ | Async support, type-safe queries |
| **HTTP Client** | httpx | 0.27+ | Async, HTTP/2, retry/timeout middleware |
| **Frontend Framework** | React | 18.2+ | Component model, concurrent features |
| **Build Tool** | Vite | 5.0+ | Instant HMR, esbuild production builds |
| **Package Manager** | **bun** | 1.1+ | Sub-second installs, native TypeScript, test runner |
| **State Management** | TanStack Query | 5.0+ | Server state, caching, deduping, retries |
| **URL State** | React Router | 6.20+ | Search params as filter state source of truth |
| **UI State** | Zustand | 4.4+ | Minimal client-only state (3-4 booleans) |
| **Styling** | Tailwind CSS | 3.4+ | Utility-first, dark mode, small bundle |
| **Containerization** | Docker Compose | 2.24+ | Single-command dev/prod parity |
| **Reverse Proxy** | Nginx | 1.25+ | TLS termination, static file serving |
| **CI/CD** | GitHub Actions | — | Native integration, matrix testing |

---

## Backend Architecture

### Module Structure
```
backend/app/
├── main.py                 # FastAPI app factory, lifespan, middleware
├── config.py               # Pydantic Settings (env-driven)
├── github/
│   ├── client.py           # REST client: users, repos, rate limiting
│   └── graphql.py          # GraphQL client: contributionsCollection
├── models/
│   ├── user.py             # UserProfile, UserProfileResponse
│   ├── repo.py             # Repository, PaginatedReposResponse
│   └── contribution.py     # ContributionHeatmap, ContributionDay/Week
├── cache/
│   ├── database.py         # SQLAlchemy async engine, session factory
│   └── repository.py       # CRUD for cached_users/repos/contributions
├── services/
│   ├── filter.py           # Pure filter/sort functions (unit tested)
│   ├── export.py           # Streaming CSV/JSON generation
│   └── sync.py             # Background + manual sync orchestration
├── api/
│   ├── routes.py           # Route definitions + dependencies
│   ├── schemas.py          # Pydantic request/response models
│   └── errors.py           # Unified error envelope + exception handlers
└── tasks/
    └── scheduler.py        # APScheduler background job
```

### Request Flow
```
GET /users/{username}
    │
    ▼
APIKeyDependency ──────▶ 401 if invalid
    │
    ▼
Check cache (cached_users) ──hit──▶ Return cached + is_stale flag
    │ miss
    ▼
GitHubClient.get_user() ─────▶ GitHub REST /users/{username}
    │
    ▼
Store in cache (upsert)
    │
    ▼
If include_repos: parallel fetch repos + contributions
    │
    ▼
FilterService.apply() ──────▶ In-memory filter on cached_repos rows
    │
    ▼
Return UserProfileResponse
```

### Cache Strategy

| Data | TTL | Invalidation | Refresh Trigger |
|------|-----|--------------|-----------------|
| Profile | 24h | TTL + manual sync | `POST /sync/{username}` |
| Repositories | 6h | TTL + manual sync | `POST /sync/{username}` |
| Contributions | 1h | TTL + manual sync | `POST /sync/{username}` |

**Denormalized columns** in `cached_repos` enable index-only filter scans:
- `language`, `stargazers_count`, `forks_count`, `is_fork`, `is_archived`, `updated_at`

### GitHub API Client

**Rate Limit Handling**
```python
# Respects X-RateLimit-* headers
# On 429: raises APIError("RATE_LIMITED", retry_after=reset_timestamp - now)
# On cache hit during rate limit: returns stale data + cached_at in error envelope
```

**Endpoints Used**
- `GET /users/{username}` — profile
- `GET /users/{username}/repos?per_page=100&sort=updated` — repos (paginated)
- `POST /graphql` — `contributionsCollection` query (see `graphql.py`)

---

## Frontend Architecture

### Module Structure
```
frontend/src/
├── main.tsx                # Entry: QueryClientProvider, Router, App
├── App.tsx                 # Layout, routes, global error boundary
├── api/
│   ├── client.ts           # fetch wrapper, error parsing, API key injection
│   └── endpoints.ts        # Typed API functions (getUser, getRepos, export)
├── components/
│   ├── UsernameInput.tsx   # Debounced, URL parsing, enter=submit
│   ├── FilterPanel.tsx     # Collapsible, multi-select chips, range inputs
│   ├── SortSelect.tsx      # Dropdown → URL param
│   ├── ProfileCard.tsx     # Avatar, bio, stats, top languages
│   ├── RepoTable.tsx       # Virtualized, sortable, language badges
│   ├── ContributionHeatmap.tsx  # Calendar grid, tooltip, color scale
│   ├── ExportButton.tsx    # Dropdown CSV/JSON → streaming download
│   └── ErrorToast.tsx      # Auto-dismiss, retry-after countdown
├── hooks/
│   ├── useUser.ts          # useQuery(['user', username])
│   ├── useRepos.ts         # useQuery(['repos', username, filters])
│   ├── useFilters.ts       # parse/serialize URL search params
│   └── useExport.ts        # Mutation for streaming download
├── types/
│   └── api.ts              # Generated from backend OpenAPI (or manual mirror)
└── utils/
    ├── format.ts           # Numbers, dates, abbreviations
    └── url.ts              # Username extraction from GitHub URLs
```

### Data Fetching Strategy

```typescript
// TanStack Query config
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,      // 5 min
      gcTime: 10 * 60 * 1000,        // 10 min
      retry: 2,
      retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 30000),
      refetchOnWindowFocus: false,
    },
  },
});

// Filter state = URL search params (single source of truth)
const [searchParams, setSearchParams] = useSearchParams();
const filters = useMemo(() => parseFilters(searchParams), [searchParams]);
```

**Why URL params?**
- Shareable links (copy/paste to colleague)
- Browser back/forward works
- No client-only state to sync
- SSR-ready if migration needed

### Component Interaction Flow
```
UsernameInput
    │ onSubmit(username)
    ▼
useUser(username) ───▶ GET /users/{username}
    │
    ├─▶ ProfileCard (profile data)
    │
    └─▶ useRepos(username, filters) ───▶ GET /users/{username}/repos?filters
           │
           ├─▶ RepoTable (paginated, sortable)
           │
           └─▶ ContributionHeatmap (from user query)
                    │
                    ▼
             FilterPanel / SortSelect
                    │ onChange(newFilters)
                    ▼
             setSearchParams(merged) ───▶ URL updates ───▶ useRepos re-fetches
```

---

## Infrastructure

### Docker Compose (Development)
```yaml
# docker-compose.yml
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    env_file: ./backend/.env
    volumes:
      - ./backend:/app
      - ./data:/data
    command: uvicorn app.main:app --reload --host 0.0.0.0

  frontend:
    build: ./frontend
    ports: ["5173:5173"]
    volumes:
      - ./frontend:/app
      - /app/node_modules
    command: bun dev --host
    environment:
      - VITE_API_BASE=http://localhost:8000/api/v1
      - VITE_API_KEY=${INTERNAL_API_KEY}
```

### Docker Compose (Production)
```yaml
# docker-compose.prod.yml
services:
  backend:
    command: uvicorn app.main:app --host 0.0.0.0 --workers 4
    deploy:
      resources:
        limits:
          memory: 512M
    restart: unless-stopped

  frontend:
    command: bun run build && bunx serve -s dist -l 5173
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports: ["80:80", "443:443"]
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./certbot:/etc/letsencrypt
    restart: unless-stopped
    depends_on: [frontend]
```

### Nginx Config (Production)
```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    location / {
        proxy_pass http://frontend:5173;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Data Persistence
- SQLite file at `/data/github_cache.db` (Docker volume `./data:/data`)
- Backup: `cp ./data/github_cache.db ./backups/github_cache_$(date +%F).db`
- No migrations needed (SQLAlchemy creates tables on startup)

---

## Security

### Authentication
- **Shared API Key**: `X-API-Key` header validated on every request
- Stored in `.env` (never committed); rotated quarterly
- Frontend injects via `VITE_API_KEY` build-time env var

### Input Validation
- Username: regex `^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,37}[a-zA-Z0-9])?$` (GitHub rules)
- URL parsing: extracts username via `github\.com/([^/?#]+)`
- All query params validated by Pydantic schemas

### Secrets Management
| Secret | Location | Rotation |
|--------|----------|----------|
| `GITHUB_TOKEN` | Backend `.env` | Quarterly (PAT) |
| `INTERNAL_API_KEY` | Both `.env` files | Quarterly |
| TLS certs | Let's Encrypt (certbot) | Auto 90-day |

### CORS
```python
# FastAPI CORS middleware
allow_origins = ["http://localhost:5173", "https://your-domain.com"]
allow_credentials = True
allow_methods = ["GET", "POST"]
allow_headers = ["X-API-Key", "Content-Type"]
```

---

## Observability

### Logging (Structured JSON)
```python
import structlog

logger = structlog.get_logger()
logger.info("request_started", path=request.url.path, user=username)
logger.warning("rate_limited", retry_after=60, cached_at=cached_at)
logger.error("upstream_error", error=str(e), username=username)
```

### Metrics (Prometheus-ready)
| Metric | Type | Description |
|--------|------|-------------|
| `http_requests_total` | Counter | By method, path, status |
| `http_request_duration_seconds` | Histogram | p50, p95, p99 |
| `cache_hits_total` | Counter | By table (users/repos/contributions) |
| `cache_misses_total` | Counter | By table |
| `github_api_calls_total` | Counter | By endpoint, status |
| `github_rate_limit_remaining` | Gauge | Current quota |

### Health Check
```json
GET /health
{
  "status": "ok",
  "cache_users": 42,
  "cache_repos": 1200,
  "github_rate_limit_remaining": 4873,
  "uptime_seconds": 3600
}
```

---

## CI/CD Pipeline

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]

jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install -e "backend[test]"
      - run: pytest backend/tests --cov=backend/app --cov-fail-under=80

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: oven-sh/setup-bun@v1
      - run: cd frontend && bun install && bun run test && bun run build

  e2e:
    needs: [backend, frontend]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: docker compose -f docker-compose.ci.yml up -d
      - run: npx playwright test --project=chromium

  docker:
    needs: [backend, frontend]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/build-push-action@v5
        with:
          context: ./backend
          push: true
          tags: ghcr.io/owner/github-profile-filter-backend:${{ github.sha }}
      - uses: docker/build-push-action@v5
        with:
          context: ./frontend
          push: true
          tags: ghcr.io/owner/github-profile-filter-frontend:${{ github.sha }}
```

---

## Scaling Considerations (Future)

| Bottleneck | Current Limit | Mitigation Path |
|------------|---------------|-----------------|
| SQLite write contention | Single writer | WAL mode handles dev load; migrate to Postgres for multi-instance |
| GitHub rate limit (5k/hr) | ~5k lookups/hr | Add Redis cache layer; request coalescing; multiple PATs |
| Frontend bundle size | ~150KB gzipped | Code-split heatmap; lazy-load export |
| Background sync | In-process APScheduler | Move to cron + separate worker container |

---

## Decision Log

| Date | Decision | Alternatives Considered | Rationale |
|------|----------|------------------------|-----------|
| 2024-01 | FastAPI + SQLite | Django + Postgres | Simplicity, zero-config, async native |
| 2024-01 | React + Vite + bun | Next.js + npm | Workflow speed, single toolchain, instant HMR |
| 2024-01 | TanStack Query + URL params | Redux + localStorage | Server-state purpose-built, shareable URLs free |
| 2024-01 | GraphQL for contributions | REST only | REST lacks contribution calendar data |
| 2024-01 | Denormalized filter columns | JSONB queries | Index-only scans, simpler SQL, portable |

---

## Quick Reference

### Commands
```bash
# Development
docker compose up                    # Starts backend:8000, frontend:5173
bun install                          # Frontend deps (in frontend/)
bun dev                              # Frontend dev server
uvicorn app.main:app --reload        # Backend dev server

# Testing
pytest backend/tests                 # Backend unit/integration
bun test                             # Frontend unit
npx playwright test                  # E2E

# Production
docker compose -f docker-compose.prod.yml up -d
docker compose logs -f backend       # View logs
```

### Key URLs
| Environment | Frontend | Backend API | API Docs |
|-------------|----------|-------------|----------|
| Local | http://localhost:5173 | http://localhost:8000/api/v1 | http://localhost:8000/docs |
| Prod | https://your-domain.com | https://your-domain.com/api/v1 | https://your-domain.com/docs |

### Environment Variables
```bash
# backend/.env
GITHUB_TOKEN=ghp_xxxxxxxxxxxx
INTERNAL_API_KEY=sk-xxxxxxxxxxxx
CACHE_TTL_PROFILE=86400
CACHE_TTL_REPOS=21600
CACHE_TTL_CONTRIBUTIONS=3600
LOG_LEVEL=INFO

# frontend/.env (build-time)
VITE_API_BASE=http://localhost:8000/api/v1
VITE_API_KEY=sk-xxxxxxxxxxxx
```