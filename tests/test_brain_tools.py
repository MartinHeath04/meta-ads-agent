"""Tests for the agent's tool-use loop (offline, with a fake Anthropic client)."""

from types import SimpleNamespace

from agent.brain import AgentBrain
from agent.actions import ActionType, ActionStatus


def _tool_use(action_type=ActionType.PAUSE_ADSET.value, target_id="adset_boost"):
    return SimpleNamespace(
        type="tool_use",
        id="toolu_1",
        name="propose_action",
        input={
            "action_type": action_type,
            "target_type": "adset",
            "target_id": target_id,
            "target_name": "Boosted post audience",
            "rationale": "Cost per message 2x the account average over 7 days.",
            "confidence": "high",
        },
    )


def _text_block(text="Done."):
    return SimpleNamespace(type="text", text=text)


class FakeMessages:
    """Returns queued responses in order; records each create() call."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self._responses.pop(0)


class FakeClient:
    def __init__(self, responses):
        self.messages = FakeMessages(responses)


def _brain_with(responses):
    brain = AgentBrain(api_key="test")
    brain.client = FakeClient(responses)  # swap in the fake, no network
    return brain


def test_tool_calls_become_proposed_actions():
    responses = [
        SimpleNamespace(stop_reason="tool_use", content=[_tool_use()]),
        SimpleNamespace(stop_reason="end_turn", content=[_text_block()]),
    ]
    brain = _brain_with(responses)

    actions = brain.propose_actions("c", "a", "d")

    assert len(actions) == 1
    a = actions[0]
    assert a.action_type == ActionType.PAUSE_ADSET.value
    assert a.target_id == "adset_boost"
    assert a.status == ActionStatus.PROPOSED.value
    # Second iteration ran (end_turn) then the loop stopped.
    assert len(brain.client.messages.calls) == 2


def test_multiple_actions_across_iterations():
    responses = [
        SimpleNamespace(stop_reason="tool_use", content=[_tool_use(target_id="adset_1")]),
        SimpleNamespace(stop_reason="tool_use", content=[_tool_use(target_id="adset_2")]),
        SimpleNamespace(stop_reason="end_turn", content=[_text_block()]),
    ]
    actions = _brain_with(responses).propose_actions("c", "a", "d")
    assert [a.target_id for a in actions] == ["adset_1", "adset_2"]


def test_no_actions_when_agent_just_talks():
    responses = [SimpleNamespace(stop_reason="end_turn", content=[_text_block("Not enough data.")])]
    assert _brain_with(responses).propose_actions("c", "a", "d") == []


def test_max_iterations_guard_stops_runaway_loop():
    # Always returns tool_use — the guard must stop it.
    always = [SimpleNamespace(stop_reason="tool_use", content=[_tool_use()]) for _ in range(50)]
    brain = _brain_with(always)
    actions = brain.propose_actions("c", "a", "d", max_iterations=3)
    assert len(brain.client.messages.calls) == 3  # capped
    assert len(actions) == 3


def test_tool_and_system_are_passed_to_the_api():
    responses = [SimpleNamespace(stop_reason="end_turn", content=[_text_block()])]
    brain = _brain_with(responses)
    brain.propose_actions("c", "a", "d")
    call = brain.client.messages.calls[0]
    assert call["tools"][0]["name"] == "propose_action"
    # system prompt is cache-controlled for reuse across iterations
    assert call["system"][0]["cache_control"] == {"type": "ephemeral"}
