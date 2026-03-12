import json
import os

SETTINGS_FILE = "settings.json"


class SaveSet:

    @staticmethod
    def save(port, channel):
        """設定をJSONファイルに保存する"""
        data = {
            "port": port,
            "channel": channel,
        }
        with open(SETTINGS_FILE, "w") as f:
            json.dump(data, f)

    @staticmethod
    def load():
        """設定をJSONファイルから読み込む。ファイルがなければデフォルト値を返す"""
        if not os.path.exists(SETTINGS_FILE):
            return {"port": "", "channel": ""}

        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
