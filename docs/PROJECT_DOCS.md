# AI Code Review Bot — Project Documentation

**Single source of truth** for architecture, behavior, data model, APIs, and operations.  
Repository root: `AI_Code_Review_Bot/`.

---

## 1. Project Overview

### What it is

**AI Code Review Bot** is a production **GitHub App** that automatically reviews pull requests using **four parallel Claude (Anthropic) specialist agents**, then posts a **summary comment** and **inline review comments** with **expandable fix prompts** on GitHub. It optionally reacts to **“changes requested”** reviews from human seniors by generating **mentoring guidance** stored in the database. A **Next.js dashboard** provides history, stats, a prompts library, and **real-time notifications** via **Server-Sent Events (SSE)**.

### What it does

- Listens for GitHub webhooks (`pull_request`, `pull_request_review`).
- Verifies **HMAC-SHA256** signatures and enforces **idempotency** (Redis + `X-GitHub-Delivery`).
- Offloads work to **Celery** workers (Redis broker) so the HTTP handler returns quickly.
- Fetches PR **unified diffs**, runs **Color/Constants**, **Logic/Bugs**, **Best Practices**, and **Security** agents in parallel, then an **Aggregator** to merge and rank findings.
- Posts results via the **GitHub REST API** (installation access tokens from JWT + app private key).
- Persists **repositories, pull requests, reviews, issues, senior comments, and notifications** in **PostgreSQL** (e.g. Supabase).

### Who it is for

- **Developers** who want automated, consistent PR feedback on every push without leaving GitHub.
- **Teams / leads** who want optional visibility into cost, severity trends, and prompt quality via the dashboard.
- **Operators** who need a clear split: **GitHub = primary UX**, **dashboard = observability**.

### Key features

| Feature | Summary |
|--------|---------|
| Automatic PR review | Triggers on `opened`, `synchronize`, `reopened` |
| Four specialist agents + aggregator | Parallel Claude calls; merged verdict and fix prompts |
| Inline GitHub comments | Batch PR review API with per-line comments and collapsible fix prompts |
| Senior “changes requested” flow | Webhook → Celery → `SeniorCommentAgent` → DB + notifications (no mandatory GitHub reply from bot) |
| Dashboard | Reviews list/detail, prompts library, settings placeholder, SSE notifications |
| Cost tracking | Per-agent token usage and Haiku-style USD estimate in code |
| Idempotency & security | Redis dedup of deliveries; HMAC verification |
| Health checks | `/health` checks API, Redis, PostgreSQL |

---

## 2. Complete Folder Structure

Files are grouped as requested. Paths are relative to `AI_Code_Review_Bot/`.

### Backend API (`apps/api/`)

| File | Description |
|------|-------------|
| `main.py` | FastAPI app factory, lifespan DB init, CORS, mounts routers, `GET /`, `GET /health`. |
| `Dockerfile` | Container image for API/worker deployment. |
| `requirements.txt` | Python dependencies for the API and workers. |
| `alembic.ini` | Alembic configuration for migrations. |
| `alembic/env.py` | Alembic environment (async engine wiring when used). |
| `alembic/script.py.mako` | Template for new migration scripts. |
| `alembic/versions/.gitkeep` | Placeholder so the versions directory is tracked. |

### Core (`apps/api/core/`)

| File | Description |
|------|-------------|
| `__init__.py` | Package marker. |
| `config.py` | `pydantic-settings` — env vars, PEM decoding for GitHub private key. |
| `database.py` | Async SQLAlchemy engine, session factory, `get_db`, `init_db` (create_all). |
| `redis_client.py` | Async Redis client (TLS for `rediss://`), used for idempotency, Celery, pub/sub. |
| `celery_app.py` | Celery app: broker/backend, queues `high`/`default`, task limits, includes `tasks.review_tasks`. |

### Agents (`apps/api/agents/`)

