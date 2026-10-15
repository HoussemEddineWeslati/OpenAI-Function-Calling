import json
from types import SimpleNamespace as NS

from college_qa.assistant import MAX_TOOL_ROUNDS, answer


def tool_call(call_id, name, arguments):
    return NS(id=call_id, function=NS(name=name, arguments=json.dumps(arguments)))


def reply(content=None, tool_calls=None):
    return NS(choices=[NS(message=NS(content=content, tool_calls=tool_calls))])


class FakeClient:
    """Replays scripted model replies and records every request."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.requests = []
        self.chat = NS(completions=NS(create=self._create))

    def _create(self, **request):
        self.requests.append(json.loads(json.dumps(request["messages"], default=str)))
        return self.replies.pop(0)


HANDLERS = {"get_marks": lambda **kw: 3.4, "get_fees": lambda **kw: 1200}


def test_a_general_question_is_answered_without_tools():
    client = FakeClient([reply("A balance sheet shows assets and liabilities.")])
    assert answer("What is a balance sheet?", client, HANDLERS).startswith("A balance sheet")
    assert len(client.requests) == 1


def test_a_database_question_runs_the_tool_and_returns_the_final_answer():
    client = FakeClient(
        [
            reply(tool_calls=[tool_call("c1", "get_fees", {"student_name": "Peter Pandey", "semester": 1, "fees_type": "pending"})]),
            reply("Peter Pandey has 1200 in pending fees for semester 1."),
        ]
    )
    assert "1200" in answer("How much does Peter Pandey still owe in semester 1?", client, HANDLERS)

    second = client.requests[1]
    tool_message = second[-1]
    assert tool_message["role"] == "tool" and tool_message["tool_call_id"] == "c1"
    assert json.loads(tool_message["content"]) == {"result": 1200}


def test_an_invalid_tool_call_is_sent_back_as_an_error_for_the_model_to_fix():
    client = FakeClient(
        [
            reply(tool_calls=[tool_call("c1", "get_marks", {"semester": 9})]),
            reply("Which semester do you mean, between 1 and 4?"),
        ]
    )
    answer("GPA in semester 9?", client, HANDLERS)
    assert "error" in json.loads(client.requests[1][-1]["content"])


def test_the_loop_stops_after_a_fixed_number_of_tool_rounds():
    looping = [reply(tool_calls=[tool_call(f"c{i}", "get_marks", {"semester": 1})]) for i in range(MAX_TOOL_ROUNDS)]
    client = FakeClient(looping)
    assert "could not answer" in answer("Average GPA?", client, HANDLERS)
    assert len(client.requests) == MAX_TOOL_ROUNDS
