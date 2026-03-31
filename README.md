# AI Code Review Bot — Production GitHub App

A fully autonomous GitHub App that reviews every Pull Request with **4 specialized Claude agents**, posts inline comments with ready-to-paste fix prompts, handles senior developer feedback, and streams real-time notifications to a Next.js dashboard.

---

## Why a GitHub App (Not OAuth App)?

| GitHub App | OAuth App |
|------------|-----------|
| Installs on entire organization/repos automatically | User-specific, each user needs to authorize |
| Gets webhook events natively (PR opened, review submitted) | No native webhook support |
| Uses short-lived installation tokens (more secure) | Uses long-lived personal access tokens |
| Can act as a bot identity (not impersonating a user) | Acts as the user who authorized it |
| Fine-grained permissions (read contents, write PRs) | Broad scopes (repo, admin) |

**Our bot needs**: webhook events when PRs are opened + permission to post review comments + read code diffs. A GitHub App is the only correct choice for this.

---

## Architecture

```
GitHub PR Event → GitHub App Webhook → FastAPI (HMAC verify + idempotency) → 200 OK
                                              │
                                        Celery Queue (Redis, priority: high)
                                              │
                  ┌───────────────────────────┼───────────────────────────┐
                  │                           │                           │
          Agent 1: Color/         Agent 2: Logic/         Agent 3: Best      Agent 4:
          Constants               Bugs                    Practices          Security
          (hardcoded values,      (null checks,           (SRP, naming,      (OWASP, XSS,
           magic numbers,          race conditions,        nesting,            injection,
           design tokens)          edge cases)             error handling)     secrets)
                  │                           │                           │
                  └───────────────────────────┼───────────────────────────┘
                                              │
                                     Aggregator Agent
                                   (dedup, rank by severity, generate fix prompts)
                                              │
                           ┌──────────────────┼──────────────────┐
                           │                                     │
                    GitHub API                             PostgreSQL
               (batch PR review with                   (review history +
                inline comments +                       fix prompts +
                summary comment)                        cost tracking)
                           │
                    Redis Pub/Sub → SSE → Next.js Dashboard (real-time)
```

---

## Features

- **Automatic PR Review** — triggers on every PR opened/updated via GitHub webhook
- **4 Parallel Agents** — Color/Constants, Logic/Bugs, Best Practices, Security — all run simultaneously via `asyncio.gather`
- **Fix Prompts** — auto-generated prompt for every issue, paste into Claude/Copilot to get the fix instantly
- **Senior Comment Handler** — when a senior dev requests changes, auto-generates explanation + guidance + fix prompts
- **Real-Time Notifications** — SSE (Server-Sent Events) streaming to the dashboard with browser push notifications
- **Review History** — full searchable history with cost tracking per review
- **Batch Inline PR Comments** — posts a proper GitHub code review with inline comments on specific lines (not individual comments)
- **Idempotency** — uses `X-GitHub-Delivery` header + Redis to prevent duplicate reviews if GitHub retries
- **Prompt Feedback** — thumbs up/down on generated prompts to track which ones are actually useful
- **Dashboard Stats** — overview with total reviews, issues by severity, total cost, tokens used

---

## Tech Stack

| Component | Technology | Why This Choice |
|-----------|-----------|-----------------|
| Backend API | FastAPI + Python 3.12 | Async-native, returns 200 to GitHub in <200ms, auto-generates API docs |
| AI Engine | Claude (claude-haiku-4-5) via Anthropic SDK | Best code understanding, structured JSON output, supports parallel calls |
| Task Queue | Celery + Redis | Industry-standard, retry with exponential backoff, priority queues, scales horizontally |
| Database | PostgreSQL + SQLAlchemy (async) + Alembic | Relational integrity for reviews/issues, migrations for schema changes |
| Real-time | Redis Pub/Sub + SSE | Simpler than WebSocket for one-way notifications, no connection state to manage |
| Frontend | Next.js 15 + React 19 + TailwindCSS | App Router for routing, React for components, Tailwind for fast styling |
| GitHub Auth | GitHub App JWT + Installation Tokens | Short-lived tokens (1 hour), org-wide install, proper bot identity |
| Deployment | Railway (API + Worker) + Netlify (Dashboard) | Free tiers available, easy config, supports Procfile-based multi-process |

