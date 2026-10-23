import tkinter as tk

import theme as T
from jig_state import Recv, Sync

RECV_VIEW = {
    Recv.STOPPED: ("停止中", T.GRAY),
    Recv.WAITING: ("受信待ち", T.GRAY),
    Recv.RECEIVING: ("受信中", T.GREEN),
    Recv.NO_DATA: ("受信なし", T.RED),
}

SYNC_VIEW = {
    Sync.UNKNOWN: ("同期 不明", T.GRAY),
    Sync.SYNCED: ("同期済み", T.GREEN),
    Sync.NOT_SYNCED: ("未同期", T.AMBER),
}


class Chip(tk.Frame):
    """色の付いた枠の状態表示"""

    def __init__(self, master):
        super().__init__(master, bg=T.BG, highlightthickness=2)
        self.label = tk.Label(self, bg=T.BG, font=T.font(18, True), padx=16, pady=2)
        self.label.pack()

    def set(self, text, color):
        self.configure(highlightbackground=color, highlightcolor=color)
        self.label.configure(text="●  " + text, fg=color)


class StatusBar(tk.Frame):
    """上の状態表示（受信・同期）"""

    def __init__(self, master):
        super().__init__(master, bg=T.BG)
        self.recv_chip = Chip(self)
        self.recv_chip.pack(side="left", padx=(0, 10))
        self.sync_chip = Chip(self)
        self.sync_chip.pack(side="left")
        tk.Label(self, text="5 秒分", bg=T.BG, fg=T.SUB, font=T.font(10)).pack(
            side="right", anchor="s"
        )

    def set(self, recv, sync):
        self.recv_chip.set(*RECV_VIEW[recv])
        self.sync_chip.set(*SYNC_VIEW[sync])


class InfoBox(tk.Frame):
    """名前と値の箱"""

    def __init__(self, master, name):
        super().__init__(
            master, bg=T.PANEL, highlightbackground=T.LINE, highlightthickness=1, padx=12, pady=4
        )
        tk.Label(self, text=name, bg=T.PANEL, fg=T.SUB, font=T.font(9)).pack(anchor="w")
        self.value = tk.Label(self, text="―", bg=T.PANEL, fg=T.TEXT, font=T.font(15, True))
        self.value.pack(anchor="w")

    def set(self, text, color=T.TEXT):
        self.value.configure(text=text, fg=color)


class InfoBar(tk.Frame):
    """下の数字（CH・パケット数・抜け・化け・基盤エラー・受信なし）"""

    def __init__(self, master):
        super().__init__(master, bg=T.BG)
        self.ch_box = InfoBox(self, "CH（基盤の値／送った値）")
        self.ch_box.pack(side="left", padx=(0, 8))
        self.pkt_box = InfoBox(self, "パケット")
        self.pkt_box.pack(side="left", padx=(0, 8))
        # 1 つでもあれば赤くする（合否は人が決める）
        self.lost_box = InfoBox(self, "抜け")
        self.lost_box.pack(side="left", padx=(0, 8))
        self.bad_box = InfoBox(self, "化け")
        self.bad_box.pack(side="left", padx=(0, 8))
        self.err_box = InfoBox(self, "基盤エラー")
        self.err_box.pack(side="left", padx=(0, 8))
        self.no_data_box = InfoBox(self, "受信なし")
        self.no_data_box.pack(side="left")

    def set(self, board_ch, sent_ch, packet_count, lost_count, bad_count, board_err_count, no_data_count):
        board = "―" if board_ch is None else str(board_ch)
        sent = "―" if sent_ch is None else sent_ch
        self.ch_box.set(f"{board}（送 {sent}）")
        self.pkt_box.set(f"{packet_count:,}")
        for box, count in (
            (self.lost_box, lost_count),
            (self.bad_box, bad_count),
            (self.err_box, board_err_count),
            (self.no_data_box, no_data_count),
        ):
            box.set(f"{count:,}", T.RED if count else T.TEXT)
