"""Константы протокола локальной кольцевой сети (вариант 18)."""

FLAG_BYTE = 0x7E
ESCAPE_BYTE = 0x7D
ESCAPE_XOR = 0x20

NODE_COUNT = 3
MAX_HOPS = NODE_COUNT
MAX_PAYLOAD = 4096

# Типы кадров канального уровня
FRAME_DATA = 0x01
FRAME_ACK_DELIVERED = 0x02
FRAME_ACK_READ = 0x03
FRAME_ERROR = 0x04
FRAME_CTRL = 0x05

# Статусы письма (прикладной уровень)
STATUS_DRAFT = "draft"
STATUS_SENT = "sent"
STATUS_DELIVERED = "delivered"
STATUS_READ = "read"

DEFAULT_BAUD = 115200
