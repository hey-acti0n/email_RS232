"""CRC-16-CCITT (полином 0x1021, init 0xFFFF) — циклический контрольный код."""


def crc16_ccitt(data: bytes, init: int = 0xFFFF) -> int:
    crc = init
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


def crc16_bytes(data: bytes) -> bytes:
    value = crc16_ccitt(data)
    return bytes([(value >> 8) & 0xFF, value & 0xFF])
