#!/usr/bin/env python3
"""Запуск одного узла (для трёх процессов или реальных COM-портов)."""

from __future__ import annotations

import argparse
import os
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import tkinter as tk

from src.node import NetworkNode
from src.physical.ring_simulator import get_shared_ring
from src.ui.main_window import NodeWindow


def main() -> None:
    p = argparse.ArgumentParser(description="Узел кольцевой почтовой сети")
    p.add_argument("--node", type=int, choices=(1, 2, 3), required=True, help="ID узла 1..3")
    p.add_argument("--demo-ring", action="store_true", help="Виртуальное кольцо (общий симулятор)")
    p.add_argument("--serial-left", default=None, help="COM-порт слева (Windows/Linux)")
    p.add_argument("--serial-right", default=None, help="COM-порт справа")
    args = p.parse_args()

    use_serial = bool(args.serial_left and args.serial_right)
    vports = None
    if args.demo_ring and not use_serial:
        vports = get_shared_ring().get_ports(args.node)

    root = tk.Tk()
    node = NetworkNode(
        args.node,
        virtual_ports=vports,
        use_serial=use_serial,
        serial_left=args.serial_left,
        serial_right=args.serial_right,
    )
    NodeWindow(root, node)
    root.mainloop()


if __name__ == "__main__":
    main()
