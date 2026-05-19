"""Сборка всех уровней для одного узла сети."""

from __future__ import annotations

from src.application.app_layer import ApplicationLayer
from src.datalink.link_layer import DataLinkLayer
from src.physical.ring_simulator import VirtualPort, get_shared_ring
from src.physical.transport import PhysicalLayer


class NetworkNode:
    def __init__(
        self,
        node_id: int,
        virtual_ports: tuple[VirtualPort, VirtualPort] | None = None,
        use_serial: bool = False,
        serial_left: str | None = None,
        serial_right: str | None = None,
    ) -> None:
        self.node_id = node_id
        self._ui_callbacks: dict = {}

        if virtual_ports is None and not use_serial:
            ring = get_shared_ring()
            virtual_ports = ring.get_ports(node_id)

        left, right = virtual_ports if virtual_ports else (None, None)

        self._log_lines: list[str] = []

        def log(msg: str) -> None:
            self._log_lines.append(msg)
            cb = self._ui_callbacks.get("log")
            if cb:
                cb(msg)

        def error(msg: str) -> None:
            log(f"[ОШИБКА] {msg}")
            cb = self._ui_callbacks.get("error")
            if cb:
                cb(msg)

        self.physical = PhysicalLayer(
            node_id,
            on_bytes=self._on_bytes,
            left=left,
            right=right,
            use_serial=use_serial,
            serial_left=serial_left,
            serial_right=serial_right,
        )

        self.datalink = DataLinkLayer(
            node_id,
            self.physical,
            on_letter=self._route_letter,
            on_ack=self._route_ack,
            on_log=log,
            on_error=error,
        )

        self.app = ApplicationLayer(
            node_id,
            self.datalink,
            on_inbox=lambda l: self._ui_callbacks.get("inbox", lambda _x: None)(l),
            on_outbox_update=lambda l: self._ui_callbacks.get("outbox", lambda _x: None)(l),
            on_log=log,
        )

    def _route_letter(self, letter) -> None:
        self.app.on_letter_received(letter)

    def _route_ack(self, ack) -> None:
        self.app.on_ack_received(ack)

    def _on_bytes(self, data: bytes, side: str) -> None:
        self.datalink.on_physical_data(data, side)

    def set_ui_callbacks(self, **kwargs) -> None:
        self._ui_callbacks.update(kwargs)

    def connect(self, baudrate: int = 115200) -> bool:
        self.physical.configure(baudrate)
        ok = self.physical.connect()
        if ok:
            self._log_lines.append(f"Узел {self.node_id}: физический канал установлен ({baudrate} бод)")
            cb = self._ui_callbacks.get("log")
            if cb:
                cb(self._log_lines[-1])
        return ok

    def disconnect(self) -> None:
        self.physical.disconnect()
