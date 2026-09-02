from __future__ import annotations

import json
from typing import Any

from app.agents.contracts import ManagerDecision, ManagerRunResult
from app.core.config import settings


MANAGER_INSTRUCTIONS = """
You are the Project Manager for Mobile ChatGpt.

The Project Brain database is the durable source of truth. You are a decision layer,
not the database and not the phone executor. Never invent project/task IDs. Never
claim that a side effect happened unless the supplied context explicitly says it did.

Choose exactly one action:
- continue_project: use when existing dependency-satisfied work should be allowed to proceed.
- pause_project: use only when continuing would be unsafe or clearly contrary to the goal.
- wait: use when running work, approvals, or external dependencies should finish first.
- request_review: use when a blocker, ambiguity, risky decision, or inconsistent state needs a human.
- no_op: use when the project is complete or no state change is useful.

Rules:
1. Reference only task IDs that appear in the context.
2. Do not create new tasks in this first integration milestone.
3. High-risk/external actions are outside your authority and must remain behind Project Brain approval rules.
4. Prefer a small, conservative next step over speculative replanning.
5. If approvals are pending, normally wait or request review rather than bypassing them.
6. Your structured output is a recommendation. Deterministic policy decides whether it is applied.
""".strip()


class OpenAIAgentsRuntime:
    """Lazy OpenAI Agents SDK adapter.

    Importing this module does not require the SDK to be installed. The dependency is
    loaded only when a live run is requested, so deterministic tests remain runnable
    in environments without OpenAI credentials/network access.
    """

    async def run_manager(self, *, context: dict, instruction: str | None = None) -> ManagerRunResult:
        try:
            from agents import Agent, RunConfig, Runner
        except ImportError as exc:  # pragma: no cover - exercised only in misconfigured live envs
            raise RuntimeError(
                "OpenAI Agents SDK is not installed. Install project dependencies including openai-agents."
            ) from exc

        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured for live manager runs")

        agent = Agent(
            name="Mobile ChatGpt Project Manager",
            instructions=MANAGER_INSTRUCTIONS,
            model=settings.openai_manager_model,
            output_type=ManagerDecision,
        )
        prompt: dict[str, Any] = {
            "project_context": context,
            "operator_instruction": instruction or "Choose the safest useful next project action.",
        }
        run_config = RunConfig(
            workflow_name="Mobile ChatGpt Project Manager",
            group_id=str(context.get("project", {}).get("id") or context.get("project_id") or "unknown"),
            trace_include_sensitive_data=settings.openai_trace_include_sensitive_data,
        )
        result = await Runner.run(agent, json.dumps(prompt, ensure_ascii=False), run_config=run_config)
        decision = result.final_output
        if not isinstance(decision, ManagerDecision):
            decision = ManagerDecision.model_validate(decision)

        usage_obj = result.context_wrapper.usage
        usage = {
            "requests": getattr(usage_obj, "requests", None),
            "input_tokens": getattr(usage_obj, "input_tokens", None),
            "output_tokens": getattr(usage_obj, "output_tokens", None),
            "total_tokens": getattr(usage_obj, "total_tokens", None),
        }
        return ManagerRunResult(
            decision=decision,
            provider_run_ref=getattr(result, "last_response_id", None),
            usage=usage,
        )


def get_manager_runtime() -> OpenAIAgentsRuntime:
    return OpenAIAgentsRuntime()
