"""治具の状態（受信・同期・波形）を決める部分の試験"""

import itertools
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jig_state import DISPLAY_SAMPLES, GAP_SAMPLES, SEQ_WRAP, JigState, Recv, Sync  # noqa: E402
from packet import PktKey  # noqa: E402


_seq = itertools.count()


def packet(values=None, ch=1001, sync=3, seq=None, err=0):
    """seq を省くと、呼ぶたびに 1 ずつ増える（抜けなし）"""
    return {
        PktKey.ECG: values if values is not None else list(range(30)),
        PktKey.CHANNEL: ch,
        PktKey.SYNC_STS: sync,
        PktKey.SEQ_NO: next(_seq) if seq is None else seq,
        PktKey.ERR_CNT: err,
    }


class TestRecv(unittest.TestCase):

    def test_stopped(self):
        s = JigState()
        self.assertEqual(s.recv(0), Recv.STOPPED)
        self.assertEqual(s.sync(0), Sync.UNKNOWN)

    def test_waiting_then_receiving(self):
        s = JigState()
        s.start(10.0)
        self.assertEqual(s.recv(10.5), Recv.WAITING)
        s.on_packet(packet(), 10.5)
        self.assertEqual(s.recv(10.6), Recv.RECEIVING)

    def test_no_data_when_nothing_comes_after_start(self):
        """開始してから 1 秒何も来なければ受信なし"""
        s = JigState()
        s.start(10.0)
        self.assertEqual(s.recv(11.0), Recv.NO_DATA)

    def test_no_data_keeps_wave(self):
        """1 秒来なければ受信なし・同期不明にする。波形は消さずに残す（止まる前に何が来ていたかを見られるように）"""
        s = JigState()
        s.start(0.0)
        s.on_packet(packet(), 0.1)
        s.tick(1.1)
        self.assertEqual(s.recv(1.1), Recv.NO_DATA)
        self.assertEqual(s.sync(1.1), Sync.UNKNOWN)
        self.assertFalse(np.isnan(s.wave[:30]).any())
        self.assertEqual(s.cursor, 30)

    def test_recovers_after_no_data(self):
        """受信なしから戻ったら、残した波形の続きに描く"""
        s = JigState()
        s.start(0.0)
        s.on_packet(packet(), 0.1)
        s.tick(2.0)
        s.on_packet(packet(), 2.1)
        self.assertEqual(s.recv(2.2), Recv.RECEIVING)
        self.assertEqual(s.cursor, 60)
        self.assertFalse(np.isnan(s.wave[:60]).any())


class TestSync(unittest.TestCase):

    def test_synced_only_when_ready(self):
        s = JigState()
        s.start(0.0)
        for sts, want in ((3, Sync.SYNCED), (0, Sync.NOT_SYNCED), (1, Sync.NOT_SYNCED), (2, Sync.NOT_SYNCED)):
            s.on_packet(packet(sync=sts), 0.1)
            self.assertEqual(s.sync(0.2), want, sts)


class TestRestart(unittest.TestCase):

    def test_start_clears_previous(self):
        """停止 → 開始で、前の波形・同期・CH・数を消す（前の基盤の結果が残らないように）"""
        s = JigState()
        s.start(0.0)
        s.sent("1001")
        s.on_packet(packet(ch=1001, sync=3), 0.1)
        s.stop()
        self.assertEqual(s.recv(0.2), Recv.STOPPED)

        s.start(5.0)
        self.assertTrue(np.isnan(s.wave).all())
        self.assertEqual(s.cursor, 0)
        self.assertIsNone(s.board_ch)
        self.assertIsNone(s.sent_ch)
        self.assertEqual(s.packet_count, 0)
        self.assertEqual(s.sync(5.1), Sync.UNKNOWN)

    def test_stop_keeps_wave(self):
        """停止しただけなら波形は残す（見返せるように）"""
        s = JigState()
        s.start(0.0)
        s.on_packet(packet(), 0.1)
        s.stop()
        s.tick(10.0)
        self.assertFalse(np.isnan(s.wave[:30]).any())

    def test_packets_ignored_when_stopped(self):
        s = JigState()
        s.on_packet(packet(), 0.1)
        self.assertEqual(s.packet_count, 0)


