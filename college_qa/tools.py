"""Tool definitions the model can call, and safe dispatch of its calls.

The model only proposes a call. Every call is parsed and validated here before
anything touches the database, and every problem is returned to the model as a
readable error instead of raising.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from typing import Any

OPERATIONS = ("max", "min", "avg")
FEES_TYPES = ("paid", "pending", "total")

TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_marks",
            "description": (
                "Get a student's GPA for a semester, or an aggregate GPA (max, min or avg) "
                "of all students in a semester when no student is given."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "student_name": {"type": "string", "description": "First and last name, e.g. John Smith."},
                    "semester": {"type": "integer", "minimum": 1, "maximum": 4},
                    "operation": {
                        "type": "string",
                        "enum": list(OPERATIONS),
                        "description": "Aggregate to compute when student_name is empty.",
                    },
                },
                "required": ["semester"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_fees",
            "description": "Get the paid, pending or total fees of a student, or of a whole semester.",
            "parameters": {
                "type": "object",
                "properties": {
                    "student_name": {"type": "string", "description": "First and last name, e.g. John Smith."},
                    "semester": {"type": "integer", "minimum": 1, "maximum": 4},
                    "fees_type": {"type": "string", "enum": list(FEES_TYPES)},
                },
                "required": ["semester"],
            },
        },
    },
]


class ToolArgumentError(ValueError):
    """The model called a tool with arguments that do not match its schema."""


def _semester(args: Mapping[str, Any]) -> int:
    semester = args.get("semester")
    if isinstance(semester, bool) or not isinstance(semester, int) or not 1 <= semester <= 4:
        raise ToolArgumentError("semester must be an integer between 1 and 4")
    return semester


def _student(args: Mapping[str, Any]) -> str:
    name = args.get("student_name", "")
    if not isinstance(name, str):
        raise ToolArgumentError("student_name must be a string")
    return name.strip()


def _choice(args: Mapping[str, Any], key: str, allowed: tuple[str, ...], default: str) -> str:
    value = args.get(key, default)
    if value not in allowed:
        raise ToolArgumentError(f"{key} must be one of {', '.join(allowed)}")
    return value


def validate_marks_args(args: Mapping[str, Any]) -> dict[str, Any]:
    student = _student(args)
    operation = _choice(args, "operation", OPERATIONS, "avg")
    return {"student_name": student, "semester": _semester(args), "operation": "" if student else operation}


def validate_fees_args(args: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "student_name": _student(args),
        "semester": _semester(args),
        "fees_type": _choice(args, "fees_type", FEES_TYPES, "total"),
    }


VALIDATORS: dict[str, Callable[[Mapping[str, Any]], dict[str, Any]]] = {
    "get_marks": validate_marks_args,
    "get_fees": validate_fees_args,
}


def run_tool_call(name: str, raw_arguments: str, handlers: Mapping[str, Callable[..., Any]]) -> str:
    """Validate one tool call and run it. Always returns text the model can read."""
    if name not in VALIDATORS or name not in handlers:
        return json.dumps({"error": f"unknown tool {name!r}"})
    try:
        args = json.loads(raw_arguments or "{}")
        if not isinstance(args, dict):
            raise ToolArgumentError("arguments must be a JSON object")
        clean = VALIDATORS[name](args)
    except (json.JSONDecodeError, ToolArgumentError) as error:
        return json.dumps({"error": str(error)})

    result = handlers[name](**clean)
    if result is None or result == -1:
        return json.dumps({"result": None, "note": "no matching record in the database"})
    return json.dumps({"result": result})
