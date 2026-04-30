import json
import os

SETTINGS_FILE = "settings.json"


class SaveSet:

    @staticmethod
    def save(port, cmd):
        """設定をJSONファイルに保存する"""
        try:
            data = {
                "port": port,
                "cmd": cmd,
            }
            with open(SETTINGS_FILE, "w") as f:
                json.dump(data, f)
        except Exception:
            print("設定の保存に失敗しました")
            return

    @staticmethod
    def load():
        """設定をJSONファイルから読み込む。ファイルがなければデフォルト値を返す"""
        try:
            if not os.path.exists(SETTINGS_FILE):
                return {"port": "", "cmd": ""}

            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {
                "port": "",
                "cmd": "",
            }
