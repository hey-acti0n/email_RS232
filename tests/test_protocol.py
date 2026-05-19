"""Тесты CRC и кадрирования без GUI."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.common.constants import FRAME_DATA
from src.common.crc import crc16_ccitt
from src.common.frame import Frame, FrameDecoder, encode_frame, parse_frame


def test_crc_known():
    assert crc16_ccitt(b"123456789") == 0x29B1


def test_frame_roundtrip():
    f = Frame(dst=2, src=1, frame_type=FRAME_DATA, hop=0, seq=1, payload=b"hello")
    raw = encode_frame(f)
    dec = FrameDecoder()
    frames = dec.feed(raw)
    assert len(frames) == 1
    assert frames[0].payload == b"hello"


if __name__ == "__main__":
    test_crc_known()
    test_frame_roundtrip()
    print("OK")
