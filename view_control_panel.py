import customtkinter as ctk
from port_scanner import PortScanner


class ControlPanel(ctk.CTkFrame):

    def __init__(self, master, on_toggle, on_send_channel, on_send_cmd, settings):
        super().__init__(master)

        self.on_toggle = on_toggle
        self.on_send_channel = on_send_channel
        self.on_send_cmd = on_send_cmd

        # 保存済み設定を読み込む
        self.settings = settings

        self._setup_ui()

    def _setup_ui(self):
        """UIパーツを配置する"""

        # COMポート選択
        ctk.CTkLabel(self, text="COMポート:").pack(side="left", padx=5)
        self.port_var = ctk.StringVar(value=self.settings["port"])
        self.port_dropdown = ctk.CTkOptionMenu(
            self,
            variable=self.port_var,
            values=PortScanner.get_ports(),
        )
        self.port_dropdown.pack(side="left", padx=5)

        # 開始・停止ボタン
        self.toggle_button = ctk.CTkButton(
            self, text="開始", width=80, command=self.on_toggle
        )
        self.toggle_button.pack(side="left", padx=5)

        # チャンネル入力
        ctk.CTkLabel(self, text="CH:").pack(side="left", padx=5)
        self.channel_entry = ctk.CTkEntry(self, width=80)
        self.channel_entry.insert(0, self.settings["channel"])
        self.channel_entry.pack(side="left", padx=5)
        ctk.CTkButton(self, text="送信", width=60, command=self._on_send_channel).pack(
            side="left", padx=5
        )

        # マニュアルコマンド入力
        ctk.CTkLabel(self, text="CMD:").pack(side="left", padx=5)
        self.cmd_entry = ctk.CTkEntry(self, width=120)
        self.cmd_entry.pack(side="left", padx=5)
        ctk.CTkButton(self, text="送信", width=60, command=self._on_send_cmd).pack(
            side="left", padx=5
        )

    def get_port(self):
        """選択中のCOMポートを返す"""
        return self.port_var.get()

    def get_channel(self):
        """入力中のチャンネルを返す"""
        return self.channel_entry.get()

    def set_running(self, is_running):
        """実行状態に応じてUIを更新する"""
        if is_running:
            self.toggle_button.configure(text="停止")
            self.port_dropdown.configure(state="disabled")
        else:
            self.toggle_button.configure(text="開始")
            self.port_dropdown.configure(state="normal")

    def _on_send_channel(self):
        self.on_send_channel(self.channel_entry.get())

    def _on_send_cmd(self):
        self.on_send_cmd(self.cmd_entry.get())
