"""Кодирование и декодирование кадров канального уровня (HDLC-подобное кадрирование)."""

from __future__ import annotations

import struct
from dataclasses import dataclass

from .constants import (
    ESCAPE_BYTE,
    ESCAPE_XOR,
    FLAG_BYTE,
    MAX_HOPS,
    MAX_PAYLOAD,
)
from .crc import crc16_bytes, crc16_ccitt

# Заголовок: dst, src, type, hop, seq, len
HEADER_FMT = "!BBBBHH"
HEADER_SIZE = struct.calcsize(HEADER_FMT)


@dataclass
class Frame:
    dst: int
    src: int
    frame_type: int
    hop: int
    seq: int
    payload: bytes

    def header_bytes(self) -> bytes:
        return struct.pack(
            HEADER_FMT,
            self.dst,
            self.src,
            self.frame_type,
            self.hop,
            self.seq,
            len(self.payload),
        )

    def body_for_crc(self) -> bytes:
        return self.header_bytes() + self.payload


def stuff(data: bytes) -> bytes:
    out = bytearray()
    for b in data:
        if b == FLAG_BYTE or b == ESCAPE_BYTE:
            out.append(ESCAPE_BYTE)
            out.append(b ^ ESCAPE_XOR)
        else:
            out.append(b)
    return bytes(out)


def unstuff(data: bytes) -> bytes:
    out = bytearray()
    i = 0
    while i < len(data):
        if data[i] == ESCAPE_BYTE and i + 1 < len(data):
            out.append(data[i + 1] ^ ESCAPE_XOR)
            i += 2
        else:
            out.append(data[i])
            i += 1
    return bytes(out)


def encode_frame(frame: Frame) -> bytes:
    if len(frame.payload) > MAX_PAYLOAD:
        raise ValueError("payload слишком большой")
    body = frame.body_for_crc() + crc16_bytes(frame.body_for_crc())
    return bytes([FLAG_BYTE]) + stuff(body) + bytes([FLAG_BYTE])


class FrameDecoder:
    """Потоковый декодер кадров из байтового потока."""

    def __init__(self) -> None:
        self._buffer = bytearray()
        self._in_frame = False

    def feed(self, data: bytes) -> list[Frame]:
        frames: list[Frame] = []
        for byte in data:
            if byte == FLAG_BYTE:
                if self._in_frame and self._buffer:
                    raw = unstuff(bytes(self._buffer))
                    self._buffer.clear()
                    frame = parse_frame(raw)
                    if frame is not None:
                        frames.append(frame)
                self._in_frame = True
                continue
            if self._in_frame:
                self._buffer.append(byte)
        return frames


def parse_frame(raw: bytes) -> Frame | None:
    if len(raw) < HEADER_SIZE + 2:
        return None
    body, crc_recv = raw[:-2], raw[-2:]
    if crc16_bytes(body) != crc_recv:
        return None
    expected_crc = struct.unpack("!H", crc_recv)[0]
    if crc16_ccitt(body) != expected_crc:
        return None
    dst, src, ftype, hop, seq, plen = struct.unpack(HEADER_FMT, body[:HEADER_SIZE])
    payload = body[HEADER_SIZE : HEADER_SIZE + plen]
    if len(payload) != plen or hop > MAX_HOPS:
        return None
    return Frame(dst, src, ftype, hop, seq, payload)
