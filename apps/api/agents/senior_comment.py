"""
Senior Comment Handler: when a senior dev requests changes on a PR,
this agent reads their comments and generates actionable fix prompts + guidance.
"""
import json
import time
import anthropic

from core.config import settings


SENIOR_HANDLER_PROMPT = """<role>
You are an experienced Staff Engineer acting as a mentor. A senior developer has
left review comments on a pull request requesting changes. Your job is to help
the junior developer understand and fix each comment efficiently.
</role>

<task>
For each senior developer comment provided, generate:
1. A clear explanation of what the senior wants changed and WHY (the principle behind it).
2. Step-by-step guidance on how to implement the fix.
3. A ready-to-paste prompt for Claude/Copilot that will generate the exact fix.
</task>

<rules>
1. Be encouraging — frame feedback as learning opportunities, not criticism.
2. Reference the specific file and line when available.
3. If the comment is vague, provide your best interpretation plus alternatives.
4. Each prompt should be self-contained and actionable.
5. Group related comments that reference the same logical change.
</rules>

<output_format>
Respond with ONLY valid JSON:
{
  "handled_comments": [
    {
      "original_comment": "what the senior wrote",
      "file": "path/to/file",
      "line": null,
      "explanation": "Why the senior is asking for this change",
      "guidance": "Step-by-step on how to fix it",
      "fix_prompt": "Ready-to-paste prompt for AI assistant"
    }
  ],
  "summary": "Brief overview of all changes requested"
}
</output_format>"""


class SeniorCommentAgent:
    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.token_usage = {"input": 0, "output": 0}
        self.latency_ms = 0

    async def handle(self, pr_title: str, comments: list[dict], diff: str = "") -> dict:
        start = time.time()

        comments_text = json.dumps(comments, indent=2)
        user_content = (
            f"<pr_title>{pr_title}</pr_title>\n"
            f"<senior_comments>\n{comments_text}\n</senior_comments>"
        )
        if diff:
            user_content += f"\n<diff>\n{diff}\n</diff>"

        response = await self.client.messages.create(
            model=settings.MODEL_NAME,
            max_tokens=settings.MAX_TOKENS_AGGREGATOR,
            system=SENIOR_HANDLER_PROMPT,
            messages=[{"role": "user", "content": user_content}],
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
                "handled_comments": [],
                "summary": "Failed to parse senior comment handler output.",
            }

    def get_stats(self) -> dict:
        input_cost = self.token_usage["input"] * 1.0 / 1_000_000
        output_cost = self.token_usage["output"] * 5.0 / 1_000_000
        return {
            "agent": "senior_comment_handler",
            "model": settings.MODEL_NAME,
            "input_tokens": self.token_usage["input"],
            "output_tokens": self.token_usage["output"],
            "total_tokens": self.token_usage["input"] + self.token_usage["output"],
            "latency_ms": self.latency_ms,
            "estimated_cost_usd": round(input_cost + output_cost, 6),
        }
