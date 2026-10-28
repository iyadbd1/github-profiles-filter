# GitHub Profile Filter — Product Specification

## Overview
Internal tool for recruiters/hiring managers to evaluate GitHub candidates by username/URL. Fetches profile, repositories, and contribution heatmap; filters/sorts by technical criteria; exports to CSV/JSON.

**Target**: Small team (<100 searches/day) | **Deploy**: Local machine / VPS via Docker Compose

---

## User Workflows

### Primary: Candidate Lookup
1. Recruiter enters GitHub username (`octocat`) or full URL (`https://github.com/octocat`)
2. System fetches profile + repos + contribution heatmap (cached or live)
3. Recruiter applies filters: language, min/max stars, forks, archived/fork toggle, location substring, recent activity window
4. Recruiter sorts: stars ↓, forks ↓, updated ↓, created ↓
5. Results update instantly in URL (shareable link)
6. Recruiter exports filtered repo list to CSV/JSON

### Secondary: Cache Refresh
- Manual "Refresh" button triggers `POST /sync/{username}` → background re-fetch from GitHub
- Automatic background sync for recently queried users (configurable interval)

---

## Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-01 | Accept username or GitHub URL; normalize to lowercase username | P0 |
| FR-02 | Return profile: name, bio, location, company, blog, twitter, avatar, stats (repos, followers, following, created_at) | P0 |
| FR-03 | Return repositories with: name, description, language, stars, forks, is_fork, is_archived, topics, updated_at, html_url | P0 |
| FR-04 | Return contribution heatmap (GraphQL `contributionsCollection`): weeks → days → count, level (0-3), date | P0 |
| FR-05 | Filter repos by: `language` (multi), `min_stars`, `max_stars`, `min_forks`, `is_fork`, `is_archived` | P0 |
| FR-06 | Sort repos by: `stars_desc`, `forks_desc`, `updated_desc`, `created_desc` | P0 |
| FR-07 | Paginate repo results: `page` (default 1), `per_page` (default 30, max 100) | P0 |
| FR-08 | Export filtered repos to CSV (streaming) and JSON | P0 |
| FR-09 | Cache profile (24h), repos (6h), contributions (1h) in SQLite | P0 |
| FR-10 | Respect GitHub rate limits; return `429` with `Retry-After` when exhausted | P0 |
| FR-11 | Serve stale cache with `cached_at` timestamp when rate limited | P0 |
| FR-12 | Shared API key auth via `X-API-Key` header | P1 |
| FR-13 | Health endpoint with cache stats | P1 |

---

## Non-Functional Requirements

| Category | Requirement |
|----------|-------------|
| **Performance** | API p95 < 200ms (cache hit); < 2s (cache miss + GitHub) |
| **Workflow Speed** | `bun install` < 2s; `bun dev` HMR < 100ms; prod build < 10s |
| **Reliability** | Graceful degradation: show cached data + warning when GitHub unavailable |
| **Usability** | Shareable URLs for filter state; keyboard-navigable filter panel; responsive table |
| **Security** | API key rotated via `.env`; no secrets in repo; input validation on username |
| **Observability** | Structured logs (JSON); request ID correlation; cache hit/miss metrics |

---

## Data Model

### SQLite Tables
```sql
cached_users (
  username TEXT PRIMARY KEY,
  raw_json TEXT NOT NULL,
  fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  etag TEXT
)

cached_repos (
  id INTEGER PRIMARY KEY,
  owner_username TEXT NOT NULL,
  raw_json TEXT NOT NULL,
  language TEXT,
  stargazers_count INTEGER NOT NULL,
  forks_count INTEGER NOT NULL,
  is_fork BOOLEAN NOT NULL,
  is_archived BOOLEAN NOT NULL,
  updated_at TIMESTAMP NOT NULL,
  fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (owner_username) REFERENCES cached_users(username)
)

cached_contributions (
  username TEXT PRIMARY KEY,
  raw_json TEXT NOT NULL,
  fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (username) REFERENCES cached_users(username)
)

sync_metadata (key TEXT PRIMARY KEY, value TEXT, updated_at TIMESTAMP)
```

### Indexes
- `idx_repos_owner_lang` ON `cached_repos(owner_username, language)`
- `idx_repos_owner_stars` ON `cached_repos(owner_username, stargazers_count DESC)`
- `idx_repos_owner_updated` ON `cached_repos(owner_username, updated_at DESC)`

---

