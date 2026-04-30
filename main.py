from view import View
import os
import sys


def get_resource_path(relative_path):
    """PyInstallerで1つのファイルにまとめた際、解凍先の一時フォルダのパスを返す"""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


# もし画像やjsonを読み込んでいるなら、この関数を通すようにします
# 例: image_path = get_resource_path("assets/icon.png")

app = View()
app.mainloop()
