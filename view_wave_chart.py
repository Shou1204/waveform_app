import tkinter as tk

import matplotlib
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

import theme as T
from jig_state import DISPLAY_SAMPLES, NO_DATA_SEC

matplotlib.rcParams["font.family"] = T.PLOT_FONT

# Y軸の範囲（ECGデータは中心0で±1024）
Y_LIMIT = 1150


class WaveChart(tk.Frame):
    """波形表示（左から右へ上書きしていく）"""

    def __init__(self, master):
        super().__init__(master, bg=T.PANEL, highlightbackground=T.LINE, highlightthickness=1)
        self.x = np.arange(DISPLAY_SAMPLES)
        self._setup_plot()

    def _setup_plot(self):
        """matplotlibのグラフを作成してウィンドウに埋め込む"""
        self.fig = Figure(dpi=self.winfo_fpixels("1i"), facecolor=T.PANEL)
        self.ax = self.fig.add_axes([0.07, 0.08, 0.91, 0.9])
        ax = self.ax
        ax.set_xlim(0, DISPLAY_SAMPLES)
        ax.set_ylim(-Y_LIMIT, Y_LIMIT)
        ax.set_xticks([0, 300, 600, 900, 1200, 1500], ["0", "1秒", "2秒", "3秒", "4秒", "5秒"])
        ax.set_yticks([-1000, -500, 0, 500, 1000])
        ax.tick_params(colors=T.SUB, labelsize=8, length=0)
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.grid(color=T.GRID, linewidth=0.8)

        empty = np.full(DISPLAY_SAMPLES, np.nan)
        (self.line_old,) = ax.plot(self.x, empty, color=T.WAVE_OLD, linewidth=1.6)
        (self.line_new,) = ax.plot(self.x, empty, color=T.WAVE_NEW, linewidth=1.6)

        # 受信なしのときの文字
        self.no_data_title = ax.text(
            DISPLAY_SAMPLES / 2, 120, "受信なし", ha="center", va="center",
            color=T.RED, fontsize=30, fontweight="bold", visible=False,
        )
        self.no_data_note = ax.text(
            DISPLAY_SAMPLES / 2, -180,
            f"{NO_DATA_SEC:.1f} 秒以上データが来ていません　波形は消しました",
            ha="center", color=T.RED, fontsize=11, visible=False,
        )

        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def show(self, wave, cursor, no_data):
        """波形を描き直す。cursor より左が今の周、右が前の周"""
        is_new = self.x < cursor
        self.line_new.set_ydata(np.where(is_new, wave, np.nan))
        self.line_old.set_ydata(np.where(is_new, np.nan, wave))

        self.ax.set_facecolor(T.NO_DATA_BG if no_data else T.PANEL)
        self.no_data_title.set_visible(no_data)
        self.no_data_note.set_visible(no_data)
        # draw_idle() だと閉じた後に描画の予約が残るので、その場で描く
        self.canvas.draw()