| File | Description |
|------|-------------|
| `__init__.py` | Re-exports agent classes for orchestrator imports. |
| `base_agent.py` | `BaseAgent`: async Anthropic calls, PR context injection, JSON parsing, token/cost stats. |
| `color_constants.py` | **ColorConstantsAgent** — hardcoded colors, magic numbers, design tokens. |
| `logic_bugs.py` | **LogicBugsAgent** — logic errors, null/async/state issues, edge cases. |
| `best_practices.py` | **BestPracticesAgent** — naming, complexity, duplication, error handling, performance. |
| `security.py` | **SecurityAgent** — secrets, XSS, injection, auth, insecure defaults. |
| `aggregator.py` | **AggregatorAgent** — merges four outputs, dedup, severity counts, `fix_prompts`, markdown summary. |
| `senior_comment.py` | **SeniorCommentAgent** — turns senior comments + optional diff into guidance and fix prompts (JSON). |

### Services (`apps/api/services/`)

| File | Description |
|------|-------------|
| `__init__.py` | Package marker. |
| `github_auth.py` | JWT (RS256) for GitHub App; exchange for installation access token. |
| `github_client.py` | PR diff, files, issue comments, single/batch review comments, review comments list. |
| `review_orchestrator.py` | Runs four agents with `asyncio.gather`, aggregates, posts to GitHub. |
| `notification_service.py` | `publish_notification`: Redis PUB/SUB + optional `Notification` row; `notification_generator` for SSE. |

### Models (`apps/api/models/`)

| File | Description |
|------|-------------|
| `__init__.py` | Package marker. |
| `models.py` | SQLAlchemy models: `Repository`, `PullRequest`, `Review`, `Issue`, `SeniorComment`, `Notification`. |

### Routers (`apps/api/routers/`)

| File | Description |
|------|-------------|
| `__init__.py` | Package marker. |
| `webhooks.py` | `POST /webhooks/github` — HMAC, idempotency, Celery enqueue. |
| `reviews.py` | `GET /reviews/stats`, `GET /reviews`, `GET /reviews/{review_id}`. |
| `prompts.py` | `GET /prompts`, `POST /prompts/{issue_id}/feedback`. |
| `notifications.py` | `GET /notifications/stream`, `GET /notifications`, `PATCH .../read`, `POST .../mark-all-read`. |

### Tasks (`apps/api/tasks/`)

| File | Description |
|------|-------------|
| `__init__.py` | Package marker. |
| `review_tasks.py` | Celery tasks: `process_pr_review`, `process_senior_comments`; DB updates and notifications. |

### Frontend Dashboard (`apps/dashboard/`)

| File | Description |
|------|-------------|
| `package.json` | Next.js 15, React 19, Tailwind, scripts (`dev`, `build`, `start`, `lint`). |
| `package-lock.json` | Locked dependency tree. |
| `next.config.ts` | Next.js configuration. |
| `next-env.d.ts` | TypeScript/Next autogenerated types. |
| `tsconfig.json` | TypeScript compiler options. |
| `tsconfig.tsbuildinfo` | Incremental build cache. |
| `tailwind.config.ts` | Tailwind + typography plugin. |
| `postcss.config.js` | PostCSS pipeline. |
| `Dockerfile` | Dashboard container build. |
| `netlify.toml` | Netlify build/publish settings for the dashboard. |
| `.env.example` | Example `NEXT_PUBLIC_API_URL` for local dev. |
| `app/layout.tsx` | Root layout. |
| `app/globals.css` | Global styles. |
| `app/page.tsx` | Home / overview dashboard. |
| `app/reviews/page.tsx` | Reviews list. |
| `app/reviews/[id]/page.tsx` | Single review detail. |
| `app/prompts/page.tsx` | Prompts library. |
| `app/settings/page.tsx` | Settings UI. |
| `components/ReviewCard.tsx` | Review summary card. |
| `components/IssuesList.tsx` | Issues list for a review. |
| `components/PromptCard.tsx` | Prompt display + feedback. |
| `components/NotificationBell.tsx` | Notification UI. |
| `components/Sidebar.tsx` | Navigation sidebar. |
| `hooks/useNotifications.ts` | SSE + REST for notifications. |
| `lib/api.ts` | Typed API client helpers. |

### Config & deployment (repo root)

| File | Description |
|------|-------------|
| `.env.example` | All backend env vars documented (copy to `.env`). |
| `.gitignore` | Ignored artifacts (venv, `.env`, etc.). |
| `Procfile` | Railway: `web` (uvicorn) and `worker` (Celery). |
| `railway.toml` | Railway service configuration. |
| `docker-compose.yml` | Local full stack (Postgres, Redis, API, worker, dashboard). |
| `docker-compose.prod.yml` | Production-oriented compose (e.g. worker replicas). |