## API Contract (OpenAPI 3.1)

### `GET /api/v1/users/{username}`
**Params**: `include_repos` (bool, default true), `include_contributions` (bool, default true)  
**Response**: `UserProfileResponse`

### `GET /api/v1/users/{username}/repos`
**Params**: `language`, `min_stars`, `max_stars`, `min_forks`, `is_fork`, `is_archived`, `sort`, `page`, `per_page`  
**Response**: `PaginatedReposResponse`

### `GET /api/v1/users/{username}/export`
**Params**: same as `/repos` + `format` (`csv`|`json`)  
**Response**: File download (streaming)

### `POST /api/v1/sync/{username}`
**Body**: `{ "force": false }`  
**Response**: `{ "status": "queued"|"completed", "synced_at": "..." }`

### `GET /api/v1/health`
**Response**: `{ "status": "ok", "cache_users": 42, "cache_repos": 1200 }`

### Error Envelope (all errors)
```json
{
  "error": {
    "code": "USER_NOT_FOUND|USER_PRIVATE|RATE_LIMITED|UPSTREAM_ERROR|VALIDATION_ERROR",
    "message": "Human-readable",
    "retry_after": 60,
    "cached_at": "2024-01-15T10:30:00Z"
  }
}
```

---

## UI Specification

### Layout
- **Header**: App title, GitHub token status indicator
- **Main**: Split view — left: UsernameInput + FilterPanel; right: ProfileCard + RepoTable/Heatmap tabs
- **Footer**: Export button, cache freshness badge

### Components
| Component | Behavior |
|-----------|----------|
| `UsernameInput` | Text input; accepts `user` or `https://github.com/user`; debounced 300ms; enter = lookup |
| `FilterPanel` | Collapsible; multi-select language chips; numeric range inputs (stars/forks); toggle chips for fork/archived; location text; recency dropdown (7d/30d/90d) |
| `SortSelect` | Dropdown; updates URL `sort=` param |
| `RepoTable` | Virtualized (react-window); sortable columns; language color badges; star/fork counts; external link |
| `ContributionHeatmap` | Calendar grid (cal-heatmap or custom); tooltip on hover shows count/date; color scale 0-3 |
| `ExportButton` | Dropdown: CSV / JSON; triggers streaming download |
| `ErrorToast` | Auto-dismiss (5s) for warnings; persistent for errors; shows `retry_after` countdown for rate limits |

### State Management
- **Server state**: TanStack Query (5min staleTime, cache deduping, retry 2x with exponential backoff)
- **Filter state**: URL search params (`?language=python,typescript&min_stars=100&sort=stars_desc`)
- **UI state only**: Zustand (filter panel open/closed, theme)

---

## Acceptance Criteria

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Happy path | Valid username, cache miss | User submits | Profile + repos + heatmap load < 2s; filters work; export downloads |
| Cache hit | Same username within TTL | User submits | Loads < 200ms; `cached_at` badge shows freshness |
| Rate limited | GitHub quota exhausted | User submits | Shows cached data + warning toast with `Retry-After` countdown |
| Private user | Username exists but private | User submits | `USER_PRIVATE` error; no crash |
| Invalid username | Non-existent user | User submits | `USER_NOT_FOUND` error; clear message |
| Shareable URL | Filters applied | Copy URL | New tab opens with identical filter state |
| Keyboard nav | Focus on FilterPanel | Tab/Enter/Space | All controls reachable; no focus trap |

---

## Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GITHUB_TOKEN` | Yes | — | Personal access token (classic, `public_repo` scope) for 5k/hr limit |
| `INTERNAL_API_KEY` | Yes | — | Shared secret for `X-API-Key` header |
| `CACHE_TTL_PROFILE` | No | 86400 | Profile cache TTL (seconds) |
| `CACHE_TTL_REPOS` | No | 21600 | Repos cache TTL (seconds) |
| `CACHE_TTL_CONTRIBUTIONS` | No | 3600 | Contributions cache TTL (seconds) |
| `SYNC_INTERVAL` | No | 3600 | Background sync interval (seconds) |
| `LOG_LEVEL` | No | INFO | `DEBUG`|`INFO`|`WARNING`|`ERROR` |

---

## Out of Scope (v1)
- Multi-user search/discovery (by location, language, etc.)
- User accounts / OAuth / teams
- Real-time collaboration
- PDF reports
- Webhook integrations (ATS, Slack)
- Historical trend analysis