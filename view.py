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

        # 保存済み設定を読み込む
        self.settings = SaveSet.load()
        print(self.settings)

        # 同期状態
        self.latest_sync_sts = None  # UIに反映する確定値

        self._setup_ui()
        self._update()

        # ウィンドウを閉じるときに設定を保存する
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _setup_ui(self):
        """UIレイアウトを作成する"""

        self.columnconfigure(0, weight=1)  # 列0が余ったスペースをすべて取る
        self.rowconfigure(1, weight=1)

        # 波形表示エリア（下部）
        self.wave_chart = WaveChart(master=self)
        self.wave_chart.grid(row=1, column=0, sticky="nsew")

        # 操作パネル（上部）
        self.control_panel = ControlPanel(
            master=self,
            on_toggle=self._on_toggle,
            on_send_channel=self._on_send_channel,
            on_send_cmd=self._on_send_cmd,
            settings=self.settings,
        )
        self.control_panel.grid(row=0, column=0, pady=(10, 10), sticky="wns")

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
        if self.reader:
            self.reader.close()
        self.control_panel.set_running(False)

    def _receive_loop(self):
        """受信スレッドで動く。パケットを受信してwave_chartに追加する"""
        self.reader.open()
        self.reader.sync()

        while self.is_running:
            self.reader.sync()
            packet = self.reader.read()

            if packet:
                new_sts = packet[PktKey.SYNC_STS]

                with self.lock:
                    self.wave_chart.add_samples(packet[PktKey.ECG])
                    self.latest_sync_sts = new_sts

    def _on_send_channel(self, value):
        """チャンネル変更命令を送信する"""
        print(f"CH送信: {value}")
        self.reader.send_ch(value)

    def _on_send_cmd(self, value):
        """マニュアルコマンドを送信する"""
        print(f"CMD送信: {value}")
        if value == "":
            print("## cmd not imput")
            return
        self.reader.send_cmd(value)

    def _update(self):
        """10Hzで波形を更新する"""
        with self.lock:
            self.wave_chart.update()
            sts = self._get_sync_sts(self.latest_sync_sts)  # 同期状態

        if sts is not None:
            self.control_panel.set_sync_status(sts)

        self._update_id = self.after(UPDATE_INTERVAL_MS, self._update)

    def _get_sync_sts(self, sts):
        if self.is_running:
            match sts:
                case 0 | 1 | 2:
                    return "未同期"
                case 3:
                    return "同期済"

    def _on_close(self):
        """ウィンドウを閉じるときの処理"""
        # after()の定期処理をキャンセルする
        self.after_cancel(self._update_id)

        # 設定を保存する
        SaveSet.save(
            port=self.control_panel.get_port(),
            channel=self.control_panel.get_channel(),
            cmd=self.control_panel.get_cmd(),
        )

        # 受信を停止してウィンドウを閉じる
        self._stop()
        self.quit()  # mainloopを止める
        self.destroy()


if __name__ == "__main__":
    app = View()
    app.mainloop()
