from google.genai import types
from app.agent import handlers

verify_customer_decl = {
    "name": "verify_customer",
    "description": (
        "Verify the caller's identity. Call this BEFORE any account or loan questions. "
        "Ask the caller for the last 4 digits of their registered mobile number and their "
        "date of birth, then call this. Convert the date of birth to YYYY-MM-DD."
    ),
    "parameters": {
        "type": "OBJECT",
        'properties': {
            "mobile_last4": {"type": "STRING", "description": "Last 4 digits of registered mobile number"},
            "dob": {"type": "STRING", "description": "Date of birth as YYYY-MM-DD format."}
        },
        "required": ["mobile_last4", "dob"]
    },
}

check_loan_emi_decl = {
    "name": "check_loan_emi",
    "description": (
          "Get the EMI amount, next EMI due date, outstanding amount and any overdue amount for the "
          "verified caller's loan. Only call after verify_customer succeeded. "
          "If the caller has several loans, pass loan_type (e.g. 'home', 'personal', 'car')."
      ),
      "parameters": {
          "type": "OBJECT",
          "properties": {
              "loan_type": { "type": "STRING", "description": "KInd of loan, e.g. home, personal, car. Optional if the caller has one loan."}
          }
      }
}
check_account_balance_decl = {
    "name": "check_account_balance",
    "description": """
    Get the account balance, interest_rate and maturity_date for the verified caller's account.
    Only call after verify_customer succeeded. 
    If the caller has several accounts, pass account_type (e.g. 'Savings account', 'Fixed deposit').
     
    """,
    "parameters": {
      "type": "OBJECT",
      "properties": {
          "account_type": {"type": "STRING", "description": "Kind of account, e.g. savings or fixed deposit. Optional if the caller has one account."}
      },
    }
}

escalate_to_agent_decl = {
    "name": "escalate_to_agent",
    "description": (
        "Arrange a callback from a human agent and end the call. Use it when the caller asks for a human, "
        "makes a complaint, reports fraud, faces financial hardship, asks for something outside your scope, "
        "or is locked out of verification. It works even if the caller is not verified. "
        "After it returns, tell the caller a human agent will call them back shortly, say goodbye and stop."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "reason": {"type": "STRING", "description": "Short factual reason for the escalation."}
        },
        "required": ["reason"],
    },
}

end_call_decl = {
    "name": "end_call",
    "description": (
        "End the phone call. Use it when the caller says they are done, has nothing else to ask, says goodbye, "
        "or asks you to end, cut or hang up the call. Do not use it in the middle of a task, and do not use it "
        "after escalate_to_agent because that already ends the call. "
        "After it returns, say one short goodbye and stop."
    ),
}

TOOLS = types.Tool(function_declarations=[
    verify_customer_decl,
    check_loan_emi_decl,
    check_account_balance_decl,
    escalate_to_agent_decl,
    end_call_decl,
])

REGISTRY = {
    "verify_customer": handlers.verify_customer, 
    "check_loan_emi": handlers.check_loan_emi,
    "check_account_balance": handlers.check_account_balance,
    "escalate_to_agent": handlers.escalate_to_agent,
    "end_call": handlers.end_call,
}