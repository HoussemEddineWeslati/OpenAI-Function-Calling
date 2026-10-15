"""Question answering with the OpenAI tools API.

The model decides whether a question needs the college database. When it does,
it asks for a tool call; we validate and run it, send the result back, and let
the model write the final answer. General questions are answered directly.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from typing import Any

from .tools import TOOLS, run_tool_call

SYSTEM_PROMPT = (
    "You answer questions about AtliQ Commerce College. For a student's marks or fees, "
    "always call a tool instead of guessing. If a tool reports no matching record, say so. "
    "For general questions, answer from your own knowledge."
)
MAX_TOOL_ROUNDS = 3


def answer(
    question: str,
    client: Any,
    handlers: Mapping[str, Callable[..., Any]],
    model: str | None = None,
) -> str:
    model = model or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    for _ in range(MAX_TOOL_ROUNDS):
        response = client.chat.completions.create(model=model, messages=messages, tools=TOOLS, tool_choice="auto")
        message = response.choices[0].message
        if not message.tool_calls:
            return message.content or ""

        messages.append(
            {
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {"name": call.function.name, "arguments": call.function.arguments},
                    }
                    for call in message.tool_calls
                ],
            }
        )
        for call in message.tool_calls:
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": run_tool_call(call.function.name, call.function.arguments, handlers),
                }
            )

    return "Sorry, I could not answer that question. Please rephrase it."
