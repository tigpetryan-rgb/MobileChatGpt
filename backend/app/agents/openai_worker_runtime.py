from __future__ import annotations

import json

from app.agents.worker_contracts import WorkerOutput, WorkerRunResult
from app.core.config import settings


WORKER_INSTRUCTIONS = """
You are a specialist worker inside Mobile ChatGpt Project Brain.

You receive exactly one leased task and project context. Complete only the supplied task.
Do not invent task IDs, claim phone actions, send messages, delete data, purchase anything,
or perform other external side effects. This milestone has no side-effect tools attached.

Return structured output:
- success=true only if the requested analysis/draft/reasoning work is complete.
- requires_review=true when the task cannot be completed safely or confidently from the context.
- output_refs may contain only logical references you produced in text form; do not fabricate URLs/files.

Project Brain, not you, owns durable state and decides task transitions.
""".strip()


class OpenAIWorkerRuntime:
    async def run_worker(self, *, context: dict) -> WorkerRunResult:
        try:
            from agents import Agent, RunConfig, Runner
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("OpenAI Agents SDK is not installed") from exc
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured for live worker runs")

        agent = Agent(
            name="Mobile ChatGpt Worker",
            instructions=WORKER_INSTRUCTIONS,
            model=settings.openai_worker_model,
            output_type=WorkerOutput,
        )
        run_config = RunConfig(
            workflow_name="Mobile ChatGpt Worker",
            group_id=str(context["project"]["id"]),
            trace_include_sensitive_data=settings.openai_trace_include_sensitive_data,
        )
        result = await Runner.run(agent, json.dumps(context, ensure_ascii=False), run_config=run_config)
        output = result.final_output
        if not isinstance(output, WorkerOutput):
            output = WorkerOutput.model_validate(output)
        usage_obj = result.context_wrapper.usage
        usage = {
            "requests": getattr(usage_obj, "requests", None),
            "input_tokens": getattr(usage_obj, "input_tokens", None),
            "output_tokens": getattr(usage_obj, "output_tokens", None),
            "total_tokens": getattr(usage_obj, "total_tokens", None),
        }
        return WorkerRunResult(
            output=output,
            provider_run_ref=getattr(result, "last_response_id", None),
            usage=usage,
        )


def get_worker_runtime() -> OpenAIWorkerRuntime:
    return OpenAIWorkerRuntime()