### Docs (`docs/`)

| File | Description |
|------|-------------|
| `PROJECT_DOCS.md` | **This file** — full project documentation. |
| `TERMS.md` | Terms-related content (if present). |
| `USAGE_GUIDE.md` | Usage guide (if present). |
| `architecture-diagram.html` | Static architecture diagram page. |
| `flow-diagram.html` | Static flow diagram page. |

### Netlify static site (`netlify-site/`)

| File | Description |
|------|-------------|
| `index.html` | Landing/static page. |
| `netlify.toml` | Netlify config for that site. |
| `_redirects` | Netlify redirects rules. |
| `build_index.py` | Helper script for building index content. |

### Private / local (listed for completeness; not committed secrets)

| File | Description |
|------|-------------|
| `.env` | Local secrets (should not be committed). |

---

## 3. How It Works — End-to-End Flow

### Happy path: developer opens or updates a PR

1. **GitHub** sends `POST` to `{API_BASE_URL}/webhooks/github` with headers `X-Hub-Signature-256`, `X-GitHub-Event`, `X-GitHub-Delivery`, and a JSON body.

2. **`webhooks.github_webhook`** (`routers/webhooks.py`):
   - Reads raw **body** bytes for signature verification.
   - **`verify_signature`**: computes HMAC-SHA256 of the body with `GITHUB_WEBHOOK_SECRET`; compares to `sha256=...`. If `GITHUB_WEBHOOK_SECRET` is empty, verification is skipped (dev only — **not for production**).
   - **Idempotency**: if `X-GitHub-Delivery` is present, checks Redis key `webhook:processed:{delivery}`; if exists → returns `{status: "already_processed"}` without re-queuing. Otherwise sets key with **24h TTL**.
   - Parses JSON. For `X-GitHub-Event == "pull_request"` and `action in ("opened", "synchronize", "reopened")`, builds `task_payload` (installation id, owner, repo, PR metadata, stats).
   - **`process_pr_review.apply_async(..., queue="high")`** — Celery task queued with retries.
   - Returns **`{"status": "queued", ...}`** immediately (fast response for GitHub).

3. **Celery worker** runs **`process_pr_review`** (`tasks/review_tasks.py`):
   - **`_run_async`** runs async code in a new event loop.
   - **`_process_pr_review_async`**:
     - **Upserts `Repository`** by GitHub repo id; **upserts `PullRequest`** by repo + PR number; creates a **`Review`** row with `status="running"`, commits.
     - Builds **`pr_context`**: title, repo full name, author, files/additions/deletions from payload.
     - Instantiates **`GitHubClient(installation_id)`** and **`ReviewOrchestrator(gh)`**.
     - Calls **`await orchestrator.run_review(owner, repo_name, pr_number, head_sha, pr_context)`**.

4. **`ReviewOrchestrator.run_review`** (`services/review_orchestrator.py`):
   - **`get_pr_diff`**: GitHub API returns unified diff (`Accept: application/vnd.github.diff`).
   - If diff empty/trivial → short-circuits with approved-style message and **no GitHub review** (still returns structured dict; DB completion still runs).
   - Constructs four agents: `ColorConstantsAgent`, `LogicBugsAgent`, `BestPracticesAgent`, `SecurityAgent`.
   - **`asyncio.gather(..., return_exceptions=True)`**: parallel Claude calls; failures become exceptions logged and stored as empty/error slices in `agent_outputs`.
   - **`AggregatorAgent.aggregate`**: single Claude call over combined JSON; returns `verdict`, `summary_markdown`, severity totals, **`fix_prompts`** array.
   - Computes **token/cost** stats from all agents + aggregator (`BaseAgent.get_stats` / aggregator’s `get_stats`).
   - **`_post_results_to_github`**:
     - **`post_issue_comment`**: PR thread summary (`## 🤖 AI Code Review Bot` + markdown).
     - Builds **inline** payloads from `fix_prompts` (file, line — first line if range — severity emoji, agent label, issue text, collapsible fix prompt).
     - **`post_pr_review_batch`**: one **pull request review** with `event: COMMENT` and multiple inline comments.
     - On failure → falls back to **`post_review_comment`** per item; 422 on a line may fall back to issue comment for that body.

