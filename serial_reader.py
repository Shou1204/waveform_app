import serial
from packet import PktKey, PACKET_FIELDS


class SerialReader:

    def __init__(self, port, baudrate=115200):
        self.port = port
        self.baudrate = baudrate
        self.ser = None

    def open(self):
        """COMポートを開く"""
        self.ser = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            timeout=1,
        )
        print(f"ポートを開きました: {self.port}")

    def close(self):
        """COMポートを閉じる"""
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("ポートを閉じました")

    def sync(self):
        """パケットの先頭（0xF0）を見つけるまで読み捨てる"""
        print("同期中...")
        while True:
            byte = self.ser.read(1)
            if byte == b"\xf0":
                print("同期完了")
                return

    def read(self):
        """パケットを1つ受信して辞書で返す"""

        # sync()で読んだ0xF0を先頭に戻して100バイトのパケットとして扱う
        raw = b"\xf0" + self.ser.read(99)

        if len(raw) != 100:
            print("受信データが不足しています")
            return None

        # 末尾が0xFFか確認
        if raw[99] != 0xFF:
            print("終了コードが不正です")
            return None

        # PACKET_FIELDSのテーブルを使って全項目をパース
        packet = {}
        for key, offset, size in PACKET_FIELDS:
            packet[key] = self._parse_int(raw, offset, size)

        # ECGとチェックサムは別処理
        packet[PktKey.ECG] = self._parse_ecg(raw, 38)
        packet[PktKey.CHECKSUM] = raw[98] & 0x7F

        return packet

    def _parse_int(self, raw, offset, size):
        """指定範囲のバイト列を整数に変換する（下位7ビットのみ有効）"""
        value = 0
        for i in range(size):
            byte = raw[offset + i] & 0x7F
            value = (value << 7) | byte
        return value

    def _parse_ecg(self, raw, offset):
        """ECGデータ30個を取り出す"""
        ecg_list = []
        for i in range(30):
            high = raw[offset + i * 2] & 0x7F
            low = raw[offset + i * 2 + 1] & 0x7F
            value = ((high << 7) | low) & 0x7FF  # bit0〜bit10のみ
            ecg_list.append(value)
        return ecg_list
