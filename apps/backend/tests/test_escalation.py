from app.agent.context import CallContext
from app.agent.handlers import escalate_to_agent, verify_customer
from app.agent.tools import REGISTRY


def test_escalation_works_without_verification():
    ctx = CallContext()
    result = escalate_to_agent(ctx, "Caller asked for a human")
    assert result["escalated"] is True
    assert ctx.escalated is True
    assert ctx.escalation_reason == "Caller asked for a human"
    assert ctx.verified is False


def test_escalation_is_idempotent_and_keeps_first_reason():
    ctx = CallContext()
    escalate_to_agent(ctx, "fraud report")
    escalate_to_agent(ctx, "something else")
    assert ctx.escalation_reason == "fraud report"


def test_blank_reason_gets_a_default():
    ctx = CallContext()
    escalate_to_agent(ctx, "   ")
    assert ctx.escalation_reason == "Not specified"


def test_lockout_leaves_caller_able_to_escalate():
    ctx = CallContext()
    for _ in range(3):
        verify_customer(ctx, "0000", "2000-01-01")
    assert verify_customer(ctx, "4821", "1990-05-14")["locked"] is True
    assert escalate_to_agent(ctx, "verification locked out")["escalated"] is True


def test_tool_is_registered():
    assert REGISTRY["escalate_to_agent"] is escalate_to_agent
