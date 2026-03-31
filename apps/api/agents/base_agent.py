"""
Async base agent with structured JSON output for production code review.
Adapted from Multi_Agent_Code_Reviewer with async support + cost tracking.
"""
import json
import time
import anthropic

from core.config import settings


class BaseAgent:
    def __init__(self, name: str, system_prompt: str):
        self.name = name
        self.system_prompt = system_prompt
        self.client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.token_usage = {"input": 0, "output": 0}
        self.latency_ms = 0

    async def run(self, diff: str, pr_context: dict | None = None) -> dict:
        start = time.time()
        result = await self._call_claude(diff, pr_context)
        self.latency_ms = int((time.time() - start) * 1000)
        return result

    async def _call_claude(self, diff: str, pr_context: dict | None = None) -> dict:
        user_content = ""
        if pr_context:
            user_content += (
                f"Review this PR diff.\n\n"
                f"PR Title: {pr_context.get('title', '')}\n"
                f"Repository: {pr_context.get('repo', '')}\n"
                f"Author: {pr_context.get('author', '')}\n"
                f"Files Changed: {pr_context.get('files_changed', 0)}\n"
                f"Additions: {pr_context.get('additions', 0)}\n"
                f"Deletions: {pr_context.get('deletions', 0)}\n\n"
            )
        user_content += f"DIFF:\n```\n{diff}\n```\n\nOutput only valid JSON. Be thorough."

        response = await self.client.messages.create(
            model=settings.MODEL_NAME,
            max_tokens=settings.MAX_TOKENS_AGENT,
            system=self.system_prompt,
            messages=[{"role": "user", "content": user_content}],
        )
        self.token_usage["input"] += response.usage.input_tokens
        self.token_usage["output"] += response.usage.output_tokens
        raw = response.content[0].text
        return self._parse_json(raw)

    def _parse_json(self, raw: str) -> dict:
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start_idx = text.find("{")
            end_idx = text.rfind("}") + 1
            if start_idx != -1 and end_idx > start_idx:
                try:
                    return json.loads(text[start_idx:end_idx])
                except json.JSONDecodeError:
                    pass
            return {
                "agent": self.name,
                "summary": "Failed to parse structured output",
                "findings": [],
                "total_issues": 0,
                "_raw_response": text[:500],
            }

    def get_stats(self) -> dict:
        input_cost = self.token_usage["input"] * 1.0 / 1_000_000
        output_cost = self.token_usage["output"] * 5.0 / 1_000_000
        return {
            "agent": self.name,
            "model": settings.MODEL_NAME,
            "input_tokens": self.token_usage["input"],
            "output_tokens": self.token_usage["output"],
            "total_tokens": self.token_usage["input"] + self.token_usage["output"],
            "latency_ms": self.latency_ms,
            "estimated_cost_usd": round(input_cost + output_cost, 6),
        }
