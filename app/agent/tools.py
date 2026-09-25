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

TOOLS = types.Tool(function_declarations=[
    verify_customer_decl,
])

REGISTRY = {
    "verify_customer": handlers.verify_customer
}