#!/usr/bin/env python3
"""
Демонстрация кольцевой «почты» на одном ноутбуке.
Запускает три окна (узлы 1, 2, 3) с эмуляцией RS-232 кольца.

Использование:
  python3 demo.py
"""

from __future__ import annotations

import sys
import tkinter as tk

# Корень проекта в PYTHONPATH
import os

_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.node import NetworkNode
from src.physical.ring_simulator import get_shared_ring
from src.ui.main_window import NodeWindow


def main() -> None:
    ring = get_shared_ring()
    root = tk.Tk()
    root.withdraw()

    nodes = [NetworkNode(i) for i in (1, 2, 3)]
    windows: list[tk.Toplevel] = []

    for i, node in enumerate(nodes):
        win = tk.Toplevel(root)
        if i == 0:
            win.geometry("+40+40")
        elif i == 1:
            win.geometry("+480+40")
        else:
            win.geometry("+260+400")
        NodeWindow(win, node)
        windows.append(win)
        # Автоподключение для демо
        root.after(300 + i * 100, node.connect)

    def on_close() -> None:
        for n in nodes:
            n.disconnect()
        ring.stop()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    for w in windows:
        w.protocol("WM_DELETE_WINDOW", on_close)

    print("Демо запущено: три узла кольцевой сети.")
    print("1) Дождитесь статуса «Подключено» во всех окнах")
    print("2) В одном окне: Почта → Написать письмо → выберите адресата")
    print("3) В окне получателя откройте письмо двойным щелчком → «Прочитано»")
    print("4) В окне отправителя во «Исходящих» статус сменится на «прочитано»")

    root.mainloop()


if __name__ == "__main__":
    main()
