import threading
import customtkinter as ctk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from serial_reader import SerialReader
from packet import PktKey


# 画面に表示するサンプル数
DISPLAY_SAMPLES = 300

# 更新間隔（ミリ秒）。10Hz = 100ms
UPDATE_INTERVAL_MS = 100

# COMポート
PORT = "COM7"


class WaveView(ctk.CTk):

    def __init__(self):
        super().__init__()
        self.title("波形表示")
        self.geometry("800x400")

        # 波形データのバッファ
        self.samples = []

        # スレッド間でsamplesを安全に操作するためのロック
        self.lock = threading.Lock()

        self._setup_plot()
        self._start_serial()
        self._update()

    def _setup_plot(self):
        """matplotlibのグラフを作成してウィンドウに埋め込む"""

        # 黒背景のグラフ
        self.fig, self.ax = plt.subplots(figsize=(8, 4), facecolor="black")
        self.ax.set_facecolor("black")
        self.ax.tick_params(colors="green")
        self.ax.spines[:].set_color("green")

        # 初期の空ラインを作成
        (self.line,) = self.ax.plot([], [], color="lime", linewidth=1)

        # Y軸の範囲を固定（ECGデータのbit0〜bit10 = 0〜2047）
        self.ax.set_ylim(0, 2047)
        self.ax.set_xlim(0, DISPLAY_SAMPLES)

        # グラフをウィンドウに埋め込む
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def _start_serial(self):
        """受信スレッドを開始する"""
        self.reader = SerialReader(port=PORT)

        # 初期化も含めて全部別スレッドで動かす
        self.serial_thread = threading.Thread(target=self._receive_loop, daemon=True)
        self.serial_thread.start()

    def _receive_loop(self):
        """受信スレッドで動く。パケットを受信してsamplesに追加する"""
        self.reader.open()
        self.reader.sync()

        while True:
            self.reader.sync()
            packet = self.reader.read()
            if packet:
                with self.lock:
                    self.samples.extend(packet[PktKey.ECG])

                    # 表示サンプル数を超えたらリセット（スイープ方式）
                    if len(self.samples) >= DISPLAY_SAMPLES:
                        self.samples = []

    def _update(self):
        """10Hzで波形を更新する"""

        # ロックを取得してsamplesをコピー
        with self.lock:
            current_samples = list(self.samples)

        # グラフを更新
        self.line.set_data(range(len(current_samples)), current_samples)
        self.canvas.draw()

        # 100ms後に再度呼び出す
        self.after(UPDATE_INTERVAL_MS, self._update)


if __name__ == "__main__":
    app = WaveView()
    app.mainloop()
