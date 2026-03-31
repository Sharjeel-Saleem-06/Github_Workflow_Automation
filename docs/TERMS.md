# Glossary — AI Code Review Bot

This glossary defines technical terms used across the AI Code Review Bot project. Each entry includes a short definition and how the concept applies **in this codebase**.

**Categories**

| Tag | Meaning |
|-----|---------|
| **GitHub & Webhooks** | GitHub App integration, PRs, diffs, and API usage |
| **AI & Agents** | Claude, agents, prompts, and structured outputs |
| **Infrastructure** | Backend services, queues, databases, deployment |
| **Frontend** | Dashboard and browser-facing features |
| **Code Quality Concepts** | What the reviewers look for in your code |

---

## GitHub & Webhooks

### **GitHub App**

*A first-party integration registered with GitHub that acts as its own bot identity and receives repository events.*

In this project, the GitHub App is the core identity of the reviewer: it is installed on orgs or repos, subscribes to pull request and pull request review events, and uses installation-scoped credentials (not a human user’s OAuth session) to read diffs and post reviews. The README documents why a GitHub App is preferred over an OAuth app for webhooks and fine-grained permissions.

---

### **Webhook**

*An HTTP callback GitHub sends to your server when something happens (for example, a PR is opened).*

The FastAPI route `POST /webhooks/github` receives these payloads. The handler validates the request, deduplicates deliveries, and enqueues Celery work so GitHub gets a quick `200` response while reviews run asynchronously.

---

### **HMAC-SHA256 Signature Verification**

*A way to prove a webhook body came from GitHub and was not tampered with, using a shared secret and a keyed hash.*

This project computes `sha256=` + HMAC of the raw body with `GITHUB_WEBHOOK_SECRET` and compares it to the `X-Hub-Signature-256` header using a constant-time comparison. If verification fails, the API returns `401` so forged or misconfigured requests cannot trigger reviews.

---

### **Installation Access Token vs Personal Access Token**

*An **installation access token** is short-lived and scoped to a specific app installation on a repo/org. A **personal access token (PAT)** is tied to a user account and often has broad, long-lived access.*

Here, `github_auth.py` exchanges a GitHub App JWT for an **installation access token** per `installation_id`; `GitHubClient` uses that token for all API calls. The project does **not** rely on PATs for production bot behavior, which keeps access bounded to installed repositories and aligns with GitHub’s recommended App model.

---

### **JWT (JSON Web Token) — how GitHub Apps use it**

*A signed JSON object (often used for auth) that proves identity without sending a password on every request.*

For GitHub Apps, this project generates a short-lived JWT with RS256 using the app’s private key (`GITHUB_APP_PRIVATE_KEY`) and `iss` set to `GITHUB_APP_ID`. That JWT is sent as a Bearer token to `POST /app/installations/{id}/access_tokens` to obtain a one-hour **installation access token** used for GitHub REST API calls.

---

### **Pull Request (PR)**

*A request to merge changes from one branch into another, usually with review and CI.*

Opening, updating (`synchronize`), or reopening a PR triggers the webhook flow. The bot records metadata (title, author, SHA, stats) and runs the multi-agent review pipeline against the PR’s diff.

---

### **PR Diff**

*The textual representation of what changed in a pull request—added/removed lines per file.*

Agents consume the PR diff (fetched via GitHub’s API with `Accept: application/vnd.github.diff`) as their main input. It is the ground truth for line-level comments and for what changed in the branch compared to the base.

---

### **Inline Review Comments**

*Comments attached to a specific line (and file) in a PR, visible in the “Files changed” view.*

The orchestrator maps agent findings to paths and lines; `GitHubClient.post_review_comment` can post a single inline comment, while batch posting uses the review endpoint for a cohesive review thread. Inline comments are where developers see issues and **fix prompts** next to the code.

---

### **Batch Review API**

*GitHub’s API to submit one **pull request review** that can include multiple inline comments and an overall review body in a single request.*

