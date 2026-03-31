# Usage Guide — AI Code Review Bot

This guide explains how the AI Code Review Bot works for different roles, how to share and demo it, how to install it on new repositories, and how to operate it in production. For terminology, see [TERMS.md](./TERMS.md).

---

## Section 1 — How It Works (simple explanation)

When you open a **pull request** on a connected repository, GitHub notifies our backend automatically—like ringing a doorbell. The service quickly acknowledges the request, then hands the heavy work to a background worker so GitHub does not have to wait.

In the background, several **AI agents** read the **diff** (what you changed) at the same time: one looks for design and constant issues, one for logic bugs, one for clean-code practices, and one for security. A lead **aggregator** merges their results, removes duplicates, and assigns **severity**. The bot then posts a proper **code review** on GitHub with **inline comments** on specific lines, plus short **fix prompts** you can paste into Claude or Copilot to implement changes quickly.

If a senior reviewer submits a “changes requested” review, a separate flow can turn that feedback into structured guidance. Your team can watch review activity, costs, and history on the **Next.js dashboard**, with optional **real-time notifications** streamed from the API.

---

## Section 2 — How to Use It

### For developers

1. **Open or update a PR** on a repository where the GitHub App is installed. The bot triggers on `opened`, `synchronize` (new commits), and `reopened`.
2. **Wait for the review**—inline comments appear on the “Files changed” tab as a batch review when processing completes.
3. **Read inline comments**—each points to a file and line with an explanation.
4. **Use fix prompts**—copy the suggested prompt into your AI assistant to generate a patch, then commit and push.
5. Optionally **rate prompts** from the dashboard prompts library so the team learns which guidance was helpful.

### For team leads

1. Open the **dashboard** (local `http://localhost:3000` or your deployed Netlify URL) and review **overview stats**: total reviews, issues by **severity**, and **cost** / token usage trends.
2. Use **review history** to see past runs and drill into a single review’s issues.
3. Monitor **critical** vs **warning** vs **info** distribution to prioritize process improvements (e.g., more security training if critical spikes).
4. Share the **installation link** (see Section 3) so new repos get coverage consistently.

### For senior developers

1. Submit a normal GitHub **pull request review** with **Request changes** when you want the author to address specific points.
2. The bot’s **senior comment** flow can consume that context (webhook on `pull_request_review`) to generate explanations and **fix prompts** aligned with your feedback—helping juniors act on your review without repeating the same lecture every time.
3. Keep comments specific; the pipeline works best when tied to concrete files and expectations.

---

## Section 3 — How to Share / Demo

### Share the GitHub App installation link

1. In GitHub: **Settings → Developer settings → GitHub Apps → [Your App]**.
2. Copy the **Public page** URL or use **Install App** and share that flow with teammates.
3. Recipients choose org/account and repositories, then **Install**.

### Share the ngrok dashboard URL (live local demo)

1. While developing, start ngrok (or your tunnel) pointing at your local API port (e.g., `8000`).
2. Copy the **HTTPS** forwarding URL into the GitHub App’s **Webhook URL** (`https://<subdomain>.ngrok-free.app/webhooks/github`).
3. Share the **ngrok web interface** URL (typically `http://127.0.0.1:4040`) with viewers so they can see incoming webhook requests and replays during a live demo—useful for debugging in real time.

> **Security:** Do not leave production secrets on a shared machine; use demo-only keys or a throwaway GitHub App for public demos.

### Production: Railway + Netlify and permanent URLs

1. Deploy the **API + Celery worker** to **Railway** (see README / Section 7).
2. Deploy the **dashboard** to **Netlify** with `NEXT_PUBLIC_API_URL` pointing at your Railway API URL.
3. Update the GitHub App **Webhook URL** and **Homepage URL** to the production API and marketing page as needed.
4. Share the **Netlify** dashboard URL with stakeholders for ongoing use; share **Railway** only with operators.

### Record a demo video (suggested storyboard)

1. **Open a PR** in a repo with the app installed—show the branch and small intentional issue (e.g., hardcoded color).
2. Cut to **GitHub** as the review finishes—show inline comments appearing on “Files changed.”
3. Open the **dashboard**—show the new review in history and severity breakdown.
4. **Copy a fix prompt** from a comment or prompts page and paste into Claude/Copilot—show the suggested fix.
5. Keep the video under 3–5 minutes for sharing internally.

---

## Section 4 — How to Install on New Repositories

Follow these steps in order. Add your own screenshots where indicated—capture full browser width and hide secrets.

### Prerequisites

- GitHub App already created (see project `README.md`).
- Webhook URL reachable from the internet (production API or ngrok for testing).

### Step 1 — Open the GitHub App settings

