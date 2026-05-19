"""Графический интерфейс узла: входящие, исходящие, журнал, настройки COM."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, scrolledtext, simpledialog, ttk

from src.application.mail import Letter
from src.common.constants import NODE_COUNT, STATUS_DELIVERED, STATUS_READ, STATUS_SENT
from src.node import NetworkNode

STATUS_RU = {
    "draft": "черновик",
    "sent": "отправлено",
    "delivered": "доставлено",
    "read": "прочитано",
}


class NodeWindow:
    def __init__(self, root: tk.Tk, node: NetworkNode) -> None:
        self.root = root
        self.node = node
        self.root.title(f"Почта узла {node.node_id} — локальная кольцевая сеть")
        self.root.geometry("900x620")
        self.root.minsize(700, 500)

        node.set_ui_callbacks(
            inbox=self._add_inbox,
            outbox=self._update_outbox,
            log=self._append_log,
            error=lambda m: messagebox.showerror("Ошибка сети", m),
        )

        self._build_menu()
        self._build_toolbar()
        self._build_panels()
        self._append_log(f"Узел {node.node_id} готов. Подключите канал (меню Сеть).")

    def _build_menu(self) -> None:
        menubar = tk.Menu(self.root)
        net = tk.Menu(menubar, tearoff=0)
        net.add_command(label="Подключить канал", command=self._connect)
        net.add_command(label="Отключить канал", command=self._disconnect)
        net.add_separator()
        net.add_command(label="Параметры COM...", command=self._com_settings)
        menubar.add_cascade(label="Сеть", menu=net)
        mail = tk.Menu(menubar, tearoff=0)
        mail.add_command(label="Написать письмо...", command=self._compose)
        menubar.add_cascade(label="Почта", menu=mail)
        self.root.config(menu=menubar)

    def _build_toolbar(self) -> None:
        bar = ttk.Frame(self.root, padding=4)
        bar.pack(fill=tk.X)
        self.status_var = tk.StringVar(value="Отключено")
        ttk.Label(bar, textvariable=self.status_var).pack(side=tk.LEFT)
        ttk.Button(bar, text="Подключить", command=self._connect).pack(side=tk.RIGHT, padx=2)
        ttk.Button(bar, text="Написать", command=self._compose).pack(side=tk.RIGHT, padx=2)

    def _build_panels(self) -> None:
        paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)

        # Входящие
        inbox_frame = ttk.LabelFrame(paned, text="Входящие", padding=4)
        paned.add(inbox_frame, weight=1)
        self.inbox_tree = ttk.Treeview(
            inbox_frame, columns=("from", "subject", "status"), show="headings", height=12
        )
        for col, title, w in (
            ("from", "От", 50),
            ("subject", "Тема", 120),
            ("status", "Статус", 80),
        ):
            self.inbox_tree.heading(col, text=title)
            self.inbox_tree.column(col, width=w)
        self.inbox_tree.pack(fill=tk.BOTH, expand=True)
        self.inbox_tree.bind("<Double-1>", self._open_inbox_letter)

        # Исходящие
        out_frame = ttk.LabelFrame(paned, text="Исходящие", padding=4)
        paned.add(out_frame, weight=1)
        self.outbox_tree = ttk.Treeview(
            out_frame, columns=("to", "subject", "status"), show="headings", height=12
        )
        for col, title, w in (
            ("to", "Кому", 50),
            ("subject", "Тема", 120),
            ("status", "Статус", 100),
        ):
            self.outbox_tree.heading(col, text=title)
            self.outbox_tree.column(col, width=w)
        self.outbox_tree.pack(fill=tk.BOTH, expand=True)

        # Журнал
        log_frame = ttk.LabelFrame(self.root, text="Протокол событий сети", padding=4)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def _append_log(self, msg: str) -> None:
        def do() -> None:
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, msg + "\n")
            self.log_text.see(tk.END)
            self.log_text.config(state=tk.DISABLED)

        self.root.after(0, do)

    def _connect(self) -> None:
        if self.node.connect():
            self.status_var.set(f"Подключено | {self.node.physical.baudrate} бод")
        else:
            messagebox.showerror("Сеть", "Не удалось открыть канал")

    def _disconnect(self) -> None:
        self.node.disconnect()
        self.status_var.set("Отключено")

    def _com_settings(self) -> None:
        baud = simpledialog.askinteger(
            "Параметры COM",
            "Скорость (бод):",
            initialvalue=self.node.physical.baudrate,
            minvalue=9600,
            maxvalue=921600,
            parent=self.root,
        )
        if baud:
            self.node.physical.configure(baud)
            self._append_log(f"Параметры COM: {baud} 8N1")

    def _compose(self) -> None:
        if not self.node.physical.connected:
            messagebox.showwarning("Почта", "Сначала подключите сеть (меню Сеть → Подключить)")
            return
        win = tk.Toplevel(self.root)
        win.title("Новое письмо")
        win.geometry("420x320")
        ttk.Label(win, text="Адресат:").pack(anchor=tk.W, padx=8, pady=4)
        recipients = [i for i in range(1, NODE_COUNT + 1) if i != self.node.node_id]
        rec_var = tk.IntVar(value=recipients[0])
        for r in recipients:
            ttk.Radiobutton(win, text=f"Узел {r}", variable=rec_var, value=r).pack(anchor=tk.W, padx=16)
        ttk.Label(win, text="Тема:").pack(anchor=tk.W, padx=8)
        subj = ttk.Entry(win, width=50)
        subj.pack(padx=8, fill=tk.X)
        ttk.Label(win, text="Текст:").pack(anchor=tk.W, padx=8)
        body = scrolledtext.ScrolledText(win, height=8)
        body.pack(padx=8, pady=4, fill=tk.BOTH, expand=True)

        def send() -> None:
            text = body.get("1.0", tk.END).strip()
            if not text:
                messagebox.showwarning("Почта", "Введите текст письма")
                return
            self.node.app.send_mail(rec_var.get(), subj.get() or "(без темы)", text)
            win.destroy()

        ttk.Button(win, text="Отправить", command=send).pack(pady=8)

    def _add_inbox(self, letter: Letter) -> None:
        def do() -> None:
            self.inbox_tree.insert(
                "",
                tk.END,
                iid=letter.letter_id,
                values=(letter.sender, letter.subject, STATUS_RU.get(letter.status, letter.status)),
            )

        self.root.after(0, do)

    def _update_outbox(self, letter: Letter) -> None:
        def do() -> None:
            iid = letter.letter_id
            vals = (letter.recipient, letter.subject, STATUS_RU.get(letter.status, letter.status))
            if self.outbox_tree.exists(iid):
                self.outbox_tree.item(iid, values=vals)
            else:
                self.outbox_tree.insert("", tk.END, iid=iid, values=vals)

        self.root.after(0, do)

    def _open_inbox_letter(self, _event: tk.Event) -> None:
        sel = self.inbox_tree.selection()
        if not sel:
            return
        lid = sel[0]
        letter = self.node.app.inbox.get(lid)
        if not letter:
            return
        win = tk.Toplevel(self.root)
        win.title(f"Письмо от узла {letter.sender}")
        win.geometry("450x300")
        ttk.Label(win, text=f"Тема: {letter.subject}", font=("", 11, "bold")).pack(anchor=tk.W, padx=8, pady=6)
        txt = scrolledtext.ScrolledText(win, height=10)
        txt.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)
        txt.insert("1.0", letter.body)
        txt.config(state=tk.DISABLED)

        def on_open() -> None:
            self.node.app.open_letter(lid)
            self.inbox_tree.item(lid, values=(letter.sender, letter.subject, STATUS_RU["read"]))
            win.destroy()

        ttk.Button(win, text="Отметить прочитанным и уведомить отправителя", command=on_open).pack(pady=8)