`post_pr_review_batch` calls `POST /repos/{owner}/{repo}/pulls/{pull_number}/reviews` with `event: COMMENT`, a summary body, and a `comments` array. That produces a single formal review on the PR instead of many disconnected issue comments—better UX and clearer for teams.

---

## AI & Agents

### **Claude AI / Anthropic**

*Claude is Anthropic’s family of large language models; the Anthropic API is how this app invokes them.*

All specialized agents and the aggregator use the Anthropic SDK with a configurable `MODEL_NAME` (default `claude-haiku-4-5-20251001` in settings). API keys are supplied via `ANTHROPIC_API_KEY`; token limits are split between agents and the aggregator for cost and quality control.

---

### **AI Agent (in the context of this project)**

*A focused LLM-powered module with a fixed role, system prompt, and expected JSON output shape.*

This repo defines agents such as Color & Constants, Logic & Bugs, Best Practices, and Security—each implemented as a class/module built on `base_agent.py`. Each agent receives the same PR context and diff but applies a different “lens” (e.g., OWASP vs. design tokens).

---

### **Multi-Agent System**

*Multiple independent agents collaborating on one task, often in parallel, with a merge or coordination step.*

Here, `review_orchestrator` runs several agents concurrently (e.g., via `asyncio.gather`), then the **Aggregator** merges outputs: deduplication, severity ranking, and a single GitHub-facing result. This splits expertise without one monolithic prompt trying to do everything.

---

### **Agentic Workflow**

*A process where LLM-driven steps (tool use, reasoning, subtasks) chain toward a goal—not just a single Q&A.*

The project’s workflow is agentic in the narrow sense: webhook → queue → token fetch → parallel analysis agents → aggregation → GitHub post → notifications. Each step has clear inputs/outputs; the “agents” are structured review stages rather than arbitrary tool loops.

---

### **Prompt Engineering**

*Designing system prompts, instructions, and output constraints so models behave reliably for a task.*

Each agent file encodes domain instructions (e.g., security checks aligned with OWASP, or naming/SRP rules). The aggregator prompt defines how to merge and phrase results. Good prompt engineering here means consistent JSON, fewer hallucinated line numbers, and actionable wording in comments.

---

### **Fix Prompt**

*A ready-to-paste natural-language instruction (often aimed at Claude or Copilot) that tells how to fix a specific finding.*

Every issue in structured output can include a `fix_prompt` field: concrete steps referencing file, line, and replacement. The dashboard’s **fix prompts library** surfaces these for search and feedback—developers copy them into their AI assistant to implement fixes faster.

---

### **Structured Output (JSON schema from agents)**

*Model responses constrained to parseable JSON matching a known shape (fields like `issues`, `severity`, `line`).*

Agents return objects with `issues[]` and `summary` (see README examples). That structure lets the orchestrator validate, dedupe, sort by **severity**, and map entries to GitHub API payloads without fragile free-text parsing.

---

## Infrastructure

### **Celery (task queue)**

*A distributed task queue for Python: producers enqueue jobs; workers execute them asynchronously.*

PR reviews and related work are queued with `process_pr_review.apply_async` on a `high` priority queue. Celery provides retries and backoff so transient GitHub or Redis failures do not lose work. The worker runs as a separate process (see `Procfile` / Docker Compose).

---

### **Redis (as broker, cache, pub/sub)**

*An in-memory data store used here as Celery’s message broker, for idempotency keys, and for pub/sub.*

Redis backs: (1) Celery transport, (2) webhook idempotency via `X-GitHub-Delivery` keys with TTL, and (3) publishing events consumed for real-time dashboard updates. Upstash-hosted Redis is supported for production (`rediss://`).

---

### **Idempotency (and why it matters for webhooks)**

*Processing the same logical event once even if it is delivered more than once.*

GitHub may retry webhooks; without idempotency, duplicate deliveries could enqueue duplicate reviews. This project stores a Redis key per `X-GitHub-Delivery` for 24 hours and short-circuits if already seen, keeping reviews one-per-delivery.

---

### **PostgreSQL / Supabase**

*PostgreSQL is a relational database; Supabase is a hosted platform that provides Postgres among other services.*