5. **Back in `_process_pr_review_async`**:
   - Reloads **`Review`**, sets `status="completed"`, stores `agents_output`, `final_summary`, counts, **`tokens_used`**, **`cost_usd`**, `completed_at`.
   - Inserts **`Issue`** rows from each `fix_prompt` (severity, agent, file, line, prompts).
   - **`publish_notification`** (`review_completed`, metadata with review id, repo, PR, verdict).

### Error paths (PR review)

| Stage | What can fail | Behavior |
|-------|----------------|----------|
| HMAC | Wrong secret / tampered body | **401** `Invalid signature`. |
| Idempotency | Duplicate delivery | **200** `already_processed` — no duplicate Celery job. |
| Non-PR events | Other events or actions | **200** `ignored`. |
| Celery | Worker down / Redis down | GitHub may retry delivery; idempotency prevents double work **after** first success marking. Task has **autoretry** with backoff. |
| GitHub token | Bad installation or key | Exceptions bubble; task retries per Celery config. |
| Single agent | Exception in `gather` | Logged; that agent’s slot gets `issues: []` + `error` string; others proceed. |
| Aggregator | Parse failure | Fallback JSON with empty `fix_prompts` / error messaging from `aggregator.py`. |
| Batch review | API error | Warning log; **fallback** to per-line `post_review_comment`; individual failures logged. |
| Trivial diff | Very small/empty diff | No inline review; summary may still be minimal LGTM-style from orchestrator return path. |

### Secondary path: senior developer requests changes

1. GitHub sends **`pull_request_review`** with `action == "submitted"` and `review.state == "changes_requested"`.

2. **`webhooks.py`** builds payload including **`comments`** (currently includes review **body** as one synthetic comment if present).

3. **`process_senior_comments`** Celery task:
   - Fetches PR diff (best effort).
   - **`SeniorCommentAgent.handle`** produces `handled_comments` with explanation, guidance, fix prompt.
   - Looks up **`PullRequest`** by repo full name + PR number; if missing, **returns early** (no rows).
   - Inserts **`SeniorComment`** rows; **`publish_notification`** (`senior_feedback`).

**Note:** This flow **persists guidance in PostgreSQL** and pushes **dashboard notifications**. It does **not** automatically post a new GitHub comment unless you extend the code.

---

## 4. External Services — What We Use and Why

| Service | What it is | Why we use it here | Alternatives |
|---------|------------|---------------------|--------------|
| **GitHub (webhooks, API)** | Source control + Apps platform | Webhooks for PR/review events; REST API for diffs and review comments; GitHub Apps give installation-scoped tokens and bot identity. | GitLab/GitBucket webhooks + API (would require a different integration layer). |
| **Anthropic / Claude** | LLM API | Strong code understanding; structured JSON following system prompts; async SDK. | OpenAI, Gemini, local models (tradeoffs: quality, JSON reliability, context window). |
| **Supabase (PostgreSQL)** | Hosted Postgres | Free tier, connection string friendly for SQLAlchemy async; relational data for reviews/issues. | Neon, RDS, self-hosted Postgres, PlanetScale (MySQL — schema would differ). |
| **Upstash (Redis)** | Serverless Redis | Celery broker/backend TLS (`rediss://`); pub/sub for SSE; idempotency keys. | ElastiCache, Redis Cloud, RabbitMQ for queue only (would need separate pub/sub or SSE strategy). |
| **Ngrok (dev tunneling)** | HTTPS tunnel to localhost | GitHub requires public HTTPS webhook URL; ngrok exposes local FastAPI. | Cloudflare Tunnel, localtunnel, VS Code port forwarding with a public URL. |
| **Netlify (dashboard hosting)** | Static/SSR frontend host | Easy deploy for Next.js; env for `NEXT_PUBLIC_API_URL`. | Vercel, Cloudflare Pages, Railway static. |
| **Railway (backend hosting)** | PaaS for web + worker | `Procfile` runs **web** + **worker**; env vars for secrets. | Fly.io, Render, Docker on ECS/Kubernetes. |

---

## 5. Features Deep Dive

