from app.agent.context import CallContext
from app.agent.handlers import end_call, verify_customer
from app.agent.tools import REGISTRY


def test_end_call_works_without_verification():
    ctx = CallContext()
    result = end_call(ctx)
    assert result["ended"] is True
    assert ctx.ended is True
    assert ctx.escalated is False


def test_end_call_tolerates_an_unexpected_reason_argument():
    ctx = CallContext()
    assert end_call(ctx, reason="caller said bye")["ended"] is True


def test_end_call_does_not_change_verification():
    ctx = CallContext()
    verify_customer(ctx, "4821", "1990-05-14")
    end_call(ctx)
    assert ctx.verified is True
    assert ctx.customer_id == "C1001"


def test_end_call_is_registered():
    assert REGISTRY["end_call"] is end_call