class TestSweep(unittest.TestCase):

    def test_writes_at_cursor_and_leaves_gap(self):
        s = JigState()
        s.start(0.0)
        s.on_packet(packet(list(range(30))), 0.1)
        self.assertEqual(s.cursor, 30)
        self.assertEqual(list(s.wave[:30]), list(range(30)))
        self.assertTrue(np.isnan(s.wave[30:30 + GAP_SAMPLES]).all())

    def test_wraps_and_overwrites_old(self):
        """右端まで来たら左に戻って上書きする。すき間の先には前の周が残る"""
        s = JigState()
        s.start(0.0)
        n = DISPLAY_SAMPLES // 30
        for _ in range(n):
            s.on_packet(packet([100] * 30), 0.1)
        self.assertEqual(s.cursor, 0)
        s.on_packet(packet([200] * 30), 0.2)
        self.assertEqual(s.cursor, 30)
        self.assertTrue((s.wave[:30] == 200).all())
        self.assertTrue(np.isnan(s.wave[30:30 + GAP_SAMPLES]).all())
        self.assertTrue((s.wave[30 + GAP_SAMPLES:] == 100).all())

    def test_gap_wraps_around(self):
        s = JigState()
        s.start(0.0)
        for _ in range(DISPLAY_SAMPLES // 30 - 1):
            s.on_packet(packet([100] * 30), 0.1)
        # cursor は 1470。すき間は 1470〜1494
        self.assertEqual(s.cursor, DISPLAY_SAMPLES - 30)
        self.assertTrue(np.isnan(s.wave[DISPLAY_SAMPLES - 30:DISPLAY_SAMPLES - 5]).all())


class TestCounts(unittest.TestCase):
    """抜け・化け・基盤エラーを数える"""

    def test_no_count_when_seq_continues(self):
        s = JigState()
        s.start(0.0)
        for seq in range(506, 520):
            s.on_packet(packet(seq=seq), 0.1)
        self.assertEqual(s.lost_count, 0)

    def test_lost_counts_each_jump(self):
        """通し番号が飛ぶたびに 1 回と数える（飛んだ数ではない）"""
        s = JigState()
        s.start(0.0)
        for seq in [10, 11, 13, 14, 20, 21]:
            s.on_packet(packet(seq=seq), 0.1)
        self.assertEqual(s.lost_count, 2)

    def test_seq_wrap_is_not_lost(self):
        """通し番号が 0 に戻るのは抜けではない（48時間で一周）"""
        s = JigState()
        s.start(0.0)
        for seq in [SEQ_WRAP - 2, SEQ_WRAP - 1, 0, 1]:
            s.on_packet(packet(seq=seq), 0.1)
        self.assertEqual(s.lost_count, 0)

    def test_board_restart_is_lost(self):
        """基盤の電源を入れ直して番号が 0 から始まったら、抜けとして数える"""
        s = JigState()
        s.start(0.0)
        for seq in [500, 501, 0, 1]:
            s.on_packet(packet(seq=seq), 0.1)
        self.assertEqual(s.lost_count, 1)

    def test_first_packet_is_not_lost(self):
        """開始して最初のパケットは、番号がいくつでも抜けにしない"""
        s = JigState()
        s.start(0.0)
        s.on_packet(packet(seq=12345), 0.1)
        self.assertEqual(s.lost_count, 0)

    def test_board_err_is_summed(self):
        """基盤エラーはパケットごとの値を足していく"""
        s = JigState()
        s.start(0.0)
        for err in [0, 2, 0, 1]:
            s.on_packet(packet(err=err), 0.1)
        self.assertEqual(s.board_err_count, 3)

    def test_no_data_counts_each_time(self):
        """受信なしになるたびに 1 回。続いているあいだは増えない。戻っても残る"""
        s = JigState()
        s.start(0.0)
        s.on_packet(packet(), 0.1)
        s.tick(1.2)
        s.tick(1.5)
        self.assertEqual(s.no_data_count, 1)
        s.on_packet(packet(), 2.0)
        s.tick(2.1)
        self.assertEqual(s.no_data_count, 1)
        s.tick(3.1)
        self.assertEqual(s.no_data_count, 2)

    def test_no_data_from_start(self):
        """開始してから何も来ないのも 1 回"""
        s = JigState()
        s.start(0.0)
        s.tick(1.1)
        self.assertEqual(s.no_data_count, 1)

    def test_no_data_not_counted_when_stopped(self):
        s = JigState()
        s.tick(5.0)
        s.start(10.0)
        s.on_packet(packet(), 10.1)
        s.stop()
        s.tick(20.0)
        self.assertEqual(s.no_data_count, 0)

    def test_bad(self):
        s = JigState()
        s.start(0.0)
        s.on_bad(2)
        s.on_bad(1)
        self.assertEqual(s.bad_count, 3)

    def test_not_counted_when_stopped(self):
        s = JigState()
        s.on_bad(1)
        s.on_packet(packet(seq=5, err=1), 0.1)
        self.assertEqual((s.lost_count, s.bad_count, s.board_err_count), (0, 0, 0))

    def test_start_resets_counts(self):
        """開始で 0 に戻す。前の番号からの続きも見ない"""
        s = JigState()
        s.start(0.0)
        s.on_packet(packet(seq=1, err=1), 0.1)
        s.on_packet(packet(seq=5), 0.2)
        s.on_bad(1)
        s.tick(0.5 + 1.0)
        s.stop()
        s.start(2.0)
        self.assertEqual((s.lost_count, s.bad_count, s.board_err_count, s.no_data_count), (0, 0, 0, 0))
        s.on_packet(packet(seq=100), 2.1)
        self.assertEqual(s.lost_count, 0)


if __name__ == "__main__":
    unittest.main()
