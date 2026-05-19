"""Канальный уровень: кадрирование, CRC, маршрутизация по кольцу, подтверждения."""

from __future__ import annotations

import json
import threading
import time
from typing import Callable

from src.application.mail import AckPayload, Letter
from src.common.constants import (
    FRAME_ACK_DELIVERED,
    FRAME_ACK_READ,
    FRAME_DATA,
    FRAME_ERROR,
    MAX_HOPS,
    NODE_COUNT,
)
from src.common.frame import Frame, FrameDecoder, encode_frame
from src.physical.transport import PhysicalLayer


class DataLinkLayer:
    def __init__(
        self,
        node_id: int,
        physical: PhysicalLayer,
        on_letter: Callable[[Letter], None],
        on_ack: Callable[[AckPayload], None],
        on_log: Callable[[str], None],
        on_error: Callable[[str], None],
    ) -> None:
        self.node_id = node_id
        self._phy = physical
        self._on_letter = on_letter
        self._on_ack = on_ack
        self._on_log = on_log
        self._on_error = on_error
        self._dec_left = FrameDecoder()
        self._dec_right = FrameDecoder()
        self._seq = 0
        self._lock = threading.Lock()
        self._seen: dict[tuple[int, int], float] = {}

    def _next_seq(self) -> int:
        with self._lock:
            self._seq = (self._seq + 1) % 65536
            return self._seq

    def _is_duplicate(self, src: int, seq: int) -> bool:
        key = (src, seq)
        now = time.time()
        if key in self._seen and now - self._seen[key] < 30:
            return True
        self._seen[key] = now
        # очистка старых
        for k, t in list(self._seen.items()):
            if now - t > 60:
                del self._seen[k]
        return False

    def on_physical_data(self, data: bytes, side: str) -> None:
        decoder = self._dec_left if side == "left" else self._dec_right
        for frame in decoder.feed(data):
            self._handle_frame(frame, side)

    def _handle_frame(self, frame: Frame, arrived_on: str) -> None:
        if self._is_duplicate(frame.src, frame.seq):
            return

        if frame.dst == self.node_id:
            try:
                if frame.frame_type == FRAME_DATA:
                    letter = Letter.from_json(frame.payload)
                    self._on_log(f"Получено письмо {letter.letter_id} от узла {letter.sender}")
                    self._on_letter(letter)
                    self.send_ack(letter.sender, letter.letter_id, FRAME_ACK_DELIVERED)
                elif frame.frame_type == FRAME_ACK_DELIVERED:
                    ack = AckPayload.from_json(frame.payload)
                    ack.ack_type = "delivered"
                    self._on_ack(ack)
                elif frame.frame_type == FRAME_ACK_READ:
                    ack = AckPayload.from_json(frame.payload)
                    ack.ack_type = "read"
                    self._on_ack(ack)
                elif frame.frame_type == FRAME_ERROR:
                    msg = frame.payload.decode("utf-8", errors="replace")
                    self._on_error(msg)
                    self._on_log(f"Служебная ошибка от узла {frame.src}: {msg}")
            except Exception as exc:
                self._on_error(f"Ошибка обработки кадра: {exc}")
            return

        if frame.dst != self.node_id and frame.hop < MAX_HOPS:
            self._forward(frame, arrived_on)

    def _forward(self, frame: Frame, arrived_on: str) -> None:
        out_port = "right" if arrived_on == "left" else "left"
        fwd = Frame(
            dst=frame.dst,
            src=frame.src,
            frame_type=frame.frame_type,
            hop=frame.hop + 1,
            seq=frame.seq,
            payload=frame.payload,
        )
        self._transmit(fwd, out_port)

    def _transmit(self, frame: Frame, direction: str) -> None:
        data = encode_frame(frame)
        self._phy.send(data, direction)

    def _pick_direction(self, dst: int) -> str:
        """Выбор направления по кольцу (кратчайший путь из двух)."""
        diff_cw = (dst - self.node_id) % NODE_COUNT
        return "right" if diff_cw <= NODE_COUNT // 2 else "left"

    def send_letter(self, letter: Letter) -> None:
        frame = Frame(
            dst=letter.recipient,
            src=self.node_id,
            frame_type=FRAME_DATA,
            hop=0,
            seq=self._next_seq(),
            payload=letter.to_json(),
        )
        direction = self._pick_direction(letter.recipient)
        self._transmit(frame, direction)
        self._on_log(f"Письмо {letter.letter_id} отправлено узлу {letter.recipient} ({direction})")

    def send_ack(self, dst: int, letter_id: str, ack_type: int) -> None:
        ack = AckPayload(letter_id=letter_id, ack_type="")
        payload = ack.to_json()
        frame = Frame(
            dst=dst,
            src=self.node_id,
            frame_type=ack_type,
            hop=0,
            seq=self._next_seq(),
            payload=payload,
        )
        self._transmit(frame, self._pick_direction(dst))

    def notify_error_to_neighbor(self, neighbor: int, message: str) -> None:
        frame = Frame(
            dst=neighbor,
            src=self.node_id,
            frame_type=FRAME_ERROR,
            hop=0,
            seq=self._next_seq(),
            payload=message.encode("utf-8"),
        )
        self._transmit(frame, self._pick_direction(neighbor))
