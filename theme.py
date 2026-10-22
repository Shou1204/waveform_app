"""画面の色と文字"""

FONT = "Meiryo UI"
PLOT_FONT = ["Meiryo", "Yu Gothic", "sans-serif"]

BG = "#f4f6f8"  # 窓の背景
PANEL = "#ffffff"  # 枠の中
TEXT = "#202124"
SUB = "#5f6368"  # 説明の文字
LINE = "#dadce0"  # 枠線
BTN = "#e8eaed"  # 選ばれていないボタン
BTN_DISABLED_TEXT = "#9aa0a6"

GREEN = "#188038"
RED = "#c5221f"
BLUE = "#1a73e8"
AMBER = "#b06000"
GRAY = "#80868b"

WAVE_NEW = "#174ea6"  # 今描いている波形
WAVE_OLD = "#a8c1ef"  # 前の周の波形
GRID = "#e3e6ea"
NO_DATA_BG = "#fdecea"


def font(size, bold=False):
    return (FONT, size, "bold" if bold else "normal")
