"""Прикладной уровень: управление почтой и статусами."""

from __future__ import annotations

from typing import Callable

from src.application.mail import AckPayload, Letter
from src.common.constants import STATUS_DELIVERED, STATUS_READ, STATUS_SENT
from src.datalink.link_layer import DataLinkLayer


class ApplicationLayer:
    def __init__(
        self,
        node_id: int,
        datalink: DataLinkLayer,
        on_inbox: Callable[[Letter], None],
        on_outbox_update: Callable[[Letter], None],
        on_log: Callable[[str], None],
    ) -> None:
        self.node_id = node_id
        self._dl = datalink
        self._on_inbox = on_inbox
        self._on_outbox_update = on_outbox_update
        self._on_log = on_log
        self.inbox: dict[str, Letter] = {}
        self.outbox: dict[str, Letter] = {}

    def send_mail(self, recipient: int, subject: str, body: str) -> Letter:
        letter = Letter.create(self.node_id, recipient, subject, body)
        letter.status = STATUS_SENT
        self.outbox[letter.letter_id] = letter
        self._on_outbox_update(letter)
        self._dl.send_letter(letter)
        self._on_log(f"Исходящее: письмо {letter.letter_id} → узел {recipient}")
        return letter

    def on_letter_received(self, letter: Letter) -> None:
        letter.status = STATUS_DELIVERED
        self.inbox[letter.letter_id] = letter
        self._on_inbox(letter)

    def open_letter(self, letter_id: str) -> None:
        letter = self.inbox.get(letter_id)
        if not letter or letter.status == STATUS_READ:
            return
        letter.status = STATUS_READ
        self._on_log(f"Письмо {letter_id} прочитано — уведомляем узел {letter.sender}")
        from src.common.constants import FRAME_ACK_READ

        self._dl.send_ack(letter.sender, letter_id, FRAME_ACK_READ)

    def on_ack_received(self, ack: AckPayload) -> None:
        letter = self.outbox.get(ack.letter_id)
        if not letter:
            return
        if ack.ack_type == "delivered":
            letter.status = STATUS_DELIVERED
            self._on_log(f"Подтверждение доставки: {ack.letter_id}")
        elif ack.ack_type == "read":
            letter.status = STATUS_READ
            self._on_log(f"Подтверждение прочтения: {ack.letter_id}")
        self._on_outbox_update(letter)