### Automatic PR review

- **Trigger:** `pull_request` webhook with `action` in `opened`, `synchronize`, `reopened`.
- **Checks:** Entire **PR unified diff** (not just file list). Four agents specialize; aggregator dedupes and ranks.

### Four specialist AI agents (plus aggregator)

| Agent | Focus | Example findings |
|-------|--------|------------------|
| **ColorConstantsAgent** | Design tokens, magic numbers | Hex color in JSX instead of `theme.colors.primary`; arbitrary `padding: 13` vs token. |
| **LogicBugsAgent** | Correctness | Missing `await`; impossible `if`; stale closure in `useEffect`; off-by-one. |
| **BestPracticesAgent** | Maintainability | 200-line function; duplicated validation; swallowed errors. |
| **SecurityAgent** | Security | Hardcoded API key; `dangerouslySetInnerHTML` with user HTML; `eval`. |
| **AggregatorAgent** | Synthesis | Single markdown summary; `fix_prompts` with file/line/severity; verdict. |

### Inline GitHub comments (batch review)

- Implemented in **`GitHubClient.post_pr_review_batch`**: `POST /repos/{owner}/{repo}/pulls/{pull_number}/reviews` with `comments[]` (path, line, body, side `RIGHT`).
- **`ReviewOrchestrator`** builds bodies with emoji by severity, agent name, issue text, and **`<details>`** block for the fix prompt.

### Fix prompts

- **What:** Short, copy-paste instructions aimed at Claude/Copilot to implement a fix for a specific file/line.
- **How to use:** Expand the **Fix Prompt** section on the inline GitHub comment; paste into your AI assistant; apply the suggested change and push — a new **`synchronize`** event triggers a **new** review.

### Senior developer guidance

- **When:** Human submits a review with **Changes requested**.
- **What:** `SeniorCommentAgent` outputs structured JSON: explanation, step-by-step **guidance**, **fix_prompt** per handled comment.
- **Where it shows up:** Database (`senior_comments`) and dashboard detail API; optional notifications. **No automatic GitHub reply** in the current codebase.

### Real-time dashboard (SSE)

- **`GET /notifications/stream`**: `EventSourceResponse(notification_generator())` subscribes to Redis channel `notifications`.
- **`publish_notification`** publishes JSON to Redis and optionally inserts a **`Notification`** row.
- Frontend **`hooks/useNotifications.ts`**: on mount calls **`getNotifications`** (REST), then opens **`EventSource(`${NEXT_PUBLIC_API_URL}/notifications/stream`)`**. Incoming messages prepend to local state (max 50); payloads with `type === "connected"` are ignored. **`onerror`** closes the stream and **reconnects after 5 seconds**.

### Cost tracking

- **`BaseAgent.get_stats`** and **`AggregatorAgent.get_stats`**: Haiku-like pricing assumption — **$1/M input tokens**, **$5/M output tokens** (approximate; adjust if pricing changes).
- Stored on **`Review`**: `tokens_used`, `cost_usd`.

### Idempotency

- Redis key: `webhook:processed:{X-GitHub-Delivery}` with **86400 s** TTL.
- Prevents duplicate processing when GitHub retries the same delivery id.

### HMAC security

- Header: **`X-Hub-Signature-256`**.
- **`verify_signature`**: HMAC-SHA256 over **raw body**; constant-time compare.
- Empty `GITHUB_WEBHOOK_SECRET` skips verification — **development only**.

---

## 6. Web UI vs GitHub Integration

- The **bot operates entirely through GitHub** once the app is installed: developers see **summary** and **inline** comments on the PR **without opening any dashboard**.
- The **dashboard is optional**: analytics, searchable history, prompts library, notifications UI.
- **Comments appear on the PR** automatically after the worker finishes (typically on the order of tens of seconds, depending on diff size and model latency).
- **No manual step** is required after installation beyond normal GitHub permissions and webhook URL configuration for your deployment.

---

## 7. How to Use It — Step by Step

### For a developer

1. **Install the GitHub App** on the account or organization that owns the repository (see root `README.md` for permissions and events).
2. **Open a PR** (or push new commits to an existing PR).
3. **Wait** roughly **30–60 seconds** (longer for large diffs or queue backlog).
4. Open the PR **Files changed** tab and read **inline review** comments; read the **summary** on the conversation tab.
5. Expand **Fix prompts**, paste into your AI tool, apply fixes locally.
6. **Push** new commits; **`synchronize`** fires → **new review** run.

