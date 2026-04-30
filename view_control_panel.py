import customtkinter as ctk
from port_scanner import PortScanner
from wave_list import WAVE_LIST


class ControlPanel(ctk.CTkFrame):

    COLOR_SUCCESS = "#03a53e"
    COL_TXT1 = "#b9b9b9"

    # --------------------------------------------------------
    #               ウィジェット位置のテーブル
    # --------------------------------------------------------
    POS = {
        ## comポート
        "com_label": {
            "row": 0,
            "column": 0,
            "padx": (10, 10),
            "sticky": "w",
        },
        ## 起動・停止
        "run_label": {
            "row": 1,
            "column": 0,
            "padx": (10, 10),
            "sticky": "ns",
        },
        "run_btn": {
            "row": 1,
            "column": 1,
            "padx": (15, 10),
            "sticky": "ns",
        },
        "com_dd": {"row": 0, "column": 1, "padx": (0, 0)},
        ## コマンド
        "cmd_label": {"row": 0, "column": 3, "padx": (10, 0), "sticky": "ws"},
        "cmd_entry": {"row": 0, "column": 4, "padx": (10, 0), "sticky": "e"},
        "cmd_btn": {"row": 0, "column": 5, "padx": (3, 0), "sticky": "w"},
        ## 波形選択
        "select_label": {"row": 1, "column": 3, "padx": (10, 0), "sticky": "ws"},
        "select_btn": {
            "row": 1,
            "column": 4,
            "padx": (10, 10),
            "sticky": "ns",
        },
        ## 同期状態
        "sync_label": {"row": 0, "column": 7, "padx": (10, 5), "sticky": "e"},
        "sync_mark": {"row": 0, "column": 8, "padx": (10, 5), "sticky": "e"},
        "sync_sts_label": {"row": 0, "column": 9, "padx": (5, 10), "sticky": "w"},
        ## dummy
        "dummy": {"row": 0, "column": 6, "padx": (5, 10), "sticky": "we"},
    }

    def __init__(
        self, master, on_toggle, on_send_channel, on_send_cmd, settings, **kwargs
    ):
        super().__init__(master, **kwargs)
        self.my_font = ctk.CTkFont(family="BIZ UDGothic", size=12, weight="bold")

        self.LABEL_SET1 = {"text_color": "#A0A0A0", "font": self.my_font}

        self.on_toggle = on_toggle
        self.on_send_channel = on_send_channel
        self.on_send_cmd = on_send_cmd

        self.settings = settings
        self._setup_ui()

    def _setup_ui(self):
        """UIパーツを配置する"""
        pos = self.POS

        # グリッド幅調整用ダミーボックス
        self.dummy_box = ctk.CTkFrame(self, width=20, height=20, fg_color="transparent")
        self.dummy_box.grid(**pos["dummy"])

        # COMポート選択
        self.port_var = ctk.StringVar(value=self.settings["port"])
        ## ラベル
        ctk.CTkLabel(self, text="COMポート", **self.LABEL_SET1).grid(**pos["com_label"])
        ## DD
        self.port_dropdown = ctk.CTkOptionMenu(
            self,
            width=100,
            height=20,
            variable=self.port_var,
            values=PortScanner.get_ports(),
            font=self.my_font,
            dropdown_font=self.my_font,
        )
        self.port_dropdown.grid(**pos["com_dd"])

        # 通信開始・停止
        ## ラベル
        self.power_label = ctk.CTkLabel(self, text="停止/通信開始", **self.LABEL_SET1)
        self.power_label.grid(**pos["run_label"])
        ## ボタン
        self.power_tgl_btn = ctk.CTkSwitch(
            self,
            text="",
            switch_width=36,
            switch_height=18,
            corner_radius=12,
            border_width=2,
            progress_color=self.COLOR_SUCCESS,
            button_color="#E0E0E0",
            button_hover_color="#FFFFFF",
            command=self.on_toggle,
            font=self.my_font,
        )
        self.power_tgl_btn.grid(**pos["run_btn"])

        # コマンド
        ctk.CTkLabel(self, text="コマンド", **self.LABEL_SET1).grid(**pos["cmd_label"])
        self.cmd_entry = ctk.CTkEntry(self, width=160, height=20, font=self.my_font)
        self.cmd_entry.insert(0, self.settings["cmd"])
        self.cmd_entry.grid(**pos["cmd_entry"])
        self.cmd_btn = ctk.CTkButton(
            self,
            text="送信",
            font=self.my_font,
            width=40,
            height=20,
            command=self._on_send_cmd,
        )
        self.cmd_btn.grid(**pos["cmd_btn"])

        # 波形選択
        ## ラベル
        ctk.CTkLabel(self, text="波形選択", **self.LABEL_SET1).grid(
            **pos["select_label"]
        )
        ## ボタン
        self.select_wave_btn = ctk.CTkSegmentedButton(
            self,
            values=[item["label"] for item in WAVE_LIST],
            font=self.my_font,
            # **color,
            command=self._on_send_channel,
        )
        self.select_wave_btn.grid(**pos["select_btn"])
        self.select_wave_btn.set("未設定")  # 初期値

        # 同期状態
        ## ラベル
        self.sync_label = ctk.CTkLabel(self, text="同期状態", **self.LABEL_SET1)
        self.sync_label.grid(**pos["sync_label"])
        ## ●
        self.sync_mark = ctk.CTkLabel(self, text="●", font=self.my_font)
        self.sync_mark.grid(**pos["sync_mark"])
        ## 状態ラベル
        self.sync_sts_chr = ctk.CTkLabel(
            self,
            text="---",
            font=self.my_font,
        )
        self.sync_sts_chr.grid(**pos["sync_sts_label"])

    def set_sync_status(self, value):

        match value:
            case 0:
                self.sync_sts_chr.configure(text="未")
                self.sync_mark.configure(text_color="#FF6B6B")
            case 1:
                self.sync_sts_chr.configure(text="済")
                self.sync_mark.configure(text_color="#00ff5e")

    def get_port(self):
        return self.port_var.get()

    def get_cmd(self):
        return self.cmd_entry.get()

    def set_running(self, is_running):
        if is_running:
            self.port_dropdown.configure(state="disabled")
            self.cmd_btn.configure(state="normal")
            self.select_wave_btn.configure(state="normal")
        else:
            self.port_dropdown.configure(state="normal")
            self.cmd_btn.configure(state="disabled")
            self.select_wave_btn.configure(state="disabled")
            self.sync_sts_chr.configure(
                text="---",
            )
            self.sync_mark.configure(text_color="#656565")

    def _on_send_channel(self, val):
        cmd = next(item["cmd"] for item in WAVE_LIST if item["label"] == val)
        self.on_send_channel(cmd)

    def _on_send_cmd(self):
        self.on_send_cmd(self.cmd_entry.get())
