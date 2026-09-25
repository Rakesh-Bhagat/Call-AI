from datetime import date

from app.data import mock_db


def test_find_customer_requires_both_fields_to_match():
    assert mock_db.find_customer("4821", "1990-05-14") == "C1001"
    assert mock_db.find_customer("4821", "1987-11-02") is None
    assert mock_db.find_customer("0000", "1990-05-14") is None


def test_loans_and_accounts_are_scoped_to_their_owner():
    assert mock_db.get_loan("C1001", "HL-20481") is not None
    assert mock_db.get_loan("C1002", "HL-20481") is None       # someone else's loan
    assert mock_db.get_account("C1003", "FD-880014") is None   # someone else's deposit
    assert {a["account_id"] for a in mock_db.list_accounts("C1002")} == {"SB-559340", "FD-880014"}


def test_next_emi_due_rolls_forward():
    assert mock_db.next_emi_due(5, date(2026, 9, 2)) == date(2026, 9, 5)
    assert mock_db.next_emi_due(5, date(2026, 9, 5)) == date(2026, 9, 5)
    assert mock_db.next_emi_due(5, date(2026, 9, 6)) == date(2026, 10, 5)
    assert mock_db.next_emi_due(5, date(2026, 12, 20)) == date(2027, 1, 5)
    assert mock_db.next_emi_due(31, date(2026, 2, 10)) == date(2026, 2, 28)  # short month
