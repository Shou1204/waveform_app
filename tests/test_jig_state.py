"""治具の状態（受信・同期・波形）を決める部分の試験"""

import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jig_state import DISPLAY_SAMPLES, GAP_SAMPLES, JigState, Recv, Sync  # noqa: E402
from packet import PktKey  # noqa: E402


def packet(values=None, ch=1001, sync=3):
    return {
        PktKey.ECG: values if values is not None else list(range(30)),
        PktKey.CHANNEL: ch,
        PktKey.SYNC_STS: sync,
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

    def test_no_data_clears_wave(self):
        """1 秒来なければ受信なしにして、波形を消す（前の波形が残って合格に見えないように）"""
        s = JigState()
        s.start(0.0)
        s.on_packet(packet(), 0.1)
        s.tick(0.5)
        self.assertFalse(np.isnan(s.wave[:30]).any())
        s.tick(1.1)
        self.assertEqual(s.recv(1.1), Recv.NO_DATA)
        self.assertTrue(np.isnan(s.wave).all())
        self.assertEqual(s.sync(1.1), Sync.UNKNOWN)

    def test_recovers_after_no_data(self):
        s = JigState()
        s.start(0.0)
        s.on_packet(packet(), 0.1)
        s.tick(2.0)
        s.on_packet(packet(), 2.1)
        self.assertEqual(s.recv(2.2), Recv.RECEIVING)
        self.assertFalse(np.isnan(s.wave[:30]).any())


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


if __name__ == "__main__":
    unittest.main()
