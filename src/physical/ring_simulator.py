"""Эмуляция физического кольца RS-232 между тремя узлами на одном компьютере."""

from __future__ import annotations

import queue
import threading
import time


class VirtualPort:
    """Виртуальный COM-порт."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._rx: queue.Queue[bytes] = queue.Queue()
        self._tx: queue.Queue[bytes] = queue.Queue()
        self._open = False
        self.baudrate = 115200
        self.bytesize = 8
        self.parity = "N"
        self.stopbits = 1

    @property
    def tx_queue(self) -> queue.Queue[bytes]:
        return self._tx

    @property
    def rx_queue(self) -> queue.Queue[bytes]:
        return self._rx

    def open(self) -> None:
        self._open = True

    def close(self) -> None:
        self._open = False

    @property
    def is_open(self) -> bool:
        return self._open

    def write(self, data: bytes) -> int:
        if not self._open:
            raise OSError("порт закрыт")
        delay = len(data) * 10.0 / max(self.baudrate, 9600)
        if delay > 0:
            time.sleep(min(delay, 0.02))
        self._tx.put(data)
        return len(data)

    def read(self, size: int = 1, timeout: float | None = 0.1) -> bytes:
        if not self._open:
            return b""
        deadline = None if timeout is None else time.monotonic() + timeout
        buf = bytearray()
        while len(buf) < size:
            remaining = None if deadline is None else max(0.0, deadline - time.monotonic())
            if deadline is not None and remaining == 0:
                break
            try:
                chunk = self._rx.get(timeout=remaining if remaining else 0.05)
                buf.extend(chunk)
            except queue.Empty:
                if buf:
                    break
        return bytes(buf)

    def in_waiting(self) -> int:
        return self._rx.qsize()


class RingSimulator:
    """Кольцо 1—2—3—1: два направления по двум портам каждого узла."""

    def __init__(self) -> None:
        self._nodes: dict[int, dict[str, VirtualPort]] = {
            nid: {"left": VirtualPort(f"N{nid}-LEFT"), "right": VirtualPort(f"N{nid}-RIGHT")}
            for nid in (1, 2, 3)
        }
        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []

    def _link(self, src: VirtualPort, dst: VirtualPort) -> None:
        def loop() -> None:
            while not self._stop.is_set():
                try:
                    data = src.tx_queue.get(timeout=0.05)
                except queue.Empty:
                    continue
                dst.rx_queue.put(data)

        t = threading.Thread(target=loop, daemon=True)
        t.start()
        self._threads.append(t)

    def start(self) -> None:
        if self._threads:
            return
        self._stop.clear()
        n = self._nodes
        # по часовой: right(N) -> left(N+1)
        self._link(n[1]["right"], n[2]["left"])
        self._link(n[2]["right"], n[3]["left"])
        self._link(n[3]["right"], n[1]["left"])
        # против часовой: left(N) -> right(N-1)
        self._link(n[1]["left"], n[3]["right"])
        self._link(n[2]["left"], n[1]["right"])
        self._link(n[3]["left"], n[2]["right"])

    def stop(self) -> None:
        self._stop.set()

    def get_ports(self, node_id: int) -> tuple[VirtualPort, VirtualPort]:
        p = self._nodes[node_id]
        return p["left"], p["right"]


_global_ring: RingSimulator | None = None
_ring_lock = threading.Lock()


def get_shared_ring() -> RingSimulator:
    global _global_ring
    with _ring_lock:
        if _global_ring is None:
            _global_ring = RingSimulator()
            _global_ring.start()
        return _global_ring
