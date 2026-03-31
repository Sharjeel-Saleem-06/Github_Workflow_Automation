# AI Code Review Bot — Complete Running Guide

Everything you need to know: how to run, how it works, what the Claude workflow is, and how to optimize it.

---

## Table of Contents

1. [Quick Start (5 commands)](#1-quick-start)
2. [What Each Service Does](#2-what-each-service-does)
3. [How to Run Locally (Step by Step)](#3-how-to-run-locally)
4. [How to Deploy for 24/7 Auto-Review](#4-deploy-for-247)
5. [The Claude Agentic Workflow Explained](#5-claude-agentic-workflow)
6. [What Happens When a PR Is Opened](#6-what-happens-on-pr)
7. [All 5 Agents Deep Dive](#7-agents-deep-dive)
8. [How to Test It Right Now](#8-test-it-now)
9. [Optimization Guide](#9-optimization)
10. [Common Issues & Fixes](#10-troubleshooting)

---

## 1. Quick Start

```bash
# Terminal 1 — API server
cd AI_Code_Review_Bot/apps/api
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000

# Terminal 2 — Celery worker (processes reviews)
cd AI_Code_Review_Bot/apps/api
source venv/bin/activate
celery -A core.celery_app worker --loglevel=info --concurrency=2 -Q default,high

# Terminal 3 — Ngrok tunnel (exposes localhost to GitHub)
/tmp/ngrok http 8000

# Terminal 4 — Dashboard (optional, for stats)
cd AI_Code_Review_Bot/apps/dashboard
npm run dev

# Terminal 5 — Verify everything works
curl http://localhost:8000/health
```

After starting all 4 services:
1. Copy the ngrok HTTPS URL (e.g. `https://xyz.ngrok-free.app`)
2. Go to GitHub → Settings → Developer settings → GitHub Apps → AI Code Review Bot
3. Set Webhook URL to: `https://xyz.ngrok-free.app/webhooks/github`
4. Open a PR on any repo where the app is installed
5. Wait 30-60 seconds — inline comments appear automatically

---

## 2. What Each Service Does

| Service | Port | Purpose | Required? |
|---------|------|---------|-----------|
| **FastAPI API** | 8000 | Receives GitHub webhooks, serves REST API for dashboard | Yes |
| **Celery Worker** | — | Background processing: runs AI agents, posts GitHub comments | Yes |
| **Ngrok** | 4040 (inspector) | Tunnels GitHub webhooks to your localhost (only for local dev) | Only locally |
| **Next.js Dashboard** | 3000 | Web UI for review history, stats, fix prompts | Optional |
| **Supabase** | — | PostgreSQL database (cloud, always running) | Yes (already running) |
| **Upstash** | — | Redis (cloud, always running) | Yes (already running) |

**Key point:** Supabase and Upstash are cloud services — they are always running. You only need to start the API, Celery worker, and ngrok locally.

---

## 3. How to Run Locally (Detailed)

### Prerequisites

- Python 3.11+ with `venv` activated
- Node.js 18+ (for dashboard)
- All environment variables set in `.env` (already done)
- GitHub App installed on at least one repo (already done)

### Step 1: Start the API

```bash
cd AI_Code_Review_Bot/apps/api
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

- `--reload` auto-restarts on code changes (dev only)
- Verify: `curl http://localhost:8000/health` should return `{"status":"healthy","checks":{"api":"ok","redis":"ok","database":"ok"}}`

### Step 2: Start the Celery Worker

```bash
cd AI_Code_Review_Bot/apps/api
source venv/bin/activate
celery -A core.celery_app worker --loglevel=info --concurrency=2 -Q default,high
```

- `--concurrency=2` means 2 reviews can process simultaneously
- `-Q default,high` listens on both queues (PR reviews go to `high`)
- You'll see `celery@... ready.` when it's working

### Step 3: Start Ngrok

```bash
/tmp/ngrok http 8000
```

- Copy the `Forwarding` HTTPS URL
- Update your GitHub App's Webhook URL to this URL + `/webhooks/github`
- Example: `https://abc123.ngrok-free.app/webhooks/github`

**Important:** Every time you restart ngrok, you get a NEW URL. You must update the GitHub App webhook URL each time.

### Step 4: Start Dashboard (Optional)

```bash
cd AI_Code_Review_Bot/apps/dashboard
npm run dev
```

- Opens at `http://localhost:3000`
- Shows review history, stats, fix prompts library

### Step 5: Test It

Open a new PR (or push a commit to an existing PR) on a repo where the GitHub App is installed. Within 30-60 seconds, you'll see:
- A summary comment on the PR
- Inline comments on specific lines in "Files changed" tab
- Each comment has a severity emoji and a collapsible fix prompt

---

## 4. Deploy for 24/7 Auto-Review (No Laptop Needed)

To make the bot fully autonomous and always-on:

### Option A: Railway (Recommended)

| Service | Railway Plan | What |
|---------|-------------|------|
| FastAPI API | Web service | Runs `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| Celery Worker | Worker service | Runs `celery -A core.celery_app worker ...` |

Steps:
1. Push `apps/api/` to a GitHub repo
2. Create a Railway project → New Service → Deploy from GitHub
3. Set all env vars from `.env` in Railway's Variables tab
4. Railway gives you a permanent URL like `https://your-app.up.railway.app`
5. Update GitHub App Webhook URL to `https://your-app.up.railway.app/webhooks/github`
6. **Done** — the bot reviews every PR automatically, 24/7

### Option B: Docker Compose (Self-hosted)

```bash
cd AI_Code_Review_Bot
docker-compose up -d
```

This starts API + Worker + local Redis + local Postgres in containers.

### After deploying:
- Supabase (database) — already running in the cloud
- Upstash (Redis) — already running in the cloud
- Netlify (dashboard docs) — already deployed at https://melodic-queijadas-7520ef.netlify.app
- You no longer need ngrok — Railway gives a permanent URL

---

## 5. The Claude Agentic Workflow — Is This a Proper Claude Workflow?

### Yes, this is an agentic Claude workflow. Here's exactly why:

**What makes something "agentic":**
An agentic AI system makes autonomous decisions, takes actions, and chains multiple steps to complete a goal — not just answering a single question.

**Our bot's agentic pipeline:**

```
GitHub Webhook (trigger)
    │
    ▼
FastAPI receives → verifies HMAC → checks idempotency → queues task
    │
    ▼
Celery Worker picks up task
    │
    ▼
GitHub Auth: Generate JWT → Exchange for Installation Token
    │
    ▼
Fetch PR Diff from GitHub API
    │
    ▼
┌──────────────────────────────────────────────┐
│        asyncio.gather (PARALLEL)             │
│                                              │
│  Agent 1: Color & Constants                  │
│    └─ Claude call with specialized prompt     │
│    └─ Returns structured JSON                │
│                                              │
│  Agent 2: Logic & Bugs                       │
│    └─ Claude call with specialized prompt     │
│    └─ Returns structured JSON                │
│                                              │
│  Agent 3: Best Practices                     │
│    └─ Claude call with specialized prompt     │
│    └─ Returns structured JSON                │
│                                              │
│  Agent 4: Security                           │
│    └─ Claude call with specialized prompt     │
│    └─ Returns structured JSON                │
│                                              │
└──────────────────────────────────────────────┘
    │
    ▼
Aggregator Agent (5th Claude call)
    └─ Merges all 4 outputs
    └─ Deduplicates same-line issues
    └─ Ranks by severity (critical → high → medium → low)
    └─ Generates fix prompts for every issue
    └─ Produces final markdown summary
    │
    ▼
Post to GitHub:
    1. Summary comment on the PR
    2. Batch inline review comments on specific lines
    │
    ▼
Save to PostgreSQL:
    └─ Review record, issues, costs, tokens
    │
    ▼
Redis Pub/Sub → SSE → Dashboard notification
```

### How to explain this in an interview:

> "I built a production GitHub App that implements an agentic Claude workflow. When a PR is opened, GitHub sends a signed webhook. My FastAPI backend verifies the HMAC signature, deduplicates deliveries using Redis, and queues a Celery task. The worker fetches the PR diff and runs 4 specialist Claude agents in parallel using asyncio.gather — each with a focused system prompt for colors/constants, logic bugs, best practices, and security. A 5th aggregator agent merges all findings, deduplicates, ranks by severity, and generates actionable fix prompts. The results are posted as batch inline review comments on the PR using the GitHub API, and stored in PostgreSQL for the dashboard."

### What makes it "agentic" vs just "calling an API":

| Aspect | Simple API Call | Our Agentic Workflow |
|--------|----------------|---------------------|
| Decision making | None — human triggers | Autonomous — triggered by webhook |
| Number of steps | 1 API call | 8+ chained steps |
| Parallelism | Sequential | 4 agents run concurrently |
| Error handling | Crash | Retry with backoff, graceful fallback |
| Output | Raw text | Structured JSON → mapped to GitHub API |
| State | Stateless | Persisted in PostgreSQL + Redis |
| Real-time | Pull only | Push via SSE |

---

## 6. What Happens When a PR Is Opened (Detailed)

1. **Developer opens PR** on a repo where the GitHub App is installed
2. **GitHub fires** `pull_request.opened` webhook to our URL
3. **FastAPI receives** the POST at `/webhooks/github`
4. **HMAC verification** — computes SHA256 hash and compares with `X-Hub-Signature-256`
5. **Idempotency check** — looks up `X-GitHub-Delivery` in Redis; skips if already processed
6. **Returns HTTP 200** immediately (GitHub expects a response within 10 seconds)
7. **Queues Celery task** `process_pr_review` with PR metadata on the `high` queue
8. **Celery worker** picks up the task from Redis
9. **JWT generation** — creates a GitHub App JWT signed with the private key
10. **Token exchange** — JWT → installation access token (valid 1 hour)
11. **Fetches PR diff** — calls GitHub API with `Accept: application/vnd.github.diff`
12. **Runs 4 agents in parallel** — each makes an async Claude API call with its system prompt
13. **Aggregator merges** — 5th Claude call that deduplicates, ranks, generates fix prompts
14. **Posts summary comment** — `POST /repos/{owner}/{repo}/issues/{pr}/comments`
15. **Posts batch inline review** — `POST /repos/{owner}/{repo}/pulls/{pr}/reviews` with inline comments array
16. **Saves to database** — review record, individual issues, token costs
17. **Redis pub/sub** — publishes notification event
18. **Dashboard SSE** — connected clients get real-time update

**Total time:** 30-60 seconds (mostly waiting for 5 Claude API calls)

---

## 7. All 5 Agents Deep Dive

### Agent 1: Color & Constants

**System prompt role:** Senior frontend code reviewer specializing in design system consistency.

**Detects:**
- Hardcoded hex colors (`#FF5733`, `rgb(255,87,51)`) instead of design tokens
- Magic numbers (`padding: 16`, `fontSize: 14`) instead of constants
- Design system violations
- Inline styles overriding theme variables
- Inconsistent naming in color constants

**Output categories:** `hardcoded-color`, `magic-number`, `design-system-violation`, `inline-style`, `naming`

### Agent 2: Logic & Bugs

**System prompt role:** Senior software engineer specializing in logic error detection.

**Detects:**
- Logic errors (always-true/false conditions, off-by-one)
- Null/undefined handling (missing nil checks, optional chaining)
- Async/await issues (missing await, race conditions)
- State management bugs (stale state, mutation)
- Type mismatches
- Edge cases (empty arrays, zero/negative numbers)

**Output categories:** `logic-error`, `null-handling`, `async-issue`, `state-bug`, `type-mismatch`, `edge-case`

### Agent 3: Best Practices

**System prompt role:** Senior engineer enforcing clean code and SOLID principles.

**Detects:**
- Naming conventions (unclear variable/function names)
- Function complexity (should be decomposed)
- Duplication (copy-pasted logic)
- Component structure violations (SRP)
- Import organization issues
- Missing documentation for complex functions
- Missing error handling (no try-catch, swallowed errors)
- Performance issues (unnecessary re-renders, missing memoization)

**Output categories:** `naming`, `complexity`, `duplication`, `component-structure`, `imports`, `documentation`, `error-handling`, `performance`

### Agent 4: Security

**System prompt role:** Security-focused senior engineer doing code review.

**Detects:**
- Exposed secrets (API keys, tokens, passwords in code)
- XSS vulnerabilities (`dangerouslySetInnerHTML`, unescaped input)
- Sensitive data logging (logging PII, tokens)
- Insecure dependencies
- Auth/AuthZ issues (missing checks, privilege escalation)
- Injection risks (SQL injection, command injection)
- Insecure defaults (disabled headers, open CORS)
- Anti-patterns (`eval()`, `document.write()`)

**Output categories:** `exposed-secret`, `xss`, `sensitive-logging`, `insecure-dependency`, `auth-issue`, `injection`, `insecure-default`, `anti-pattern`

### Agent 5: Aggregator

**System prompt role:** Lead Staff Engineer writing the final PR review.

**Does:**
- Merges all 4 agent outputs into one unified review
- Deduplicates (if 2 agents flagged the same line)
- Groups by severity: Critical → High → Medium → Low
- Generates a markdown summary with issue counts per agent
- Creates a `fix_prompt` for every single issue
- Assigns verdict: `CHANGES_REQUESTED` or `APPROVED`

---

## 8. How to Test It Right Now

### Option A: Open a fresh PR

1. Go to any repo where the app is installed (e.g. `BaatCheet_IOS`)
2. Create a new branch, make some changes (introduce a hardcoded color or skip error handling)
3. Open a PR
4. Wait 30-60 seconds
5. Check the PR — summary comment + inline comments appear

### Option B: Push to an existing PR

1. Go to an existing open PR
2. Push a new commit (any code change)
3. The `synchronize` event triggers a new review

### Option C: Manually trigger (for testing without a real PR event)

```bash
cd AI_Code_Review_Bot/apps/api
source venv/bin/activate
python3 -c "
from tasks.review_tasks import process_pr_review
result = process_pr_review.apply_async(
    args=[{
        'installation_id': 120431684,
        'owner': 'Sharjeel-Saleem-06',
        'repo': 'BaatCheet_IOS',
        'repo_id': 0,
        'pr_number': 1,
        'pr_title': 'Test PR',
        'pr_author': 'Sharjeel-Saleem-06',
        'head_sha': 'HEAD_SHA_HERE',
        'files_changed': 0,
        'additions': 0,
        'deletions': 0,
    }],
    queue='high',
)
print(f'Task queued: {result.id}')
"
```

Replace `HEAD_SHA_HERE` with the actual latest commit SHA from the PR.

---

## 9. Optimization Guide

### Current Setup

| Setting | Current Value | What It Means |
|---------|--------------|---------------|
| Model | `claude-haiku-4-5-20251001` | Fastest/cheapest Claude model |
| Agent max tokens | 4096 | Max output per specialist agent |
| Aggregator max tokens | 8192 | Max output for the merger |
| Concurrency | 2 | 2 reviews at the same time |

### How to Optimize

#### 1. Switch to a Smarter Model (Better Reviews, Higher Cost)

In `.env`, change:
```
MODEL_NAME=claude-sonnet-4-20250514
```

| Model | Quality | Cost per review (~500 line diff) |
|-------|---------|--------------------------------|
| claude-haiku-4-5-20251001 | Good | ~$0.01-0.03 |
| claude-sonnet-4-20250514 | Better | ~$0.05-0.15 |

**Recommendation:** Use Haiku for daily reviews, Sonnet for critical repos.

#### 2. Add More Agents

Create a new file like `apps/api/agents/performance.py`:

```python
from .base_agent import BaseAgent

SYSTEM_PROMPT = """You are a performance engineering specialist.
Your ONLY job: detect performance issues in the diff:
1. N+1 queries
2. Missing database indexes
3. Unnecessary re-renders in React
4. Large bundle imports that should be lazy-loaded
5. Memory leaks (event listeners not cleaned up)
6. Synchronous blocking calls in async context

Output only JSON... (same schema as other agents)
"""

class PerformanceAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="performance", system_prompt=SYSTEM_PROMPT)
```

Then add it to `agents/__init__.py` and `review_orchestrator.py`.

#### 3. Language-Specific Agents

You can create agents tailored to specific languages:
- **SwiftAgent** for iOS-specific patterns (retain cycles, force unwraps, missing `@MainActor`)
- **KotlinAgent** for Android patterns (coroutine leaks, nullable handling)
- **TypeScriptAgent** for strict type checking, `any` usage

#### 4. Increase Concurrency

```bash
celery -A core.celery_app worker --concurrency=4 -Q default,high
```

#### 5. Add Caching

Skip reviews if the diff is identical to a previously reviewed one:
- Hash the diff → check Redis → skip if already reviewed with same hash
- Saves Claude API costs on force-pushes that don't change code

#### 6. Diff Size Limits

For very large PRs (1000+ lines), you can:
- Split the diff into chunks and review each chunk separately
- Or skip review and post a comment saying "PR too large for automated review"

#### 7. Selective Agent Routing

Not every PR needs all 4 agents:
- If only `.md` files changed → skip all agents (documentation only)
- If only `.css`/`.scss` changed → only run Color & Constants
- If only tests changed → only run Logic & Bugs

Add this logic in `review_orchestrator.py` before running agents.

#### 8. Webhook Filtering

In the GitHub App settings, you can also filter which events trigger the webhook — but the current setup (PR opened/sync/reopened) is already optimal.

---

## 10. Common Issues & Fixes

| Problem | Cause | Fix |
|---------|-------|-----|
| No comments appear | Ngrok URL expired or changed | Restart ngrok, update webhook URL in GitHub App |
| "Invalid signature" in logs | Webhook secret mismatch | Ensure `GITHUB_WEBHOOK_SECRET` in `.env` matches GitHub App settings |
| "already_processed" response | Duplicate webhook delivery | Normal — idempotency working correctly. Clear Redis key if you want to re-process |
| Celery worker not processing | Worker not running or wrong queue | Start with `-Q default,high` |
| "Could not parse public key" | Corrupted private key in `.env` | Re-encode the PEM: `cat key.pem \| base64 \| tr -d '\n'` and update `.env` |
| Dashboard shows no data | API URL mismatch | Set `NEXT_PUBLIC_API_URL=http://localhost:8000` in dashboard `.env.local` |
| Review takes > 2 minutes | Large diff or slow Claude response | Check diff size; consider model downgrade or diff chunking |
| Comments on wrong lines | Line numbers from diff don't match PR | Known GitHub API limitation; aggregator may post as issue comment instead |

---

## Summary: What You Can Say About This Project

> "I built a production-grade agentic AI system — a GitHub App that autonomously reviews every pull request. It uses 4 specialized Claude agents running in parallel (color/constants, logic/bugs, best practices, security), merged by a 5th aggregator agent. The system is event-driven via GitHub webhooks, processes reviews asynchronously with Celery, stores results in PostgreSQL, and streams real-time notifications to a Next.js dashboard. Each review produces inline comments with fix prompts that developers can paste into any AI assistant. The whole pipeline — from webhook receipt to posted comments — runs in under 60 seconds with no human intervention."

This is a **proper Claude agentic workflow** because:
- It's **autonomous** (triggered by events, no human in the loop)
- It uses **multiple specialized agents** with different system prompts
- Agents run in **parallel** (not sequential)
- Results are **aggregated and ranked** by a coordinator agent
- Output is **structured JSON** mapped to real-world actions (GitHub API calls)
- The system has **state** (PostgreSQL), **messaging** (Redis/Celery), and **real-time push** (SSE)
- It handles **errors gracefully** with retries and fallbacks