1. Go to [GitHub Settings → Developer settings → GitHub Apps](https://github.com/settings/apps).
2. Click your **AI Code Review Bot** (or your app name).

**Screenshot:** App settings header showing App ID and app name.

### Step 2 — Confirm webhook and permissions

1. Under **Webhook**, ensure **Active** is checked and **Webhook URL** matches your deployment:  
   `https://<your-api-host>/webhooks/github`
2. Under **Repository permissions**, verify: **Contents** Read, **Issues** Read & write, **Metadata** Read, **Pull requests** Read & write.
3. Under **Subscribe to events**, enable **Pull request** and **Pull request review**.

**Screenshot:** Webhook section with URL (redact tokens if any appear).

### Step 3 — Install the app on more repositories

1. In the left sidebar, click **Install App**.
2. Choose the **GitHub account or organization** where the new repo lives.
3. Click **Configure** (if already installed) or **Install**.
4. Select **Only select repositories** and pick the new repository(ies), or **All repositories** if appropriate.
5. Click **Save** or **Install**.

**Screenshot:** Repository selection dialog with the new repo checked.

### Step 4 — Verify delivery

1. Open **Recent Deliveries** (from the app’s **Advanced** or webhook section, depending on UI).
2. Open a test PR in the new repo; confirm a delivery with **200** response.
3. If failed, inspect response body—often **401** means HMAC mismatch (**Webhook Secret** must match server `GITHUB_WEBHOOK_SECRET`).

**Screenshot:** Successful delivery row with green status.

### Step 5 — Smoke-test the PR flow

1. Create a small PR in the new repo.
2. Confirm Celery worker logs show the review task.
3. Confirm inline comments and dashboard entry appear.

---

## Section 5 — Dashboard Features

| Feature | What it does |
|--------|----------------|
| **Overview stats** | High-level counts: reviews completed, issues grouped by **severity**, estimated **cost** / usage—useful for leads. |
| **Review history** | Paginated list of past reviews with links to detail pages. |
| **Review detail** | Per-review breakdown of issues, metadata, and senior feedback when applicable. |
| **Fix prompts library** | Searchable collection of generated **fix prompts** with filters (e.g., agent, severity) and **feedback** (helpful / not helpful). |
| **Real-time notifications** | **SSE**-driven updates (e.g., new review completed) with optional browser notifications via the notification bell hook. |
| **Settings** | In-app reference for GitHub App setup, permissions, webhook URL pattern, and agent descriptions (see `apps/dashboard/app/settings/page.tsx`). |

---

## Section 6 — Configuration Options

Configuration is primarily **environment-driven** (see `.env.example` in the repo root).

| Area | Options | Notes |
|------|---------|--------|
| **Models** | `MODEL_NAME` | Default `claude-haiku-4-5-20251001`; can switch to a larger model for quality at higher cost. |
| **Token limits** | `MAX_TOKENS_AGENT`, `MAX_TOKENS_AGGREGATOR` | Bound output size per agent vs aggregator pass. |
| **Agents** | Four specialized agents + aggregator | Implemented in code; disabling an agent requires code change today—the Settings page documents roles for operators. |
| **Severity** | `critical`, `warning`, `info` | Produced by agents/aggregator; drives dashboard charts and triage. |
| **GitHub** | `GITHUB_APP_ID`, `GITHUB_APP_PRIVATE_KEY`, `GITHUB_WEBHOOK_SECRET` | Required for auth and webhook verification. |
| **URLs** | `API_BASE_URL`, `FRONTEND_URL` | Used for CORS, links, and client configuration. |

For **thresholds** (e.g., only post “warning” and above), the codebase may evolve—check `aggregator` and review orchestrator for filtering logic when upgrading.

---

## Section 7 — Deployment for Production

A typical production layout:

| Layer | Service | Role |
|-------|---------|------|
| **Backend API** | **Railway** | Runs FastAPI (`web` process from `Procfile`). |
| **Worker** | **Railway** | Runs Celery (`worker` process) on the same or a second service with the same env. |
| **Frontend** | **Netlify** | Hosts the Next.js dashboard; set `NEXT_PUBLIC_API_URL` to the public API URL. |
| **Database** | **Supabase** | Managed **PostgreSQL**; use `postgresql+asyncpg://` connection string. |
| **Redis** | **Upstash** | **Celery broker**, idempotency, and **pub/sub** for notifications; use `rediss://` URL. |

**Checklist**

1. Set all variables from `.env.example` in Railway (and Netlify for frontend).
2. Run **database migrations** (Alembic) against Supabase before traffic.
3. Point GitHub App **Webhook URL** to `https://<railway-domain>/webhooks/github`.
4. Confirm `/health` returns healthy for API, DB, and Redis.
5. Scale worker replicas if queue depth grows.

---

## Section 8 — Troubleshooting

| Symptom | Likely cause | What to do |
|--------|----------------|------------|
| Webhook returns **401** | Invalid HMAC or wrong secret | Ensure `GITHUB_WEBHOOK_SECRET` in the server matches GitHub App **Webhook secret**; redeploy after changes. |
| Duplicate reviews | Idempotency bypassed | Confirm **Redis** is reachable; check `X-GitHub-Delivery` handling and TTL. |
| No review queued | Wrong events or repo not installed | Verify **Pull request** events and that the app is installed on the target repo. |
| Worker idle / tasks stuck | Celery not running or wrong **Redis** URL | Start worker with `high,default` queues; verify `REDIS_URL` and TLS (`rediss://`). |
| 422 on inline comment | Line not in diff | GitHub rejects comments on unchanged lines; aggregator may fall back to issue comment—check `github_client` behavior. |
| Dashboard empty | Wrong API URL | Set `NEXT_PUBLIC_API_URL` (Netlify) to the public API; check CORS and `FRONTEND_URL` on API. |
| SSE disconnects | Proxy timeouts | Netlify/Railway may need keep-alive friendly settings; client reconnects via `useNotifications`—check browser console. |
| High cost | Large diffs + many agents | Reduce PR size, lower `MAX_TOKENS_*`, or use a smaller model for non-critical repos. |
| DB connection errors | Wrong `DATABASE_URL` or pooler | Use `postgresql+asyncpg://` for async SQLAlchemy; verify Supabase password and pooler host. |

**Logs:** Inspect Railway logs for API and worker; use Supabase SQL editor for persisted reviews; use ngrok inspector locally.

---

## Related documentation

- Project **README.md** — full setup, GitHub App fields, and local dev with Docker.
- **TERMS.md** — glossary of concepts used in this guide.