---

## Project Structure

```
AI_Code_Review_Bot/
├── apps/
│   ├── api/                        # FastAPI backend
│   │   ├── main.py                 # App factory, CORS, health check (DB+Redis)
│   │   ├── core/
│   │   │   ├── config.py           # Pydantic Settings — all env vars + PEM decoder
│   │   │   ├── celery_app.py       # Celery config — high/default queues, time limits
│   │   │   ├── database.py         # SQLAlchemy async engine, connection pooling
│   │   │   └── redis_client.py     # aioredis client with max 10 connections
│   │   ├── agents/
│   │   │   ├── base_agent.py       # Async base — pr_context injection + cost tracking
│   │   │   ├── color_constants.py  # Agent 1: hardcoded colors, magic numbers, design tokens
│   │   │   ├── logic_bugs.py       # Agent 2: null checks, race conditions, edge cases
│   │   │   ├── best_practices.py   # Agent 3: SRP, naming, nesting, error handling
│   │   │   ├── security.py         # Agent 4: OWASP, XSS, injection, exposed secrets
│   │   │   ├── aggregator.py       # Merges all findings, dedup, ranks, generates fix prompts
│   │   │   └── senior_comment.py   # Processes senior dev change requests into guidance
│   │   ├── services/
│   │   │   ├── github_auth.py      # JWT generation (RS256) + installation token exchange
│   │   │   ├── github_client.py    # GitHub API: diffs, batch reviews, PR details
│   │   │   ├── review_orchestrator.py  # asyncio.gather for parallel agent execution
│   │   │   └── notification_service.py # Redis pub/sub publish + DB persistence
│   │   ├── routers/
│   │   │   ├── webhooks.py         # POST /webhooks/github — HMAC + idempotency + Celery
│   │   │   ├── reviews.py          # GET /reviews, /reviews/{id}, /reviews/stats
│   │   │   ├── prompts.py          # GET /prompts + POST /prompts/{id}/feedback
│   │   │   └── notifications.py    # GET /notifications/stream (SSE) + CRUD
│   │   ├── models/
│   │   │   └── models.py           # 6 SQLAlchemy tables with indexes
│   │   ├── tasks/
│   │   │   └── review_tasks.py     # Celery tasks with autoretry + backoff
│   │   └── alembic/                # Database migrations
│   └── dashboard/                  # Next.js 15 frontend
│       ├── app/                    # Pages: /, /reviews, /reviews/[id], /prompts, /settings
│       ├── components/             # ReviewCard, IssuesList, PromptCard (with feedback), NotificationBell, Sidebar
│       ├── hooks/                  # useNotifications (SSE + REST initial load + auto-reconnect)
│       └── lib/                    # API client + TypeScript interfaces + getStats/ratePrompt
├── docker-compose.yml              # Full local dev: Postgres + Redis + API + Worker + Dashboard
├── docker-compose.prod.yml         # Production: API + Worker (2 replicas)
├── railway.toml                    # Railway deployment config
├── Procfile                        # web: FastAPI, worker: Celery
└── .env.example                    # All environment variables documented
```

---

## Agents — What Each One Does

| Agent | Role | What It Catches | Why It Matters |
|-------|------|-----------------|----------------|
| **Color & Constants** | UI/Design System Specialist | Hardcoded hex/RGB colors, magic numbers (16, 24, 300), inline styles overriding theme, inconsistent naming | Prevents design inconsistency, makes theme switching impossible if colors are hardcoded |
| **Logic & Bugs** | Logic Correctness Engineer | Null/undefined access, off-by-one errors, missing await, race conditions, stale state in React hooks, type mismatches | Catches bugs that pass linting but fail in production — the hardest bugs to find in code review |
| **Best Practices** | Clean Code Enforcer | Functions too long, deep nesting, missing error handling, unused imports, poor naming, code duplication, performance issues | Enforces what a senior dev would catch — maintainability issues that accumulate as tech debt |
| **Security** | OWASP Security Auditor | Exposed API keys, SQL injection, XSS (dangerouslySetInnerHTML), sensitive data logging, open CORS, eval() usage | Catches vulnerabilities before they reach production — every exposed secret is a potential breach |
| **Aggregator** | Lead Staff Engineer | De-duplicates findings across agents, ranks by severity, generates markdown summary + fix prompts | Produces the final GitHub comment — clean, organized, actionable |
| **Senior Handler** | Mentoring Assistant | Processes senior dev "changes requested" comments | When your senior requests changes, generates explanation of WHY + step-by-step guidance + ready-to-paste fix prompt |

