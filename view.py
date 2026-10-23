import queue
import re
import threading
import time
import tkinter as tk
from tkinter import messagebox

import theme as T
from jig_state import JigState
from serial_reader import SerialReader
from view_control_panel import ControlPanel
from view_status import InfoBar, StatusBar
from view_wave_chart import WaveChart

# 更新間隔（ミリ秒）。10Hz = 100ms
UPDATE_INTERVAL_MS = 100

APP_TITLE = "受信ユニット検査治具 v.1.0"


class View(tk.Tk):

    def __init__(self, serial_factory=None, extra_ports=(), clock=time.monotonic):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1000x620")
        self.minsize(940, 560)  # 下の数字の箱（6 つ）が欠けずに並ぶ幅
        self.configure(bg=T.BG)

        self.serial_factory = serial_factory
        self.clock = clock

        # 治具の状態（tk.Tk の state() と名前がぶつかるので jig とする）
        self.jig = JigState()

        # シリアル受信関連
        self.reader = None
        self.thread = None
        self.stop_event = None
        self.rx_queue = queue.Queue()

        self._setup_ui(extra_ports)
        self._update()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _setup_ui(self, extra_ports):
        """UIレイアウトを作成する"""
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # 操作パネル（左）
        self.control_panel = ControlPanel(
            self,
            on_toggle=self._on_toggle,
            on_send_channel=self._on_send_channel,
            on_send_cmd=self._on_send_cmd,
            extra_ports=extra_ports,
        )
        self.control_panel.grid(row=0, column=0, sticky="ns", padx=(12, 0), pady=12)

        # 状態・波形・数字（右）
        right = tk.Frame(self, bg=T.BG)
        right.grid(row=0, column=1, sticky="nsew", padx=12, pady=12)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        self.status_bar = StatusBar(right)
        self.status_bar.grid(row=0, column=0, sticky="we")
        self.wave_chart = WaveChart(right)
        self.wave_chart.grid(row=1, column=0, sticky="nsew", pady=8)
        self.info_bar = InfoBar(right)
        self.info_bar.grid(row=2, column=0, sticky="we")

    # ------------------------------------------------------------ 開始・停止

    def _on_toggle(self):
        """開始・停止ボタンの処理"""
        if self.reader:
            self._stop()
        else:
            self._start()

    def _start(self):
        """受信を開始する。ポートを開けなければ知らせて止まったままにする"""
        port = self.control_panel.get_port()
        if not port:
            messagebox.showwarning(APP_TITLE, "COM ポートが見つかりません。\nUSB シリアル変換器をつないで「↻ 探す」を押してください。")
            return

        reader = SerialReader(port=port, serial_factory=self.serial_factory)
        try:
            reader.open()
        except Exception as e:
            messagebox.showerror(
                APP_TITLE,
                f"{port} を開けませんでした。\n"
                "ほかのアプリ（Tera Term など）が使っていないか、変換器が抜けていないかを確かめてください。\n\n"
                f"{e}",
            )
            return

        self.reader = reader
        self.rx_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.thread = threading.Thread(
            target=self._receive_loop,
            args=(reader, self.stop_event, self.rx_queue),
            daemon=True,
        )
        self.jig.start(self.clock())
        self.control_panel.set_selected_wave(None)
        self.control_panel.set_running(True)
        self.thread.start()

    def _stop(self):
        """受信を停止する"""
        if self.stop_event:
            self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=1)
        if self.reader:
            self.reader.close()
        self.reader = None
        self.thread = None
        self.stop_event = None
        # 止める前に入った受信やエラーを持ち越さない
        self.rx_queue = queue.Queue()
        self.jig.stop()
        self.control_panel.set_running(False)

    def _fail(self, error):
        """受信や送信が失敗したら、止めて知らせる"""
        self._stop()
        messagebox.showerror(
            APP_TITLE,
            "受信が止まりました。\nUSB シリアル変換器が抜けていないかを確かめ、もう一度「開始」を押してください。\n\n"
            f"{error}",
        )

    @staticmethod
    def _receive_loop(reader, stop_event, rx_queue):
        """受信スレッドで動く。パケットをキューに入れるだけで、画面には触らない"""
        try:
            while not stop_event.is_set():
                bad = reader.parser.bad_count
                for packet in reader.read_packets():
                    rx_queue.put(("packet", packet))
                if reader.parser.bad_count != bad:
                    rx_queue.put(("bad", reader.parser.bad_count - bad))
        except Exception as e:
            if not stop_event.is_set():
                rx_queue.put(("error", e))

    # ------------------------------------------------------------ 送信

    def _on_send_channel(self, cmd):
        """チャンネル変更命令を送信する（同じボタンをもう一度押しても送る）"""
        if not self.reader:
            return
        try:
            self.reader.send_ch(cmd)
        except Exception as e:
            self._fail(e)
            return
        self.jig.sent(cmd)
        self.control_panel.set_selected_wave(cmd)

    def _on_send_cmd(self, value):
        """手打ちのコマンドを送信する"""
        if not self.reader or value == "":
            return
        if not (value.isascii() and value.isprintable()):
            # 打ち間違いで受信まで止めないよう、送る前に断る
            messagebox.showwarning(APP_TITLE, "コマンドは半角の英数字で入れてください。")
            return
        try:
            self.reader.send_cmd(value)
        except Exception as e:
            self._fail(e)
            return
        # チャンネル（先頭か、前の項目の数字の直後の C＋4桁）が入っていれば、送った値として覚える
        m = re.search(r"(?:^|(?<=\d))C(\d{4})(?!\d)", value)
        if m:
            self.jig.sent(m.group(1))
            self.control_panel.set_selected_wave(m.group(1))

    # ------------------------------------------------------------ 定期更新

    def _update(self):
        """10Hzで受信したパケットを取り込み、画面を更新する"""
        try:
            self._refresh()
        finally:
            # 途中で例外が出ても、定期更新は止めない（画面が固まって前の波形が残らないように）
            self._update_id = self.after(UPDATE_INTERVAL_MS, self._update)

    def _refresh(self):
        now = self.clock()
        while True:
            try:
                kind, item = self.rx_queue.get_nowait()
            except queue.Empty:
                break
            if kind == "error":
                self._fail(item)
                break
            if kind == "bad":
                self.jig.on_bad(item)
            else:
                self.jig.on_packet(item, now)

        self.jig.tick(now)
        self.status_bar.set(self.jig.recv(now), self.jig.sync(now))
        self.info_bar.set(
            self.jig.board_ch,
            self.jig.sent_ch,
            self.jig.packet_count,
            self.jig.lost_count,
            self.jig.bad_count,
            self.jig.board_err_count,
            self.jig.no_data_count,
        )
        self.wave_chart.show(self.jig.wave, self.jig.cursor)

    def _on_close(self):
        """ウィンドウを閉じるときの処理"""
        self.after_cancel(self._update_id)
        self._stop()
        self.quit()  # mainloopを止める
        self.destroy()
