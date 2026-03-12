import threading
import customtkinter as ctk

from serial_reader import SerialReader
from view_wave_chart import WaveChart
from view_control_panel import ControlPanel
from packet import PktKey
from save_set import SaveSet

# 更新間隔（ミリ秒）。10Hz = 100ms
UPDATE_INTERVAL_MS = 100


class View(ctk.CTk):

    def __init__(self):
        super().__init__()
        self.title("波形表示")
        self.geometry("800x500")

        # シリアル受信関連
        self.reader = None
        self.is_running = False
        self.lock = threading.Lock()

        self._setup_ui()
        self._update()

        # ウィンドウを閉じるときに設定を保存する
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _setup_ui(self):
        """UIレイアウトを作成する"""

        # 波形表示エリア（上部）
        self.wave_chart = WaveChart(master=self)
        self.wave_chart.pack(fill="both", expand=True, padx=10, pady=5)

        # 操作パネル（下部）
        self.control_panel = ControlPanel(
            master=self,
            on_toggle=self._on_toggle,
            on_send_channel=self._on_send_channel,
            on_send_cmd=self._on_send_cmd,
        )
        self.control_panel.pack(fill="x", padx=10, pady=5)

    def _on_toggle(self):
        """開始・停止ボタンの処理"""
        if self.is_running:
            self._stop()
        else:
            self._start()

    def _start(self):
        """受信を開始する"""
        self.reader = SerialReader(port=self.control_panel.get_port())
        self.is_running = True
        self.control_panel.set_running(True)

        self.serial_thread = threading.Thread(target=self._receive_loop, daemon=True)
        self.serial_thread.start()

    def _stop(self):
        """受信を停止する"""
        self.is_running = False
        self.control_panel.set_running(False)
        if self.reader:
            self.reader.close()

    def _receive_loop(self):
        """受信スレッドで動く。パケットを受信してwave_chartに追加する"""
        self.reader.open()
        self.reader.sync()

        while self.is_running:
            self.reader.sync()
            packet = self.reader.read()
            if packet:
                with self.lock:
                    self.wave_chart.add_samples(packet[PktKey.ECG])

    def _on_send_channel(self, value):
        """チャンネル変更命令を送信する（未実装）"""
        print(f"CH送信: {value}")

    def _on_send_cmd(self, value):
        """マニュアルコマンドを送信する（未実装）"""
        print(f"CMD送信: {value}")

    def _update(self):
        """10Hzで波形を更新する"""
        with self.lock:
            self.wave_chart.update()

        self.after(UPDATE_INTERVAL_MS, self._update)

    def _on_close(self):
        """ウィンドウを閉じるときの処理"""
        # 設定を保存する
        SaveSet.save(
            port=self.control_panel.get_port(),
            channel=self.control_panel.get_channel(),
        )

        # 受信を停止してウィンドウを閉じる
        self._stop()
        self.destroy()


if __name__ == "__main__":
    app = View()
    app.mainloop()
