"""
Aggregator agent: merges output from all specialist agents, de-duplicates,
ranks by severity, and generates a fix prompt for every issue.
"""
import json
import anthropic

from core.config import settings


AGGREGATOR_PROMPT = """<role>
You are a Lead Staff Engineer writing the final Pull Request review.
You are merging reports from 4 specialized review agents:
  1. Color/Constants Agent — hardcoded colors, magic numbers, missing design tokens
  2. Logic/Bugs Agent — logic errors, null checks, edge cases
  3. Best Practices Agent — SRP, naming, nesting, coupling, error handling
  4. Security Agent — OWASP vulnerabilities, hardcoded secrets, injections
</role>

<task>
Given the combined JSON output from all agents, produce two things:

1. A **markdown summary** for the GitHub PR comment — grouped by severity, de-duplicated.
2. A **fix_prompts** array: for EVERY issue found, generate a ready-to-paste prompt
   that a developer can send to Claude/Copilot to get the exact fix. Each prompt should
   include the file, line, issue description, and specific instructions to fix it.
</task>

<rules>
1. Group findings: 🔴 Critical → 🟠 High → 🟡 Medium → 🟢 Low
2. De-duplicate if multiple agents flagged the same line/issue.
3. Tag each issue with the agent that found it.
4. Verdict at top: "CHANGES REQUESTED" or "APPROVED".
5. If zero issues: return "LGTM ✅ — No issues found."
6. Summary table at top: issue counts per agent and per severity.
7. Each fix_prompt should be a self-contained instruction a dev can paste into an AI assistant.
</rules>

<output_format>
Respond with ONLY valid JSON:
{
  "verdict": "CHANGES_REQUESTED | APPROVED",
  "summary_markdown": "Full markdown review comment",
  "total_critical": 0,
  "total_high": 0,
  "total_medium": 0,
  "total_low": 0,
  "fix_prompts": [
    {
      "file": "path/to/file",
      "line": "line number",
      "agent": "which agent found it",
      "severity": "critical|high|medium|low",
      "issue": "brief description",
      "prompt": "Full prompt to paste into Claude to fix this issue"
    }
  ]
}
</output_format>"""


class AggregatorAgent:
    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.token_usage = {"input": 0, "output": 0}
        self.latency_ms = 0

    async def aggregate(self, agent_results: list[dict]) -> dict:
        import time
        start = time.time()

        combined = json.dumps(agent_results, indent=2)
        response = await self.client.messages.create(
            model=settings.MODEL_NAME,
            max_tokens=settings.MAX_TOKENS_AGGREGATOR,
            system=AGGREGATOR_PROMPT,
            messages=[
                {"role": "user", "content": f"<agent_reports>\n{combined}\n</agent_reports>"}
            ],
        )
        self.token_usage["input"] += response.usage.input_tokens
        self.token_usage["output"] += response.usage.output_tokens
        self.latency_ms = int((time.time() - start) * 1000)

        raw = response.content[0].text
        return self._parse_json(raw)

    def _parse_json(self, raw: str) -> dict:
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            s = text.find("{")
            e = text.rfind("}") + 1
            if s != -1 and e > s:
                try:
                    return json.loads(text[s:e])
                except json.JSONDecodeError:
                    pass
            return {
                "verdict": "ERROR",
                "summary_markdown": "Failed to parse aggregator output.",
                "total_critical": 0,
                "total_high": 0,
                "total_medium": 0,
                "total_low": 0,
                "fix_prompts": [],
            }

    def get_stats(self) -> dict:
        input_cost = self.token_usage["input"] * 1.0 / 1_000_000
        output_cost = self.token_usage["output"] * 5.0 / 1_000_000
        return {
            "agent": "aggregator",
            "model": settings.MODEL_NAME,
            "input_tokens": self.token_usage["input"],
            "output_tokens": self.token_usage["output"],
            "total_tokens": self.token_usage["input"] + self.token_usage["output"],
            "latency_ms": self.latency_ms,
            "estimated_cost_usd": round(input_cost + output_cost, 6),
        }
