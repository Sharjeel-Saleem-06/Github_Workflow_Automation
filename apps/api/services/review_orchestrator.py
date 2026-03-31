"""
Review Orchestrator: runs all 4 specialist agents in parallel using asyncio.gather,
then feeds results to the aggregator. Posts comments back to GitHub.
Mirrors Anthropic's own Code Review architecture (parallel agents, cross-verification).
"""
import asyncio
import logging

from agents import (
    ColorConstantsAgent,
    LogicBugsAgent,
    BestPracticesAgent,
    SecurityAgent,
    AggregatorAgent,
)
from services.github_client import GitHubClient

logger = logging.getLogger(__name__)


class ReviewOrchestrator:
    def __init__(self, github_client: GitHubClient):
        self.gh = github_client

    async def run_review(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        head_sha: str,
        pr_context: dict | None = None,
    ) -> dict:
        logger.info(f"Starting review for {owner}/{repo}#{pr_number}")

        diff = await self.gh.get_pr_diff(owner, repo, pr_number)

        if not diff or len(diff.strip()) < 10:
            logger.warning("Empty or trivial diff, skipping review")
            return {
                "verdict": "APPROVED",
                "summary_markdown": "LGTM ✅ — No substantive changes to review.",
                "fix_prompts": [],
                "agent_stats": [],
                "total_tokens": 0,
                "total_cost_usd": 0.0,
            }

        if not pr_context:
            pr_context = {"title": "", "repo": f"{owner}/{repo}", "author": ""}

        color_agent = ColorConstantsAgent()
        logic_agent = LogicBugsAgent()
        practices_agent = BestPracticesAgent()
        security_agent = SecurityAgent()

        results = await asyncio.gather(
            color_agent.run(diff, pr_context),
            logic_agent.run(diff, pr_context),
            practices_agent.run(diff, pr_context),
            security_agent.run(diff, pr_context),
            return_exceptions=True,
        )

        agent_labels = ["color_constants", "logic_bugs", "best_practices", "security"]
        agent_outputs = {}
        agents = [color_agent, logic_agent, practices_agent, security_agent]
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Agent {agents[i].name} failed: {result}")
                agent_outputs[agent_labels[i]] = {"issues": [], "error": str(result)}
            else:
                agent_outputs[agent_labels[i]] = result

        aggregator = AggregatorAgent()
        final = await aggregator.aggregate(list(agent_outputs.values()))

        all_agents = agents + [aggregator]
        stats = [a.get_stats() for a in all_agents]
        total_tokens = sum(s["total_tokens"] for s in stats)
        total_cost = sum(s["estimated_cost_usd"] for s in stats)

        await self._post_results_to_github(
            owner, repo, pr_number, head_sha, final
        )

        return {
            **final,
            "agents_output": agent_outputs,
            "agent_stats": stats,
            "total_tokens": total_tokens,
            "total_cost_usd": total_cost,
        }

    async def _post_results_to_github(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        head_sha: str,
        aggregated: dict,
    ):
        summary = aggregated.get("summary_markdown", "Review complete.")
        bot_header = "## 🤖 AI Code Review Bot\n\n"
        await self.gh.post_issue_comment(
            owner, repo, pr_number, bot_header + summary
        )

        inline_comments = []
        for prompt_item in aggregated.get("fix_prompts", []):
            file_path = prompt_item.get("file", "")
            line_str = prompt_item.get("line", "")
            if not file_path or not line_str:
                continue
            try:
                line_num = int(str(line_str).split("-")[0])
            except (ValueError, IndexError):
                continue

            severity_emoji = {
                "critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"
            }.get(prompt_item.get("severity", ""), "⚪")

            comment_body = (
                f"{severity_emoji} **{prompt_item.get('agent', 'bot')}**: "
                f"{prompt_item.get('issue', '')}\n\n"
                f"<details><summary>💡 Fix Prompt (click to expand)</summary>\n\n"
                f"```\n{prompt_item.get('prompt', '')}\n```\n</details>"
            )
            inline_comments.append({
                "path": file_path,
                "line": line_num,
                "body": comment_body,
            })

        if inline_comments:
            try:
                await self.gh.post_pr_review_batch(
                    owner, repo, pr_number, head_sha, inline_comments
                )
            except Exception as e:
                logger.warning(f"Batch review failed, falling back to individual: {e}")
                for c in inline_comments:
                    try:
                        await self.gh.post_review_comment(
                            owner, repo, pr_number, head_sha,
                            c["body"], c["path"], c["line"],
                        )
                    except Exception as inner_e:
                        logger.warning(f"Inline comment failed on {c['path']}:{c['line']}: {inner_e}")
