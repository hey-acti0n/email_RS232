"""Физический уровень: работа с COM-портом или виртуальным портом кольца."""

from __future__ import annotations

import threading
from typing import Callable

from .ring_simulator import VirtualPort

try:
    import serial
except ImportError:
    serial = None  # type: ignore


class PhysicalLayer:
    def __init__(
        self,
        node_id: int,
        on_bytes: Callable[[bytes, str], None],
        left: VirtualPort | None = None,
        right: VirtualPort | None = None,
        use_serial: bool = False,
        serial_left: str | None = None,
        serial_right: str | None = None,
    ) -> None:
        self.node_id = node_id
        self._on_bytes = on_bytes
        self._left = left
        self._right = right
        self._use_serial = use_serial
        self._ser_left = None
        self._ser_right = None
        self._serial_left_name = serial_left
        self._serial_right_name = serial_right
        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []
        self.connected = False
        self.baudrate = 115200

    def configure(self, baudrate: int, bytesize: int = 8, parity: str = "N", stopbits: int = 1) -> None:
        self.baudrate = baudrate
        for port in (self._left, self._right):
            if port is not None:
                port.baudrate = baudrate
                port.bytesize = bytesize
                port.parity = parity
                port.stopbits = stopbits

    def connect(self) -> bool:
        try:
            if self._use_serial and serial:
                self._ser_left = serial.Serial(self._serial_left_name, self.baudrate, timeout=0.1)
                self._ser_right = serial.Serial(self._serial_right_name, self.baudrate, timeout=0.1)
            else:
                if self._left is None or self._right is None:
                    raise OSError("виртуальные порты не заданы")
                self._left.open()
                self._right.open()
            self._stop.clear()
            if self._use_serial and serial:
                self._threads = [
                    threading.Thread(target=self._read_loop_serial, args=(self._ser_left, "left"), daemon=True),
                    threading.Thread(target=self._read_loop_serial, args=(self._ser_right, "right"), daemon=True),
                ]
            else:
                self._threads = [
                    threading.Thread(target=self._read_loop_virtual, args=(self._left, "left"), daemon=True),
                    threading.Thread(target=self._read_loop_virtual, args=(self._right, "right"), daemon=True),
                ]
            for t in self._threads:
                t.start()
            self.connected = True
            return True
        except Exception as exc:
            self._last_error = str(exc)
            self.connected = False
            return False

    def disconnect(self) -> None:
        self._stop.set()
        if self._left:
            self._left.close()
        if self._right:
            self._right.close()
        if self._ser_left:
            self._ser_left.close()
        if self._ser_right:
            self._ser_right.close()
        self.connected = False

    def send(self, data: bytes, direction: str) -> None:
        port = self._left if direction == "left" else self._right
        if self._use_serial and serial:
            ser = self._ser_left if direction == "left" else self._ser_right
            if ser and ser.is_open:
                ser.write(data)
        elif port and port.is_open:
            port.write(data)

    def _read_loop_virtual(self, port: VirtualPort, side: str) -> None:
        while not self._stop.is_set():
            if not port.is_open:
                break
            chunk = port.read(256, timeout=0.1)
            if chunk:
                self._on_bytes(chunk, side)

    def _read_loop_serial(self, ser: "serial.Serial", side: str) -> None:
        while not self._stop.is_set():
            if not ser.is_open:
                break
            n = ser.in_waiting
            if n:
                self._on_bytes(ser.read(n), side)
            else:
                self._stop.wait(0.05)
