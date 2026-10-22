"""受信したバイト列からパケットを切り出す部分の試験"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fake_board import build_packet, wave_value  # noqa: E402
from packet import PktKey  # noqa: E402
from serial_reader import PacketParser, SerialReader  # noqa: E402


def triangle_packet(start=0, ch=1001, sync=3, seq=0):
    ecg = [1024 + wave_value(1001, start + i) for i in range(30)]
    return build_packet(ecg, ch, sync, seq)


class TestPacketParser(unittest.TestCase):

    def test_reads_fields(self):
        """CH・同期状態・連番・ECG を読める"""
        pkt = PacketParser().feed(triangle_packet(ch=1002, sync=3, seq=12345))[0]
        self.assertEqual(pkt[PktKey.CHANNEL], 1002)
        self.assertEqual(pkt[PktKey.SYNC_STS], 3)
        self.assertEqual(pkt[PktKey.SEQ_NO], 12345)
        self.assertEqual(pkt[PktKey.ECG], [wave_value(1001, i) for i in range(30)])

    def test_ecg_flags_are_ignored(self):
        """ECG のフラグ（bit12 など）は値に入れない"""
        pkt = PacketParser().feed(build_packet([0x1000 | 1024] * 30))[0]
        self.assertEqual(pkt[PktKey.ECG], [0] * 30)

    def test_split_chunks(self):
        """細切れに届いても 1 つにまとまる"""
        data = triangle_packet() + triangle_packet(30, seq=1)
        parser = PacketParser()
        got = []
        for i in range(0, len(data), 7):
            got += parser.feed(data[i:i + 7])
        self.assertEqual([p[PktKey.SEQ_NO] for p in got], [0, 1])

    def test_skips_garbage_before_start(self):
        """開始コードの前のごみは捨てる"""
        got = PacketParser().feed(b"\x01\x02\x7f" + triangle_packet())
        self.assertEqual(len(got), 1)

    def test_recovers_after_lost_bytes(self):
        """途中のバイトが抜けたパケットは捨て、次のパケットから戻る"""
        broken = triangle_packet(seq=0)[:60]  # 後ろが抜けた
        data = broken + triangle_packet(seq=1) + triangle_packet(seq=2)
        got = PacketParser().feed(data)
        self.assertEqual([p[PktKey.SEQ_NO] for p in got], [1, 2])

    def test_waits_for_rest(self):
        """足りない分は次に届くまで待つ"""
        parser = PacketParser()
        data = triangle_packet()
        self.assertEqual(parser.feed(data[:50]), [])
        self.assertEqual(len(parser.feed(data[50:])), 1)


class FakeWriteSerial:
    def __init__(self):
        self.written = []

    def write(self, data):
        self.written.append(data)


class TestSend(unittest.TestCase):

    def test_send_ch_format(self):
        """チャンネル変更命令は STX 'C' 4桁 ETX（SerialViewer の C1002 と同じバイト列）"""
        reader = SerialReader("X")
        reader.ser = FakeWriteSerial()
        reader.send_ch("1002")
        self.assertEqual(reader.ser.written, [b"\x02C1002\x03"])


if __name__ == "__main__":
    unittest.main()