### For a team lead

1. Open the **dashboard** (Netlify or local) for **aggregate stats**: `/reviews/stats` drives totals, severity breakdown, cost, tokens, recent reviews.
2. Use **trends** implicitly via history lists and issue severity fields (no separate analytics product in-repo).

**Note on severity counts:** `GET /reviews/stats` aggregates `Issue.severity` for values `critical`, `warning`, and `info`. The aggregator’s `fix_prompts` often use **`high` / `medium` / `low`**. If dashboard severity buckets look empty or skewed, compare stored `Issue.severity` values to those filter strings.

### For sharing / demo

1. Install on a **public** test repo (or grant access on private).
2. Open a PR with intentional issues (colors, logic, security) to showcase **parallel** findings and **inline** prompts.

---

## 8. Database Schema

Six tables (SQLAlchemy in `models/models.py`).

### `repositories`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID PK | Internal id. |
| `github_id` | int, unique | GitHub repository id. |
| `full_name` | string | e.g. `owner/name`. |
| `installation_id` | int | GitHub App installation id. |
| `is_active` | bool | Soft enable/disable. |
| `config` | JSON, nullable | Extensible repo config. |
| `created_at` | timestamptz | Created. |

**Relationships:** One `repository` → many `pull_requests`.

### `pull_requests`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID PK | Internal id. |
| `repo_id` | FK → `repositories.id` | Owning repo. |
| `pr_number` | int | GitHub PR number. |
| `title`, `author` | string | PR metadata. |
| `head_sha` | string | Current HEAD sha reviewed. |
| `base_branch`, `head_branch` | nullable string | Branches. |
| `state` | string | e.g. open/closed. |
| `created_at` | timestamptz | Created. |

**Constraints:** `UniqueConstraint(repo_id, pr_number)`.

**Relationships:** Many `reviews`; many `senior_comments`.

### `reviews`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID PK | Internal id. |
| `pr_id` | FK → `pull_requests.id` | PR. |
| `status` | string | e.g. `running`, `completed`. |
| `trigger_type` | string | e.g. `pr_webhook`. |
| `github_comment_id` | bigint, nullable | Optional link to GitHub comment. |
| `agents_output` | JSON, nullable | Raw combined agent output blob. |
| `final_summary` | text, nullable | Markdown summary text. |
| `total_issues` | int | Count derived from severity buckets. |
| `critical_count`, `warning_count`, `info_count` | int | Aggregated issue counts. |
| `tokens_used` | int | Total tokens for the run. |
| `cost_usd` | float | Estimated USD. |
| `started_at`, `completed_at`, `created_at` | timestamptz | Lifecycle. |

**Relationships:** One `review` → many `issues`.

### `issues`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID PK | Used as **issue id** in `POST /prompts/{issue_id}/feedback`. |
| `review_id` | FK → `reviews.id` | Parent review. |
| `agent_type` | string | Which agent produced it. |
| `severity` | string | e.g. critical / high / medium / low (aggregator) or agent-specific labels. |
| `category` | string | Short category label. |
| `file_path` | text | File path in repo. |
| `line_number` | int, nullable | Line in diff context. |
| `description` | text | Human-readable issue text. |
| `suggested_fix`, `generated_prompt` | text, nullable | Fix suggestion / copy-paste prompt. |
| `is_dismissed` | bool | Soft dismiss. |
| `is_helpful` | bool, nullable | User feedback. |
| `created_at` | timestamptz | Created. |

**Indexes:** `idx_issues_severity` on `severity`.

### `senior_comments`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID PK | Internal id. |
| `pr_id` | FK → `pull_requests.id` | PR. |
| `github_comment_id` | bigint, nullable | Optional GitHub comment id. |
| `reviewer_login` | string | Human reviewer username. |
| `body` | text | Original comment text (or synthesized). |
| `file_path`, `line_number` | nullable | Location if known. |
| `generated_prompt`, `guidance` | text, nullable | AI outputs. |
| `created_at` | timestamptz | Created. |

