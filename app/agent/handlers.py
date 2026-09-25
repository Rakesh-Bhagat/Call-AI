import re
from app.agent.context import CallContext, MAX_FAILED_ATTEMPTS
from app.data import mock_db

def verify_customer(ctx: CallContext, mobile_last4: str, dob: str) -> dict:

    if ctx.verified:
        return {"verified": True, "message": "Caller is already verified."}
    if ctx.locked:
        return {"verified": False, "locked": True, "message": "Too many failed attempts. Do not retry. Offer to transfer to a human agent."}

    digits = re.sub(r"\D", "", mobile_last4)[-4:]
    customer_id = mock_db.find_customer(digits, dob)

    if customer_id is None:
        ctx.failed_attempts += 1
        remaining =  MAX_FAILED_ATTEMPTS - ctx.failed_attempts

        return {"verified": False, "attempt_remaining": remaining, "message": "The details did not match our records."}

    ctx.customer_id = customer_id
    ctx.failed_attempts = 0
    first_name = mock_db.get_customer(customer_id)["name"].split()[0]
    return {"verified": True, "customer_first_name": first_name}