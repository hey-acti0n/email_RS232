"""Модель писем прикладного уровня."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field

from src.common.constants import STATUS_DELIVERED, STATUS_DRAFT, STATUS_READ, STATUS_SENT


@dataclass
class Letter:
    letter_id: str
    sender: int
    recipient: int
    subject: str
    body: str
    status: str = STATUS_DRAFT
    created_at: float = field(default_factory=time.time)

    @staticmethod
    def create(sender: int, recipient: int, subject: str, body: str) -> "Letter":
        return Letter(
            letter_id=str(uuid.uuid4())[:8],
            sender=sender,
            recipient=recipient,
            subject=subject,
            body=body,
        )

    def to_json(self) -> bytes:
        return json.dumps(asdict(self), ensure_ascii=False).encode("utf-8")

    @staticmethod
    def from_json(data: bytes) -> "Letter":
        d = json.loads(data.decode("utf-8"))
        return Letter(**d)


@dataclass
class AckPayload:
    letter_id: str
    ack_type: str  # delivered | read

    def to_json(self) -> bytes:
        return json.dumps(asdict(self), ensure_ascii=False).encode("utf-8")

    @staticmethod
    def from_json(data: bytes) -> "AckPayload":
        d = json.loads(data.decode("utf-8"))
        return AckPayload(**d)
