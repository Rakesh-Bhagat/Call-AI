import re
from app.agent.context import CallContext, MAX_FAILED_ATTEMPTS
from app.data import mock_db

def verify_customer(ctx: CallContext, mobile_last4: str, dob: str) -> dict:

    if ctx.verified:
        return {"verified": True, "message": "Caller is already verified."}
    if ctx.locked:
        return {"verified": False, "locked": True, "message": "Too many failed attempts. Do not retry. Call escalate_to_agent."}

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

def check_loan_emi(ctx: CallContext, loan_type: str | None = None) -> dict:
    if not ctx.verified:
        return {"error": "not_verified", "message": "Ask the Caller to verify with their mobile last 4 digits and date of birth first."}
    loans = mock_db.list_loans(ctx.customer_id)
    if not loans:
        return { "found": False, "message": "NO loans found for this customer."}
    if loan_type:
        wanted = loan_type.lower()
        loans = [l for l in loans if wanted in l["type"].lower()]
        if not loans:
            return {"found": False, "message": "No loan of that type on this account.", "available_types": [l["type"] for l in mock_db.list_loans(ctx.customer_id)]}

    if len(loans) > 1:
        return { 
            "needs_clarification": True,
            "message": "The customer has more than one loan. Ask which one they mean",
            "loan_types": [l["type"] for l in loans]
            }   
    loan = loans[0]
    return{
        "found": True,
        "loan_type": loan["type"],
        "emi_amount": loan["emi_amount"],
        "next_emi_due": loan["next_emi_due"], 
        "outstanding": loan["outstanding"],
        "overdue_amount": loan["overdue_amount"]
    }

def check_account_balance(ctx: CallContext, account_type: str | None = None) -> dict:
    if not ctx.verified:
        return {"error": "not_verified", "message": "Ask the Caller to verify with their mobile last 4 digits and date of birth first."}

    accounts = mock_db.list_accounts(ctx.customer_id)

    if not accounts: 
        return {"found": False, "message": "No account found for this customer."}
    if account_type:
        wanted = account_type.lower()
        matches = [ a for a in accounts if wanted in a["type"].lower()]
        if not matches: 
            return {"found": False, "message": "No account of that type for this customer.", "available_types": [a["type"] for a in accounts]}

        accounts = matches
        
    if len(accounts) > 1:
        return {
            "needs_clarification": True,
            "message": "Caller has multiple accounts. Ask them to clarify which one they mean.",
            "available_types": [a["type"] for a in accounts]
        }

    account = accounts[0]
    result = {
        "found": True,
        "type": account["type"],
        "balance": account["balance"]
        }
    if "interest_rate" in account:
        result["interest_rate"] = account["interest_rate"]
        result["maturity_date"] = account["maturity_date"]
    return result


def escalate_to_agent(ctx: CallContext, reason: str = "") -> dict:
    if not ctx.escalated:
        ctx.escalated = True
        ctx.escalation_reason = (reason or "").strip() or "Not specified"
    return {
        "escalated": True,
        "message": (
            "A human agent will call the customer back shortly. In one short sentence tell the caller this, "
            "thank them and say goodbye. Do not ask anything else. The call ends after you finish speaking."
        ),
    }


def end_call(ctx: CallContext, reason: str = "") -> dict:
    ctx.ended = True
    return {
        "ended": True,
        "message": (
            "In one short sentence say goodbye to the caller, thanking them by first name if you know it. "
            "Do not ask anything else. The call ends after you finish speaking."
        ),
    }
