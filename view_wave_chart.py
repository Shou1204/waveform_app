import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import customtkinter as ctk

# 画面に表示するサンプル数（サンプル数=秒数x300）
DISPLAY_SAMPLES = 1500


class WaveChart(ctk.CTkFrame):

    COLOR_FRAME = "#555C65"
    COLOR_LINE = "#57E908"

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
        self.ax.tick_params(
            colors=self.COLOR_FRAME,
            labelsize=8,
            labelfontfamily="BIZ UDGothic",
        )  # メモリ
        self.ax.spines[:].set_color(self.COLOR_FRAME)  # 枠線

        # 初期の空ラインを作成
        (self.line,) = self.ax.plot(
            [],
            [],
            color=self.COLOR_LINE,
            linewidth=1.2,
            solid_capstyle="round",
            solid_joinstyle="round",
        )

        # Y軸の範囲を固定（ECGデータのbit0〜bit10 = 0〜2047）
        self.ax.set_ylim(-2047, 2047)
        self.ax.set_xlim(0, DISPLAY_SAMPLES)
        # self.ax.set_yticklabels([])  # Y軸目盛の値を非表示
        self.ax.spines["top"].set_visible(False)
        self.ax.spines["right"].set_visible(False)
        self.ax.grid(
            axis="both", color=self.COLOR_FRAME, linewidth=0.4, linestyle="--"
        )  # Y軸の内部メモリ線

        self.ax.set_xticks([0, 300, 600, 900, 1200, 1500])
        self.ax.set_xticklabels(
            ["0sec", "1.0sec", "2.0sec", "3.0sec", "4.0sec", "5.0sec"]
        )

        # グラフをウィンドウに埋め込む
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def add_samples(self, new_samples):
        """ECGデータを追加する"""
        self.samples.extend(new_samples)

        # 表示サンプル数を超えたらリセット
        if len(self.samples) >= DISPLAY_SAMPLES:
            self.samples = []

    def update(self):
        """波形を再描画する"""
        self.line.set_data(range(len(self.samples)), self.samples)
        self.canvas.draw()
