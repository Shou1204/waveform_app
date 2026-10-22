import tkinter as tk

import theme as T
from port_scanner import PortScanner
from wave_list import WAVE_LIST


class ControlPanel(tk.Frame):
    """左の操作パネル（① ポート → ② 受信 → ③ 波形を送る）"""

    def __init__(self, master, on_toggle, on_send_channel, on_send_cmd, extra_ports=()):
        super().__init__(
            master, bg=T.PANEL, width=240, highlightbackground=T.LINE, highlightthickness=1
        )
        self.pack_propagate(False)

        self.on_toggle = on_toggle
        self.on_send_channel = on_send_channel
        self.on_send_cmd = on_send_cmd
        self.extra_ports = list(extra_ports)

        self.wave_btns = {}
        self.selected_cmd = None
        self.manual_open = False

        self._setup_ui()
        self.set_running(False)

    def _step(self, text):
        tk.Label(self, text=text, bg=T.PANEL, fg=T.TEXT, font=T.font(13, True)).pack(
            anchor="w", padx=14, pady=(16, 6)
        )

    def _flat_btn(self, parent, **kwargs):
        return tk.Button(parent, relief="flat", bd=0, cursor="hand2", **kwargs)

    def _setup_ui(self):
        """UIパーツを配置する"""

        # ① ポート
        self._step("①  ポート")
        row = tk.Frame(self, bg=T.PANEL)
        row.pack(anchor="w", padx=14)
        self.port_var = tk.StringVar()
        self.port_menu = tk.OptionMenu(row, self.port_var, "")
        self.port_menu.configure(font=T.font(11), width=8)
        self.port_menu.pack(side="left")
        self.refresh_btn = self._flat_btn(
            row, text="↻ 探す", bg=T.BTN, fg=T.TEXT, font=T.font(10), padx=8,
            command=self.refresh_ports,
        )
        self.refresh_btn.pack(side="left", padx=6)
        self.refresh_ports()

        # ② 受信
        self._step("②  受信")
        self.run_btn = self._flat_btn(
            self, fg="#ffffff", font=T.font(16, True), pady=6, command=self.on_toggle
        )
        self.run_btn.pack(fill="x", padx=14)

        # ③ 波形を送る
        self._step("③  波形を送る")
        for item in WAVE_LIST:
            btn = self._flat_btn(
                self,
                text=f"{item['label']}　（{item['cmd']}）",
                font=T.font(12),
                pady=4,
                command=lambda cmd=item["cmd"]: self.on_send_channel(cmd),
            )
            btn.pack(fill="x", padx=14, pady=2)
            self.wave_btns[item["cmd"]] = btn
        self.set_selected_wave(None)

        # 手打ちコマンド（ふだんは畳んでおく）
        self.manual_toggle = self._flat_btn(
            self, text="▸ 手打ちコマンド", bg=T.PANEL, fg=T.SUB, font=T.font(10),
            activebackground=T.PANEL, anchor="w", command=self._toggle_manual,
        )
        self.manual_toggle.pack(side="bottom", anchor="w", padx=14, pady=(4, 12))

        self.manual_frame = tk.Frame(self, bg=T.PANEL)
        self.cmd_entry = tk.Entry(self.manual_frame, font=T.font(11), width=12)
        self.cmd_entry.pack(side="left", fill="x", expand=True)
        self.cmd_entry.bind("<Return>", lambda _e: self._on_send_cmd())
        self.cmd_btn = self._flat_btn(
            self.manual_frame, text="送信", bg=T.BTN, fg=T.TEXT, font=T.font(10), padx=8,
            command=self._on_send_cmd,
        )
        self.cmd_btn.pack(side="left", padx=(6, 0))

    def refresh_ports(self):
        """COMポートの一覧を読み直す"""
        ports = [p for p in PortScanner.get_ports() if p] + self.extra_ports
        menu = self.port_menu["menu"]
        menu.delete(0, "end")
        for port in ports:
            menu.add_command(label=port, command=tk._setit(self.port_var, port))
        if self.port_var.get() not in ports:
            self.port_var.set(ports[0] if ports else "")

    def get_port(self):
        return self.port_var.get()

    def set_running(self, is_running):
        """開始・停止に合わせて、押せるボタンを切り替える"""
        if is_running:
            self.run_btn.configure(text="■ 停止", bg=T.RED, activebackground=T.RED)
        else:
            self.run_btn.configure(text="▶ 開始", bg=T.GREEN, activebackground=T.GREEN)

        idle = "normal" if not is_running else "disabled"
        busy = "normal" if is_running else "disabled"
        self.port_menu.configure(state=idle)
        self.refresh_btn.configure(state=idle)
        for btn in self.wave_btns.values():
            btn.configure(state=busy)
        self.cmd_entry.configure(state=busy)
        self.cmd_btn.configure(state=busy)

    def set_selected_wave(self, cmd):
        """送った波形のボタンに色を付ける"""
        self.selected_cmd = cmd
        for c, btn in self.wave_btns.items():
            if c == cmd:
                btn.configure(bg=T.BLUE, fg="#ffffff", activebackground=T.BLUE,
                              activeforeground="#ffffff", disabledforeground="#d2e3fc")
            else:
                btn.configure(bg=T.BTN, fg=T.TEXT, activebackground="#dadce0",
                              activeforeground=T.TEXT, disabledforeground=T.BTN_DISABLED_TEXT)

    def _toggle_manual(self):
        self.manual_open = not self.manual_open
        if self.manual_open:
            self.manual_toggle.configure(text="▾ 手打ちコマンド")
            self.manual_frame.pack(side="bottom", fill="x", padx=14)
        else:
            self.manual_toggle.configure(text="▸ 手打ちコマンド")
            self.manual_frame.pack_forget()

    def _on_send_cmd(self):
        self.on_send_cmd(self.cmd_entry.get().strip())