### `notifications`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID PK | Matches payload id from pub/sub when published from service. |
| `type` | string | e.g. `review_completed`, `senior_feedback`. |
| `title`, `body` | text | Display fields. |
| `metadata` | JSON column mapped as `extra_data` in ORM | Extra payload. |
| `is_read` | bool | Read state. |
| `created_at` | timestamptz | Created. |

**Indexes:** `idx_notifications_read` on `is_read`, `created_at`.

---

## 9. API Endpoints

All routers are mounted in `main.py` with **no** global prefix except each router’s own `prefix`.

### Root (`main.py`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Service name, version, status, link to `/docs`. |
| GET | `/health` | `api`, `redis`, `database` checks; `healthy` vs `degraded`. |

### Webhooks (`/webhooks`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/webhooks/github` | GitHub webhook; HMAC + idempotency + Celery. |

### Reviews (`/reviews`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/reviews/stats` | Dashboard aggregates + recent reviews. |
| GET | `/reviews` | Paginated list; optional `status` filter. |
| GET | `/reviews/{review_id}` | Detail with `issues` and PR-linked `senior_comments`. |

### Prompts (`/prompts`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/prompts` | Paginated prompts library; filters: `severity`, `agent`, `search`. |
| POST | `/prompts/{issue_id}/feedback` | Body `{ "helpful": true/false }` — sets `Issue.is_helpful`. |

### Notifications (`/notifications`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/notifications/stream` | SSE stream (Redis pub/sub). |
| GET | `/notifications` | Paginated list; `unread_only` query param. |
| PATCH | `/notifications/{notification_id}/read` | Mark one read. |
| POST | `/notifications/mark-all-read` | Mark all read. |

### Auto docs

| Method | Path | Description |
|--------|------|-------------|
| GET | `/docs` | Swagger UI (FastAPI default). |
| GET | `/redoc` | ReDoc (if enabled by FastAPI defaults). |

---

## 10. Environment Variables

Defined in `apps/api/core/config.py` and `.env.example`. All can be set in the environment or in `.env` at repo root (see `Config.env_file` path in `config.py`).

| Variable | Required | Description |
|----------|----------|-------------|
| `GITHUB_APP_ID` | Yes (production) | GitHub App numeric id. |
| `GITHUB_APP_PRIVATE_KEY` | Yes | PEM string **or** base64-encoded PEM (see `github_private_key_pem`). |
| `GITHUB_WEBHOOK_SECRET` | Strongly recommended | Secret for HMAC; empty disables verification. |
| `GITHUB_CLIENT_ID` | Optional | OAuth client id (placeholder for future user login). |
| `GITHUB_CLIENT_SECRET` | Optional | OAuth client secret. |
| `ANTHROPIC_API_KEY` | Yes | Claude API key. |
| `MODEL_NAME` | Optional | Default `claude-haiku-4-5-20251001`. |
| `MAX_TOKENS_AGENT` | Optional | Per-agent max output tokens (default 4096). |
| `MAX_TOKENS_AGGREGATOR` | Optional | Aggregator max output tokens (default 8192). |
| `DATABASE_URL` | Yes | Async SQLAlchemy URL, e.g. `postgresql+asyncpg://...`. |
| `REDIS_URL` | Yes | Redis URL; use `rediss://` for TLS (Upstash). |
| `API_BASE_URL` | Optional | Public base URL of this API (documented for callbacks/links; default localhost). |
| `FRONTEND_URL` | Optional | Allowed CORS origin for dashboard (plus `http://localhost:3000` always allowed in `main.py`). |

### Dashboard (`apps/dashboard/.env.local`)

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_API_URL` | Browser-accessible base URL of the FastAPI backend (e.g. `http://localhost:8000` or Railway URL). |

---

## Appendix: Celery tasks

| Task | Queue | Purpose |
|------|-------|---------|
| `process_pr_review` | `high` (from webhook) | Full AI review pipeline + GitHub post + DB + notification. |
| `process_senior_comments` | `high` | Senior comment handling + DB + notification. |

Both use **`_run_async`** to bridge sync Celery to async SQLAlchemy and httpx.

---

*End of PROJECT_DOCS.md — keep in sync when adding routers, models, or deployment targets.*