The app uses SQLAlchemy (async) with `DATABASE_URL`, typically `postgresql+asyncpg://…`. Supabase is the documented hosting choice for managed Postgres, backups, and a dashboard for inspecting review records—schema lives under `apps/api/models/` with Alembic migrations.

---

### **SSE (Server-Sent Events)**

*A browser mechanism where the server pushes a stream of events over a single long-lived HTTP connection (client reads; typical for one-way updates).*

The API exposes notification streaming (e.g., `/notifications/stream`) so the Next.js dashboard receives live updates without full WebSocket complexity. The README positions SSE plus Redis pub/sub as the real-time stack for “fire and forget” server→client pushes.

---

### **FastAPI**

*A modern Python web framework for building APIs with async support and automatic OpenAPI docs.*

`main.py` mounts routers for webhooks, reviews, prompts, and notifications. FastAPI keeps webhook handling fast (return after queueing) and exposes `/docs` for integration testing. Health checks verify DB and Redis connectivity.

---

### **Cost Tracking (token usage estimation)**

*Measuring or estimating how many tokens (and thus dollars) each LLM call consumes.*

`base_agent.py` integrates cost-related tracking so reviews can attribute usage per agent run. Dashboard stats (e.g., `/reviews/stats`) expose aggregates so teams can monitor spend and tune models or agent settings.

---

### **Ngrok (for local development tunneling)**

*A tool that exposes a local HTTP(S) port to a public URL—useful for webhooks that require internet-reachable HTTPS.*

GitHub cannot call `localhost`; during local dev, ngrok provides a URL you paste into the GitHub App’s webhook settings. The README’s setup section walks through this so `POST /webhooks/github` receives real events while the API runs on your machine.

---

### **Docker / Docker Compose**

*Docker packages apps into containers; Compose defines multi-container local stacks in YAML.*

`docker-compose.yml` orchestrates Postgres, Redis, API, worker, and dashboard for a one-command dev environment. `docker-compose.prod.yml` targets API/worker replicas for production-like testing. This standardizes dependencies without manual service installation.

---

## Frontend

### **Next.js Dashboard**

*The React-based web UI (Next.js App Router) that ships under `apps/dashboard`.*

It consumes REST APIs for reviews, stats, prompts, and notifications; `useNotifications` hooks SSE for live updates. Pages include overview, review detail, prompts library, and settings—giving leads and developers a central place to browse history and severity without reading GitHub alone.

---

## Code Quality Concepts

### **Severity Levels (critical, warning, info)**

*A coarse priority scale for findings so teams triage what to fix first.*

The aggregator ranks and filters issues using these levels so the GitHub summary and dashboard charts (e.g., issues by severity) reflect risk. Critical items might represent security or correctness; info might be style or minor consistency.

---

### **OWASP (in context of security agent)**

*The Open Web Application Security Project—widely referenced guidelines and top risks for web app security.*

The Security agent is framed to catch classes of issues aligned with OWASP-style thinking (injection, XSS, secrets in code, misconfigurations). It does not replace a full pentest but automates first-pass review for common vulnerabilities called out in OWASP materials.

---

### **Design Tokens**

*Named design-system values (colors, spacing, typography) used instead of raw literals so themes stay consistent.*

The Color & Constants agent flags hardcoded colors and missing tokens so UI code can align with a shared system—important for dark mode, branding, and maintainability.

---

### **Magic Numbers / Hardcoded Values**

*Unexplained numeric literals or fixed values in code (e.g., `padding: 16`) that should be named constants or tokens.*

This project explicitly calls these out as anti-patterns in the Color & Constants agent: magic numbers and hardcoded hex/RGB make refactors harder. Fix prompts often suggest replacing them with shared constants or design tokens.

---

### **SRP (Single Responsibility Principle)**

*A SOLID principle: each module or function should have one reason to change—one clear responsibility.*

The Best Practices agent uses SRP as a lens for overly large functions, mixed concerns, and tangled modules. Findings encourage splitting responsibilities to match how senior reviewers think about maintainability.

---
