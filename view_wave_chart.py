import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import customtkinter as ctk

# 画面に表示するサンプル数
DISPLAY_SAMPLES = 1200


class WaveChart(ctk.CTkFrame):

    def __init__(self, master):
        super().__init__(master)

        # 波形データのバッファ
        self.samples = []

        self._setup_plot()

    def _setup_plot(self):
        """matplotlibのグラフを作成してウィンドウに埋め込む"""

        # 黒背景のグラフ
        self.fig, self.ax = plt.subplots(figsize=(8, 4), facecolor="black")  # 大背景
        self.ax.set_facecolor("black")  # グラフ背景
        self.ax.tick_params(colors="ivory")  # メモリ
        self.ax.spines[:].set_color("ivory")  # 枠線

        # 初期の空ラインを作成
        (self.line,) = self.ax.plot([], [], color="lime", linewidth=1)

        # Y軸の範囲を固定（ECGデータのbit0〜bit10 = 0〜2047）
        self.ax.set_ylim(-2047, 2047)
        self.ax.set_xlim(0, DISPLAY_SAMPLES)

        # グラフをウィンドウに埋め込む
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def add_samples(self, new_samples):
        """ECGデータを追加する"""
        self.samples.extend(new_samples)

        # 表示サンプル数を超えたらリセット（スイープ方式）
        if len(self.samples) >= DISPLAY_SAMPLES:
            self.samples = []

    def update(self):
        """波形を再描画する"""
        self.line.set_data(range(len(self.samples)), self.samples)
        self.canvas.draw()