Each agent outputs structured JSON with this schema:
```json
{
  "issues": [
    {
      "file": "src/Button.tsx",
      "line": 45,
      "severity": "warning",
      "category": "hardcoded-color",
      "code_snippet": "color: '#FF6B35'",
      "description": "Hardcoded color prevents theme switching",
      "suggested_fix": "Use theme.colors.primary instead",
      "fix_prompt": "In src/Button.tsx line 45, replace '#FF6B35' with the design token from theme..."
    }
  ],
  "summary": "Found 3 hardcoded colors that should be design tokens"
}
```

---

## COMPLETE SETUP GUIDE (Step by Step)

### Step 1 — Accounts You Need (All Free)

| # | Service | What For | Sign Up |
|---|---------|----------|---------|
| 1 | **GitHub** | Create the GitHub App that receives webhooks | You already have this |
| 2 | **Anthropic** | Claude API key — powers all 4 AI agents | [console.anthropic.com](https://console.anthropic.com) |
| 3 | **Supabase** | Free PostgreSQL database — stores reviews, issues, prompts | [supabase.com](https://supabase.com) |
| 4 | **Upstash** | Free Redis — Celery task queue + real-time pub/sub | [upstash.com](https://upstash.com) |
| 5 | **Railway** | Deploy backend API + Celery worker | [railway.app](https://railway.app) |
| 6 | **Netlify** | Deploy Next.js dashboard | [netlify.com](https://netlify.com) |

---

### Step 2 — Create the GitHub App (Field by Field)

Go to: **https://github.com/settings/apps/new**

Fill EVERY field exactly as shown:

**Basic Information:**

| Field | What to Enter | Why |
|-------|--------------|-----|
| **GitHub App name** | `AI Code Review Bot` | Display name users see when installing |
| **Description** | `Autonomous AI code reviewer — 4 parallel Claude agents analyze every PR for colors, logic, best practices, and security` | Shows on the app's page |
| **Homepage URL** | `https://github.com/Sharjeel-Saleem-06` | Your GitHub profile or app landing page |

**Identifying and authorizing users:**

| Field | What to Select | Why |
|-------|---------------|-----|
| **Callback URL** | Leave empty | We don't need OAuth user login for the bot |
| **Expire user authorization tokens** | Check it (default) | Security best practice |
| **Request user authorization during installation** | UNCHECK | Bot doesn't need user identity — it acts as itself |
| **Enable Device Flow** | UNCHECK | Not needed for webhook-based bot |

**Post installation:**

| Field | What to Enter |
|-------|--------------|
| **Setup URL** | Leave empty |
| **Redirect on update** | UNCHECK |

**Webhook:**

| Field | What to Enter | How to Get It |
|-------|--------------|---------------|
| **Active** | CHECK (must be checked) | Enables webhook delivery |
| **Webhook URL** | `https://example.com/webhooks/github` | Placeholder — you'll update this after deploying to Railway |
| **Webhook Secret** | Paste the output of `openssl rand -hex 32` | Run this in your terminal, save the output, you'll need it for `.env` |

**Repository Permissions (expand this section):**

| Permission | Access Level | Why We Need It |
|------------|-------------|----------------|
| **Contents** | **Read-only** | To fetch PR diffs (the code changes) via GitHub API |
| **Issues** | **Read & write** | To post the summary comment on the PR |
| **Metadata** | **Read-only** | Mandatory for all GitHub Apps — repo info |
| **Pull requests** | **Read & write** | To post inline review comments + read PR details |

**Organization permissions:** Leave all as "No access"

**Account permissions:** Leave all as "No access"

**Subscribe to events (checkboxes appear AFTER you set permissions above):**

| Event | CHECK? | Why |
|-------|--------|-----|
| **Pull request** | YES | Triggers when a PR is opened, updated (synchronize), or reopened |
| **Pull request review** | YES | Triggers when a senior dev submits a review with "changes requested" |

Everything else: UNCHECK

**Where can this GitHub App be installed?**

| Option | Select? | Why |
|--------|---------|-----|
| **Only on this account** | YES (for now) | Start with your own repos, expand later |
| **Any account** | Later | Select this when you want others to install your bot |

Click **"Create GitHub App"**

**After creation — 3 things to do:**

1. **Note your App ID** — it's shown at the top of the app's settings page (a number like `123456`)
2. **Generate a private key:**
   - Scroll down to "Private keys" section
   - Click **"Generate a private key"**
   - A `.pem` file downloads automatically
   - Encode it for your `.env`:
     ```bash
     cat ~/Downloads/ai-code-review-bot.*.private-key.pem | base64 | tr -d '\n'
     ```
   - Save this long string — it's your `GITHUB_APP_PRIVATE_KEY`
3. **Install the app on your repos:**
   - Go to the left sidebar → **"Install App"**
   - Click **"Install"** next to your account
   - Select **"All repositories"** or pick specific ones
   - Click **"Install"**

---

### Step 3 — Create Supabase Database (Detailed Steps)

**3.1 — Create Account & Project:**
1. Go to [supabase.com](https://supabase.com) → click **"Start your project"**
2. Sign in with your **GitHub account** (easiest)
3. Click **"New Project"**
4. Fill in:
   - **Organization**: Select your default org (or create one)
   - **Project name**: `reviewbot`
   - **Database Password**: Create a STRONG password (save it somewhere safe — you need it for the connection string)
   - **Region**: Choose the closest to you (e.g., `East US (Virginia)` or `Southeast Asia (Singapore)`)
   - **Pricing Plan**: Free
5. Click **"Create new project"** — wait 2 minutes for provisioning

**3.2 — Get Your Connection String:**
1. In your Supabase project dashboard, click the **gear icon** (Project Settings) in the left sidebar
2. Click **"Database"** in the settings menu
3. Scroll to **"Connection string"** section
4. Select the **"URI"** tab
5. You'll see something like:
   ```
   postgresql://postgres.[PROJECT-REF]:[YOUR-PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres
   ```
6. **IMPORTANT**: For our async SQLAlchemy, change `postgresql://` to `postgresql+asyncpg://`:
   ```
   postgresql+asyncpg://postgres.[PROJECT-REF]:[YOUR-PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres
   ```
7. Replace `[YOUR-PASSWORD]` with the database password you set in step 4
8. This is your `DATABASE_URL`

**Why Supabase?** Free PostgreSQL with 500MB storage, no credit card needed, auto-backups, and a nice dashboard to inspect your data.

---

### Step 4 — Create Upstash Redis (Detailed Steps)

**4.1 — Create Account & Database:**
1. Go to [upstash.com](https://upstash.com) → click **"Start for Free"**
2. Sign in with your **GitHub account**
3. On the console, click **"Create Database"**
4. Fill in:
   - **Name**: `reviewbot-redis`
   - **Type**: Regional
   - **Region**: Choose closest to your Supabase region (for lowest latency)
   - **TLS (SSL)**: Enabled (default)
5. Click **"Create"**

**4.2 — Get Your Redis URL:**
1. On the database details page, you'll see the **"REST API"** section at top
2. Scroll down to find **"Redis URL"** or click the **"Details"** tab
3. Look for the connection string that looks like:
   ```
   rediss://default:AbCdEf123456@us1-xxxxx-xxxxx.upstash.io:6379
   ```
   (Note: `rediss://` with double-s means TLS is enabled — this is correct)
4. Click the **copy** button
5. This is your `REDIS_URL`

**Why Upstash?** Free Redis with 10,000 commands/day, TLS encryption, works as both Celery broker (task queue) and pub/sub (real-time notifications).

---

### Step 5 — Get Anthropic API Key

1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Sign up / log in
3. Go to **"API Keys"** in the sidebar
4. Click **"Create Key"**
5. Name it: `review-bot`
6. Copy the key (starts with `sk-ant-...`)
7. This is your `ANTHROPIC_API_KEY`

**Why Claude?** Best code understanding of any model, supports structured JSON output reliably, handles large diffs (200K token context), and our 4 agents can make parallel API calls.

---

### Step 6 — Configure Environment Variables

```bash
cd AI_Code_Review_Bot
cp .env.example .env
```

Edit `.env` and fill in everything:

```bash
# --- GitHub App (from Step 2) ---
GITHUB_APP_ID=123456                      # The number from your app's settings page
GITHUB_APP_PRIVATE_KEY=LS0tLS1CRUdJT...   # The base64-encoded PEM (very long string)
GITHUB_WEBHOOK_SECRET=a1b2c3d4e5f6...     # Output of: openssl rand -hex 32

# --- Anthropic (from Step 5) ---
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx      # Your Claude API key
MODEL_NAME=claude-haiku-4-5-20251001      # Cheaper model (or claude-sonnet-4-6 for higher quality)

# --- Database (from Step 3) ---
DATABASE_URL=postgresql+asyncpg://postgres.abcdef:[PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres

# --- Redis (from Step 4) ---
REDIS_URL=rediss://default:AbCdEf@us1-xxxxx.upstash.io:6379

# --- App URLs (update after deploy) ---
API_BASE_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000
```

---

### Step 7 — Run Locally

You need **4 terminal windows**:

**Terminal 1 — Database & Redis (skip if using Supabase + Upstash):**
```bash
cd AI_Code_Review_Bot
docker compose up -d postgres redis
```

**Terminal 2 — Backend API:**
```bash
cd AI_Code_Review_Bot/apps/api
python3 -m venv venv
source venv/bin/activate          # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

You should see:
```
INFO     Creating database tables …
INFO     AI Code Review Bot ready
INFO     Uvicorn running on http://0.0.0.0:8000
```

Verify: Open **http://localhost:8000/health** — should show `{"status": "healthy", "checks": {"api": "ok", "redis": "ok", "database": "ok"}}`

**Terminal 3 — Celery Worker:**
```bash
cd AI_Code_Review_Bot/apps/api
source venv/bin/activate
celery -A core.celery_app worker -Q high,default -c 4 --loglevel=info
```

You should see:
```
[config]
.> app:         reviewbot
.> transport:   redis://...
.> concurrency: 4 (prefork)
.> task events: OFF
[queues]
.> default    exchange=default(direct) key=default
.> high       exchange=high(direct) key=high
```

**Terminal 4 — Frontend Dashboard:**
```bash
cd AI_Code_Review_Bot/apps/dashboard
npm install
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
npm run dev
```

You should see:
```
▲ Next.js 15.x
- Local: http://localhost:3000
```

Open **http://localhost:3000** — you'll see the empty dashboard (no reviews yet — that's correct).

---

### Step 8 — Test Locally with ngrok

GitHub needs a public HTTPS URL to deliver webhooks to your local machine:

```bash
# Install ngrok (if not installed)
brew install ngrok       # macOS
# OR: npm install -g ngrok

# Create free ngrok account at ngrok.com and authenticate
ngrok config add-authtoken YOUR_TOKEN

# Expose your local FastAPI server
ngrok http 8000
```

ngrok will show a URL like:
```
Forwarding    https://abc123.ngrok-free.app -> http://localhost:8000
```

**Now update your GitHub App:**
1. Go to [github.com/settings/apps](https://github.com/settings/apps)
2. Click your **AI Code Review Bot**
3. Change **Webhook URL** to: `https://abc123.ngrok-free.app/webhooks/github`
4. Click **Save changes**

**Trigger a test:**
1. Go to any repo where the app is installed
2. Create a new branch, make a code change, open a Pull Request
3. Watch your terminals — you should see:
   - Terminal 2 (API): `Queued review for owner/repo#1`
   - Terminal 3 (Worker): Agent execution logs, then `Review completed for owner/repo#1`
4. Check the PR on GitHub — inline comments + summary should appear
5. Check http://localhost:3000 — the review should appear in the dashboard

---

### Step 9 — Deploy to Production

**9.1 — Backend on Railway:**

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Initialize project (from AI_Code_Review_Bot directory)
cd AI_Code_Review_Bot
railway init

# Set all environment variables
railway variables set GITHUB_APP_ID=123456
railway variables set GITHUB_APP_PRIVATE_KEY="LS0tLS1CR..."
railway variables set GITHUB_WEBHOOK_SECRET="a1b2c3..."
railway variables set ANTHROPIC_API_KEY="sk-ant-..."
railway variables set DATABASE_URL="postgresql+asyncpg://..."
railway variables set REDIS_URL="rediss://..."
railway variables set FRONTEND_URL="https://your-dashboard.netlify.app"

# Deploy
railway up
```

Railway reads the `Procfile` and runs:
- `web`: FastAPI server (receives webhooks from GitHub)
- `worker`: Celery worker (runs the AI agents in the background)

After deploy, Railway gives you a URL like `https://reviewbot-production.up.railway.app`

**9.2 — Frontend on Netlify:**

Option A — CLI:
```bash
cd AI_Code_Review_Bot/apps/dashboard
npm run build
npx netlify-cli deploy --prod --dir=.next
```

Option B — Git connect (recommended):
1. Go to [app.netlify.com](https://app.netlify.com) → **"Add new site"** → **"Import from Git"**
2. Connect your GitHub repo
3. Configure:
   - **Base directory**: `AI_Code_Review_Bot/apps/dashboard`
   - **Build command**: `npm run build`
   - **Publish directory**: `.next`
4. Add environment variable: `NEXT_PUBLIC_API_URL` = `https://reviewbot-production.up.railway.app`
5. Click **"Deploy site"**

---

### Step 10 — Update GitHub App Webhook URL (Final Step)

1. Go to [github.com/settings/apps](https://github.com/settings/apps)
2. Click your **AI Code Review Bot**
3. Change **Webhook URL** to your Railway URL:
   ```
   https://reviewbot-production.up.railway.app/webhooks/github
   ```
4. Click **Save changes**

Now every PR on your installed repos will be automatically reviewed.

---

### Step 11 — Verify End-to-End

1. Open a PR on any repo where the app is installed
2. Wait 30-60 seconds
3. Check the PR — you should see:
   - A summary comment from "AI Code Review Bot"
   - Inline comments on specific lines with fix prompts
4. Check your Netlify dashboard — the review appears with all issues
5. Click into a review — see per-agent findings, click "Copy" on fix prompts
6. Paste the fix prompt into Claude — it should generate the exact fix

---

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/webhooks/github` | GitHub webhook (HMAC + idempotency + Celery queue) |
| `GET` | `/reviews/stats` | Dashboard stats (total reviews, issues by severity, cost) |
| `GET` | `/reviews` | Paginated review list with filters |
| `GET` | `/reviews/{id}` | Review detail with all issues + senior feedback |
| `GET` | `/prompts` | Searchable fix prompts library (filter by agent, severity) |
| `POST` | `/prompts/{id}/feedback` | Rate a prompt helpful / not helpful |
| `GET` | `/notifications/stream` | SSE real-time notification stream |
| `GET` | `/notifications` | List notifications (paginated) |
| `PATCH` | `/notifications/{id}/read` | Mark one notification as read |
| `POST` | `/notifications/mark-all-read` | Mark all as read |
| `GET` | `/health` | Health check (API + DB + Redis connectivity) |
| `GET` | `/docs` | Auto-generated Swagger API documentation |

---

## How It Works (Complete Flow)

```
1. Developer opens a PR
      ↓
2. GitHub fires webhook → POST /webhooks/github
      ↓
3. FastAPI verifies HMAC-SHA256 signature (is this really from GitHub?)
      ↓
4. Redis idempotency check (X-GitHub-Delivery header, 24h TTL)
      ↓
5. Celery queues the job on "high" priority queue → returns 200 immediately
      ↓
6. Worker picks up the task:
   a. Gets installation token (GitHub App JWT → short-lived token)
   b. Fetches the PR diff via GitHub API
   c. Creates Review record in PostgreSQL (status: "running")
      ↓
7. Builds pr_context: { title, repo, author, files_changed, additions, deletions }
      ↓
8. asyncio.gather() runs 4 agents IN PARALLEL:
   - Each agent receives: diff + pr_context
   - Each agent calls Claude API with specialized system prompt
   - Each agent returns: { issues[], summary }
      ↓
9. Aggregator Agent receives all 4 outputs:
   - De-duplicates (same issue found by multiple agents → keep one)
   - Ranks by severity: critical → high → medium → low
   - Generates markdown summary for GitHub
   - Generates a fix_prompt for EVERY issue
      ↓
10. Posts to GitHub:
    - Summary comment on the PR (markdown with issue table)
    - Batch PR review with inline comments on specific lines
      ↓
11. Saves to PostgreSQL:
    - Review record (status: "completed", cost, tokens, counts)
    - Issue records (one per finding, with fix_prompt)
      ↓
12. Redis Pub/Sub → SSE → Dashboard notification appears in real-time
      ↓
13. (Later) Senior dev reviews PR → requests changes
      ↓
14. Webhook fires pull_request_review event
      ↓
15. Senior Comment Agent:
    - Reads the senior's comment + code context
    - Generates: explanation (WHY) + best practice + fix prompt + step-by-step guidance
    - Saves to DB + sends notification
```

---

## Claude Agentic Workflow Patterns Used

| Pattern | Where Used | What It Does |
|---------|-----------|--------------|
| **Parallel Agent Execution** | `review_orchestrator.py` | `asyncio.gather` runs 4 Claude calls simultaneously — 4x faster than sequential |
| **Role Prompting** | Each agent's system prompt | "You are a senior frontend code reviewer specializing in..." — constrains the model to its domain |
| **Structured Output (JSON)** | All agents | Strict JSON schema in system prompt ensures parseable, consistent output |
| **PR Context Injection** | `base_agent.py` | Every agent receives title, repo, author, files_changed — makes reviews context-aware |
| **Fix Prompt Generation** | Aggregator + all agents | Meta-prompting: AI generates prompts that a dev can paste into another AI to get the fix |
| **Error Isolation** | `return_exceptions=True` | One agent failing doesn't kill the entire review — others continue |
| **Webhook → Queue → Agent** | webhooks.py → Celery → orchestrator | Production event-driven architecture: instant ACK, async processing |
| **Idempotency** | webhooks.py + Redis | `X-GitHub-Delivery` header prevents duplicate processing if GitHub retries |
| **Retry with Backoff** | Celery tasks | `autoretry_for=(Exception,), retry_backoff=True` — exponential retry on failure |
| **Cost Tracking** | base_agent + aggregator | Tracks input/output tokens per agent, computes USD cost per review |

---

## Environment-Specific Configs

| Setting | Local Dev | Production |
|---------|-----------|------------|
| Webhook URL | ngrok tunnel | Railway HTTPS URL |
| Database | Local Docker postgres OR Supabase | Supabase |
| Redis | Local Docker redis OR Upstash | Upstash |
| Celery workers | 1 (for debugging) | 2-4 (for concurrency) |
| Log level | DEBUG | INFO |
| Claude model | claude-haiku-4-5 (cheaper for testing) | claude-haiku-4-5 or claude-sonnet-4-6 (higher quality) |

---

## Production Hardening Checklist

- [x] HMAC-SHA256 webhook signature verification on every request
- [x] Idempotency check with Redis (X-GitHub-Delivery header, 24h TTL)
- [x] Return 200 to GitHub within 200ms, process async via Celery
- [x] Celery autoretry with exponential backoff (3 retries)
- [x] `apply_async(queue="high")` for priority processing
- [x] Batch PR review API for inline comments (one API call, not N calls)
- [x] Database indexes on severity, notifications (is_read + created_at), reviews
- [x] Unique constraint on (repo_id, pr_number) to prevent duplicate PRs
- [x] Secrets in environment variables — never in code
- [x] Private key base64-encoded in env, decoded at runtime
- [x] Structured logging (not print statements)
- [x] Health check endpoint (`/health`) verifying DB + Redis connectivity
- [x] Prompt feedback tracking (helpful/not helpful) for continuous improvement
- [x] Cost tracking per review (input/output tokens + USD)
- [x] SSE reconnect with 5-second retry on connection loss
- [x] Notifications loaded from REST on mount + live via SSE
- [x] Safe markdown rendering (no raw HTML injection)
- [x] docker-compose.prod.yml with 2 worker replicas
# Github_Workflow_Automation
