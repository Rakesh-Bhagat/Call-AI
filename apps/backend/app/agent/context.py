from dataclasses import dataclass

MAX_FAILED_ATTEMPTS = 3

@dataclass
class CallContext:
    customer_id: str | None = None
    failed_attempts: int = 0
    escalated: bool = False
    escalation_reason: str | None = None
    ended: bool = False

    @property
    def verified(self) -> bool:
        return self.customer_id is not None

    @property
    def locked(self) -> bool:
        return self.failed_attempts >= MAX_FAILED_ATTEMPTS