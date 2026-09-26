"""In-memory stand-in for a lending / deposits core system.

Every lookup takes a customer_id and refuses to return a record that belongs to
someone else. The agent layer calls these only after a caller has been verified,
so authorization lives in code and not in the prompt.
"""

import calendar
from datetime import date

CUSTOMERS = {
    "C1001": {
        "name": "Rahul Sharma",
        "mobile_last4": "4821",
        "dob": "1990-05-14",
        "language": "en",
    },
    "C1002": {
        "name": "Priya Verma",
        "mobile_last4": "7305",
        "dob": "1987-11-02",
        "language": "hi",
    },
    "C1003": {
        "name": "Amit Das",
        "mobile_last4": "1198",
        "dob": "1995-02-27",
        "language": "en",
    },
}

# emi_day is the day of month the EMI is debited; the next due date is computed
# from today's date so the mock data never goes stale.
LOANS = {
    "HL-20481": {
        "customer_id": "C1001",
        "type": "Home loan",
        "principal": 4_500_000,
        "outstanding": 3_872_450,
        "interest_rate": 8.75,
        "emi_amount": 39_650,
        "emi_day": 5,
        "remaining_months": 141,
        "overdue_amount": 0,
    },
    "PL-77315": {
        "customer_id": "C1001",
        "type": "Personal loan",
        "principal": 300_000,
        "outstanding": 118_200,
        "interest_rate": 12.5,
        "emi_amount": 9_870,
        "emi_day": 18,
        "remaining_months": 13,
        "overdue_amount": 0,
    },
    "CL-30256": {
        "customer_id": "C1002",
        "type": "Car loan",
        "principal": 850_000,
        "outstanding": 642_300,
        "interest_rate": 9.4,
        "emi_amount": 17_480,
        "emi_day": 10,
        "remaining_months": 43,
        "overdue_amount": 17_480,  # missed last month's EMI
    },
}

ACCOUNTS = {
    "SB-559201": {
        "customer_id": "C1001",
        "type": "Savings account",
        "balance": 84_250.75,
    },
    "SB-559340": {
        "customer_id": "C1002",
        "type": "Savings account",
        "balance": 12_030.10,
    },
    "FD-880014": {
        "customer_id": "C1002",
        "type": "Fixed deposit",
        "balance": 500_000.00,
        "interest_rate": 7.1,
        "maturity_date": "2027-03-15",
    },
    "SB-559877": {
        "customer_id": "C1003",
        "type": "Savings account",
        "balance": 3_415.00,
    },
}


def find_customer(mobile_last4: str, dob: str) -> str | None:
    """Return the customer_id whose registered mobile digits and date of birth (YYYY-MM-DD) match."""
    for customer_id, c in CUSTOMERS.items():
        if c["mobile_last4"] == mobile_last4.strip() and c["dob"] == dob.strip():
            return customer_id
    return None


def get_customer(customer_id: str) -> dict | None:
    return CUSTOMERS.get(customer_id)


def next_emi_due(emi_day: int, today: date | None = None) -> date:
    """The next date the EMI will be debited, on or after today."""
    today = today or date.today()
    day = min(emi_day, calendar.monthrange(today.year, today.month)[1])
    candidate = date(today.year, today.month, day)
    if candidate >= today:
        return candidate
    year, month = (today.year + 1, 1) if today.month == 12 else (today.year, today.month + 1)
    return date(year, month, min(emi_day, calendar.monthrange(year, month)[1]))


def list_loans(customer_id: str) -> list[dict]:
    """All loans owned by this customer, with the next EMI due date filled in."""
    return [
        {"loan_id": loan_id, **loan, "next_emi_due": next_emi_due(loan["emi_day"]).isoformat()}
        for loan_id, loan in LOANS.items()
        if loan["customer_id"] == customer_id
    ]


def get_loan(customer_id: str, loan_id: str) -> dict | None:
    """One loan, only if it belongs to this customer."""
    loan = LOANS.get(loan_id)
    if not loan or loan["customer_id"] != customer_id:
        return None
    return {"loan_id": loan_id, **loan, "next_emi_due": next_emi_due(loan["emi_day"]).isoformat()}


def list_accounts(customer_id: str) -> list[dict]:
    """All deposit accounts owned by this customer."""
    return [
        {"account_id": account_id, **acct}
        for account_id, acct in ACCOUNTS.items()
        if acct["customer_id"] == customer_id
    ]


def get_account(customer_id: str, account_id: str) -> dict | None:
    """One account, only if it belongs to this customer."""
    acct = ACCOUNTS.get(account_id)
    if not acct or acct["customer_id"] != customer_id:
        return None
    return {"account_id": account_id, **acct}
