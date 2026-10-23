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

    def test_error_flag_drawn_as_is(self):
        """エラーフラグ（bit12）が立っていても、bit0〜bit10 をそのまま値にする（基盤が ECG 無しで送る 0x1000 は −1024）"""
        pkt = PacketParser().feed(build_packet([0x1000] * 30, sync=0))[0]
        self.assertEqual(pkt[PktKey.ECG], [-1024] * 30)
        pkt = PacketParser().feed(build_packet([0x1000 | 1524] * 30))[0]
        self.assertEqual(pkt[PktKey.ECG], [500] * 30)

    def test_qrs_flag_is_ignored(self):
        """QRS フラグ（bit13）は値に入れない"""
        pkt = PacketParser().feed(build_packet([0x2000 | 1124] * 30))[0]
        self.assertEqual(pkt[PktKey.ECG], [100] * 30)

    def test_drops_bad_checksum(self):
        """チェックサムが合わないパケットは捨てる"""
        bad = bytearray(triangle_packet(seq=0))
        bad[50] ^= 0x01
        got = PacketParser().feed(bytes(bad) + triangle_packet(seq=1))
        self.assertEqual([p[PktKey.SEQ_NO] for p in got], [1])

    def test_keeps_bit7_set(self):
        """データのバイトに bit7 が立っていても捨てない（下位 7 ビットは正しいので、そのまま描く）"""
        bad = bytearray(triangle_packet(seq=0))
        bad[50] |= 0x80
        bad[98] |= 0x80
        parser = PacketParser()
        got = parser.feed(bytes(bad) + triangle_packet(seq=1))
        self.assertEqual([p[PktKey.SEQ_NO] for p in got], [0, 1])
        self.assertEqual(got[0][PktKey.ECG], [wave_value(1001, i) for i in range(30)])
        self.assertEqual(parser.bad_count, 0)

    def test_keeps_bit7_set_in_header(self):
        """見出しの項目（通し番号・基盤エラー）のバイトに bit7 が立っていても、下位 7 ビットで読む"""
        bad = bytearray(build_packet([1024] * 30, seq=300, err=2))
        bad[24] |= 0x80
        bad[31] |= 0x80
        pkt = PacketParser().feed(bytes(bad))[0]
        self.assertEqual(pkt[PktKey.SEQ_NO], 300)
        self.assertEqual(pkt[PktKey.ERR_CNT], 2)

    def test_both_flags_are_not_value(self):
        """エラー（bit12）と QRS（bit13）の両方が立っていても、値は bit0〜bit10"""
        pkt = PacketParser().feed(build_packet([0x3000 | 1124] * 30))[0]
        self.assertEqual(pkt[PktKey.ECG], [100] * 30)

    def test_counts_bad(self):
        """形の崩れたパケット（チェックサム・後ろの抜け）を 1 つずつ数える"""
        sum_ng = bytearray(triangle_packet(seq=0))
        sum_ng[50] ^= 0x01
        short = triangle_packet(seq=1)[:60]
        parser = PacketParser()
        got = parser.feed(bytes(sum_ng) + short + triangle_packet(seq=2))
        self.assertEqual([p[PktKey.SEQ_NO] for p in got], [2])
        self.assertEqual(parser.bad_count, 2)

    def test_counts_bad_end_code(self):
        """終了コードが違うパケットも化けと数える"""
        bad = bytearray(triangle_packet(seq=0))
        bad[99] = 0x7F
        parser = PacketParser()
        got = parser.feed(bytes(bad) + triangle_packet(seq=1))
        self.assertEqual([p[PktKey.SEQ_NO] for p in got], [1])
        self.assertEqual(parser.bad_count, 1)

    def test_start_code_garbled_is_lost_not_bad(self):
        """開始コードが化けたパケットは見つけられないので、化けではなく抜け（番号の飛び）で出る"""
        bad = bytearray(triangle_packet(seq=1))
        bad[0] = 0x70
        parser = PacketParser()
        got = parser.feed(triangle_packet(seq=0) + bytes(bad) + triangle_packet(seq=2))
        self.assertEqual([p[PktKey.SEQ_NO] for p in got], [0, 2])
        self.assertEqual(parser.bad_count, 0)

    def test_no_bad_for_good_or_garbage(self):
        """正しいパケットと、開始コードの前のごみ（途中から読み始めたとき）は数えない"""
        parser = PacketParser()
        parser.feed(triangle_packet(seq=0)[40:] + triangle_packet(seq=1) + triangle_packet(seq=2))
        self.assertEqual(parser.bad_count, 0)

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
