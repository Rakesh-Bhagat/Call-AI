from dataclasses import dataclass

MAX_FAILED_ATTEMPTS = 3

@dataclass
class CallContext:
    customer_id: str | None = None
    failed_attempts: int = 0

    @property
    def verified(self) -> bool:
        return self.customer_id is not None

    @property
    def locked(self) -> bool:
        return self.failed_attempts >= MAX_FAILED_ATTEMPTS