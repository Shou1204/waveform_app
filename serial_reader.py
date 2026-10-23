import serial
from packet import PktKey, PACKET_FIELDS

PACKET_SIZE = 100  # 1パケットのバイト数
START_CODE = 0xF0  # 開始コード
END_CODE = 0xFF  # 終了コード
ECG_OFFSET = 38  # ECGデータの開始位置
ECG_COUNT = 30  # 1パケットのECGデータ数
CHECKSUM_POS = 98  # チェックサムの位置

STX = b"\x02"
ETX = b"\x03"


def parse_packet(raw):
    """100バイトのパケットを辞書にする（下位7ビットのみ有効）"""
    packet = {}
    for key, offset, size in PACKET_FIELDS:
        packet[key] = _parse_int(raw, offset, size)

    # ECGとチェックサムは別処理
    packet[PktKey.ECG] = _parse_ecg(raw, ECG_OFFSET)
    packet[PktKey.CHECKSUM] = raw[CHECKSUM_POS] & 0x7F
    return packet


def is_valid_packet(raw):
    """終了コードとチェックサムが合っているか（捨てるのはこの 2 つだけ。中身の値は見ない）

    チェックサムは検査基盤（to_host.c の get_check_sum）と同じく、開始コードから
    チェックサムの手前までの合計の下位7ビット（仕様書は開始コードを除くと書いているが、実機はこちら）
    """
    if raw[-1] != END_CODE:
        return False
    return (sum(raw[:CHECKSUM_POS]) & 0x7F) == (raw[CHECKSUM_POS] & 0x7F)


def _parse_int(raw, offset, size):
    """指定範囲のバイト列を整数に変換する（下位7ビットのみ有効）"""
    value = 0
    for i in range(size):
        value = (value << 7) | (raw[offset + i] & 0x7F)
    return value


def _parse_ecg(raw, offset):
    """ECGデータ30個を取り出す（仕様書どおり bit0〜bit10 を値とし、中心を0にする）

    フラグ（bit12 エラー・bit13 QRS）は値に入れない。エラーフラグが立っていても、
    検査基盤が送ってきた bit0〜bit10 をそのまま描く（ECG が無いとき基盤は 0 を入れるので −1024 の線になる）
    """
    ecg_list = []
    for i in range(ECG_COUNT):
        high = raw[offset + i * 2] & 0x7F
        low = raw[offset + i * 2 + 1] & 0x7F
        ecg_list.append((((high << 7) | low) & 0x7FF) - 1024)
    return ecg_list


class PacketParser:
    """受信したバイト列から100バイトのパケットを切り出す"""

    def __init__(self):
        self.buf = bytearray()
        self.bad_count = 0  # 開始コードはあったが、形の崩れていたパケットの数

    def feed(self, data):
        """バイト列を足し、そろったパケット（辞書）のリストを返す"""
        self.buf += data
        packets = []
        while True:
            start = self.buf.find(START_CODE)
            if start < 0:
                # 開始コードが無ければ全部捨てる
                self.buf.clear()
                break
            del self.buf[:start]

            if len(self.buf) < PACKET_SIZE:
                break

            raw = bytes(self.buf[:PACKET_SIZE])
            if not is_valid_packet(raw):
                # 欠けている・化けている → 数えて、この開始コードだけ捨てて次を探す
                self.bad_count += 1
                del self.buf[:1]
                continue

            del self.buf[:PACKET_SIZE]
            packets.append(parse_packet(raw))
        return packets


class SerialReader:

    def __init__(self, port, baudrate=115200, serial_factory=None):
        self.port = port
        self.baudrate = baudrate
        self.serial_factory = serial_factory or serial.Serial
        self.parser = PacketParser()
        self.ser = None

    def open(self):
        """COMポートを開く。開けなければ例外を出す"""
        self.ser = self.serial_factory(
            port=self.port,
            baudrate=self.baudrate,
            timeout=0.1,
        )

    def close(self):
        """COMポートを閉じる"""
        if self.ser and self.ser.is_open:
            self.ser.close()

    def read_packets(self):
        """届いている分を読み、そろったパケットのリストを返す（最大0.1秒待つ）"""
        data = self.ser.read(self.ser.in_waiting or 1)
        return self.parser.feed(data)

    def send_ch(self, ch):
        """チャンネル変更命令を送信する（例: 1001 → STX 'C1001' ETX）"""
        self.send_cmd("C" + ch)

    def send_cmd(self, cmd):
        """コマンドをSTXとETXで挟んで送信する"""
        self.ser.write(STX + cmd.encode("ascii") + ETX)
