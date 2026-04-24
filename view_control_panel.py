import customtkinter as ctk
from port_scanner import PortScanner
from wave_list import WAVE_LIST


class ControlPanel(ctk.CTkFrame):

    POS = {
        # ウィジェット位置のテーブル
        # 起動・停止
        "run_btn": {
            "row": 0,
            "column": 0,
            "padx": (5, 10),
            "rowspan": 2,
            "sticky": "ns",
        },
        # comポート
        "com_label": {
            "row": 0,
            "column": 1,
            "padx": (5, 0),
            "pady": (0, 0),
            "sticky": "ws",
        },
        "com_dd": {"row": 1, "column": 1, "padx": (5, 0)},
        # ch
        "ch_label": {"row": 0, "column": 2, "padx": (10, 0), "sticky": "ws"},
        # "ch_entry": {"row": 1, "column": 2, "padx": (10, 0)},
        "ch_btn": {"row": 1, "column": 3, "padx": (3, 0)},
        # ch_dd
        "ch_dd": {"row": 1, "column": 2, "padx": (5, 0)},
        # cmd
        "cmd_label": {"row": 0, "column": 4, "padx": (10, 0), "sticky": "ws"},
        "cmd_entry": {"row": 1, "column": 4, "padx": (10, 0)},
        "cmd_btn": {"row": 1, "column": 5, "padx": (3, 0)},
        # rabel
        "test_label": {"row": 0, "column": 6, "padx": (10, 10), "sticky": "ws"},
    }

    def __init__(self, master, on_toggle, on_send_channel, on_send_cmd, settings):
        super().__init__(master)
        self.my_font = ctk.CTkFont(family="BIZ UDGothic", size=14, weight="bold")

        self.on_toggle = on_toggle
        self.on_send_channel = on_send_channel
        self.on_send_cmd = on_send_cmd

        self.settings = settings
        self._setup_ui()

    def _setup_ui(self):
        """UIパーツを配置する"""
        pos = self.POS

        # 開始・停止ボタン
        self.toggle_button = ctk.CTkButton(
            self, text="開始", width=80, command=self.on_toggle, font=self.my_font
        )
        self.toggle_button.grid(**pos["run_btn"])

        # COMポート選択
        ctk.CTkLabel(self, text="COMポート:", font=self.my_font).grid(
            **pos["com_label"]
        )
        self.port_var = ctk.StringVar(value=self.settings["port"])
        self.port_dropdown = ctk.CTkOptionMenu(
            self,
            width=100,
            variable=self.port_var,
            values=PortScanner.get_ports(),
            font=self.my_font,
            dropdown_font=self.my_font,
        )
        self.port_dropdown.grid(**pos["com_dd"])

        # チャンネル選択
        self.ch_var = ctk.StringVar(value=self.settings["channel"])
        self.ch_dd = ctk.CTkOptionMenu(
            self,
            width=100,
            variable=self.ch_var,
            values=[item["label"] for item in WAVE_LIST],
            font=self.my_font,
            dropdown_font=self.my_font,
        )
        self.ch_dd.grid(**pos["ch_dd"])

        # チャンネル入力
        ctk.CTkLabel(self, text="波形選択:", font=self.my_font).grid(**pos["ch_label"])
        self.channel_entry = ctk.CTkEntry(self, width=80, font=self.my_font)
        self.channel_entry.insert(0, self.settings["channel"])
        # self.channel_entry.grid(**pos["ch_entry"])
        self.ch_btn = ctk.CTkButton(
            self,
            text="選択",
            font=self.my_font,
            width=60,
            command=self._on_send_channel,
        )
        self.ch_btn.grid(**pos["ch_btn"])

        # マニュアルコマンド入力
        ctk.CTkLabel(self, text="CMD:", font=self.my_font).grid(**pos["cmd_label"])
        self.cmd_entry = ctk.CTkEntry(self, width=120, font=self.my_font)
        self.cmd_entry.insert(0, self.settings["cmd"])
        self.cmd_entry.grid(**pos["cmd_entry"])
        self.cmd_btn = ctk.CTkButton(
            self, text="送信", font=self.my_font, width=60, command=self._on_send_cmd
        )
        self.cmd_btn.grid(**pos["cmd_btn"])

        # 同期状態
        self.sync_label = ctk.CTkLabel(self, text="状態: 未同期", font=self.my_font)
        self.sync_label.grid(**pos["test_label"])

    def set_sync_status(self, value):
        self.sync_label.configure(text=f"状態: {value}")

    def get_port(self):
        return self.port_var.get()

    def get_channel(self):
        return self.ch_dd.get()

    def get_cmd(self):
        return self.cmd_entry.get()

    def set_running(self, is_running):
        if is_running:
            self.toggle_button.configure(text="停止")
            self.port_dropdown.configure(state="disabled")
            self.ch_btn.configure(state="normal")
            self.cmd_btn.configure(state="normal")
        else:
            self.toggle_button.configure(text="開始")
            self.port_dropdown.configure(state="normal")
            self.ch_btn.configure(state="disabled")
            self.cmd_btn.configure(state="disabled")
            self.sync_label.configure(text="状態:   --- ")

    # def _on_send_channel(self):
    #     self.on_send_channel(self.channel_entry.get())

    def _on_send_channel(self):
        self.on_send_channel(self.get_wave_cmd())

    def get_wave_cmd(self):
        selected = self.ch_dd.get()
        return next(item["cmd"] for item in WAVE_LIST if item["label"] == selected)

    def _on_send_cmd(self):
        self.on_send_cmd(self.cmd_entry.get())
