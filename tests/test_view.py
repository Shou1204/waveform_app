"""画面と受信をつないだ動きの試験（偽の基盤 FakeSerial を使う。窓は出さない）"""

import sys
import time
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import serial

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import fake_board  # noqa: E402
from fake_board import FakeSerial  # noqa: E402
from jig_state import Recv, Sync  # noqa: E402
from view import View  # noqa: E402


class Clock:
    """試験で進められる時計"""

    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


class ViewTestBase(unittest.TestCase):

    def setUp(self):
        self.boards = []
        self.clock = Clock()

        def factory(port, **kwargs):
            board = FakeSerial(port, **kwargs)
            self.boards.append(board)
            return board

        self.factory = factory
        self.app = View(serial_factory=factory, extra_ports=["FAKE"], clock=self.clock)
        self.app.withdraw()
        self.app.control_panel.port_var.set("FAKE")
        self.msg = mock.patch("view.messagebox").start()

    def tearDown(self):
        mock.patch.stopall()
        self.app._on_close()

    def pump(self, sec):
        """実時間で sec 秒、受信と画面更新を回す（時計も同じだけ進める）"""
        end = time.monotonic() + sec
        while time.monotonic() < end:
            time.sleep(0.05)
            self.clock.now += 0.05
            self.app.update()

    @property
    def board(self):
        return self.boards[-1]


class TestBeforeStart(ViewTestBase):

    def test_cannot_send_before_start(self):
        """開始する前は、波形と手打ちの送信ボタンが押せず、呼ばれても例外にならない"""
        panel = self.app.control_panel
        for btn in panel.wave_btns.values():
            self.assertEqual(str(btn["state"]), "disabled")
        self.assertEqual(str(panel.cmd_btn["state"]), "disabled")
        self.app._on_send_channel("1001")
        self.app._on_send_cmd("C1001")
        self.assertEqual(self.boards, [])


class TestOpenError(ViewTestBase):

    def test_open_error_is_shown(self):
        """ポートを開けなければ知らせて、停止のままにする"""
        def broken(port, **kwargs):
            raise serial.SerialException("could not open port 'COM7': PermissionError")

        self.app.serial_factory = broken
        self.app._on_toggle()
        self.msg.showerror.assert_called_once()
        self.assertIsNone(self.app.reader)
        self.assertEqual(self.app.jig.recv(self.clock()), Recv.STOPPED)
        self.assertEqual(self.app.control_panel.run_btn["text"], "▶ 開始")


class TestRunning(ViewTestBase):

    def setUp(self):
        super().setUp()
        self.app._on_toggle()  # 開始

    def test_receives_and_syncs_after_sending_channel(self):
        """電源を入れた直後は同期しない。チャンネルを送ると同期して波形が出る"""
        self.pump(0.5)
        self.assertEqual(self.app.jig.recv(self.clock()), Recv.RECEIVING)
        self.assertEqual(self.app.jig.sync(self.clock()), Sync.NOT_SYNCED)
        with mock.patch.object(fake_board, "FOLLOW_SEC", 0.3):
            self.app._on_send_channel("1001")
            self.pump(0.8)
        self.assertEqual(self.app.jig.sync(self.clock()), Sync.SYNCED)
        self.assertEqual(self.app.jig.board_ch, 1001)
        self.assertEqual(self.app.jig.sent_ch, "1001")
        self.assertGreater(np.nanmax(self.app.jig.wave), 900)

    def test_same_button_sends_again(self):
        """同じボタンをもう一度押しても送る（前の版はここで送られなかった）"""
        self.app._on_send_channel("1001")
        self.app._on_send_channel("1001")
        self.assertEqual(self.board.written, [b"\x02C1001\x03", b"\x02C1001\x03"])

    def test_manual_command_records_channel(self):
        self.app._on_send_cmd("C1002")
        self.assertEqual(self.board.written, [b"\x02C1002\x03"])
        self.assertEqual(self.app.jig.sent_ch, "1002")
        self.assertEqual(self.app.control_panel.selected_cmd, "1002")

    def test_no_data_when_board_stops(self):
        """基盤が出力をやめたら 1 秒で受信なしになり、波形が消える"""
        self.pump(0.5)
        self.assertGreater(self.app.jig.packet_count, 0)
        self.board.sending = False
        self.pump(1.6)
        self.assertEqual(self.app.jig.recv(self.clock()), Recv.NO_DATA)
        self.assertTrue(np.isnan(self.app.jig.wave).all())

    def test_not_synced_when_link_broken(self):
        """基盤 → ダミーの線が抜けていると、CH は変わるが未同期になる（2026-10-22 の場面）"""
        with mock.patch.object(fake_board, "FOLLOW_SEC", 0.2):
            self.app._on_send_channel("1001")
            self.pump(0.6)
            self.assertEqual(self.app.jig.sync(self.clock()), Sync.SYNCED)
            self.board.link_ok = False
            self.app._on_send_channel("1002")
            self.pump(0.6)
        self.assertEqual(self.app.jig.board_ch, 1002)
        self.assertEqual(self.app.jig.sync(self.clock()), Sync.NOT_SYNCED)

    def test_restart_clears_previous(self):
        """停止 → 開始で、前の波形と状態が残らない"""
        with mock.patch.object(fake_board, "FOLLOW_SEC", 0.2):
            self.app._on_send_channel("1001")
            self.pump(0.6)
        self.app._on_toggle()  # 停止
        self.app._on_toggle()  # 開始（新しい基盤）
        self.board.sending = False
        self.app.update()
        self.assertTrue(np.isnan(self.app.jig.wave).all())
        self.assertIsNone(self.app.jig.board_ch)
        self.assertEqual(self.app.jig.sync(self.clock()), Sync.UNKNOWN)
        self.assertIsNone(self.app.control_panel.selected_cmd)

    def test_read_error_is_shown(self):
        """受信中に変換器が抜けたら、止めて知らせる"""
        self.pump(0.3)

        def unplugged(size=1):
            raise serial.SerialException("ClearCommError failed")

        self.board.read = unplugged
        self.pump(0.4)
        self.msg.showerror.assert_called_once()
        self.assertIsNone(self.app.reader)
        self.assertEqual(self.app.control_panel.run_btn["text"], "▶ 開始")

    def test_stop_is_quick(self):
        """停止はすぐ終わり、受信のスレッドも止まる"""
        thread = self.app.thread
        t0 = time.monotonic()
        self.app._on_toggle()
        self.assertLess(time.monotonic() - t0, 0.5)
        self.assertFalse(thread.is_alive())


if __name__ == "__main__":
    unittest.main()
