import json

import pytest
from hypothesis import given, strategies as st

from college_qa.tools import TOOLS, run_tool_call, validate_fees_args, validate_marks_args, ToolArgumentError


def fake_handlers(calls):
    def get_marks(**kwargs):
        calls.append(("get_marks", kwargs))
        return 3.4

    def get_fees(**kwargs):
        calls.append(("get_fees", kwargs))
        return -1

    return {"get_marks": get_marks, "get_fees": get_fees}


def test_every_tool_requires_a_semester():
    for tool in TOOLS:
        assert "semester" in tool["function"]["parameters"]["required"]


def test_a_valid_call_reaches_the_handler_with_clean_arguments():
    calls = []
    out = run_tool_call("get_marks", json.dumps({"student_name": "  Peter Pandey ", "semester": 1}), fake_handlers(calls))
    assert json.loads(out) == {"result": 3.4}
    assert calls == [("get_marks", {"student_name": "Peter Pandey", "semester": 1, "operation": ""})]


def test_an_aggregate_defaults_to_the_average():
    assert validate_marks_args({"semester": 3})["operation"] == "avg"


def test_a_missing_record_is_reported_not_returned_as_minus_one():
    out = json.loads(run_tool_call("get_fees", json.dumps({"semester": 2, "fees_type": "paid"}), fake_handlers([])))
    assert out["result"] is None and "no matching record" in out["note"]


@pytest.mark.parametrize("semester", [0, 5, "1", 1.5, True, None])
def test_an_invalid_semester_never_reaches_the_database(semester):
    calls = []
    out = json.loads(run_tool_call("get_fees", json.dumps({"semester": semester}), fake_handlers(calls)))
    assert "error" in out and calls == []


def test_an_unknown_fee_type_is_rejected():
    with pytest.raises(ToolArgumentError):
        validate_fees_args({"semester": 1, "fees_type": "refund"})


def test_an_unknown_tool_is_reported_to_the_model():
    assert "unknown tool" in json.loads(run_tool_call("drop_tables", "{}", fake_handlers([])))["error"]


@given(st.text())
def test_any_argument_text_gives_a_json_answer_and_never_raises(raw):
    calls = []
    out = run_tool_call("get_marks", raw, fake_handlers(calls))
    parsed = json.loads(out)
    assert "error" in parsed or "result" in parsed


@given(st.dictionaries(st.text(max_size=12), st.one_of(st.none(), st.booleans(), st.integers(), st.text(max_size=12))))
def test_the_handler_only_ever_sees_a_valid_semester(args):
    calls = []
    run_tool_call("get_fees", json.dumps(args), fake_handlers(calls))
    for _, kwargs in calls:
        assert isinstance(kwargs["semester"], int) and 1 <= kwargs["semester"] <= 4
        assert kwargs["fees_type"] in ("paid", "pending", "total")
