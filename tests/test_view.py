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
import theme as T  # noqa: E402
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

    def test_manual_command_with_other_properties(self):
        """ほかの項目と一緒の C＋4桁はチャンネルとして覚える"""
        self.app._on_send_cmd("F1H1A2C1002K1")
        self.assertEqual(self.app.jig.sent_ch, "1002")

    def test_manual_command_not_channel(self):
        """C＋5桁や、項目の途中の C はチャンネルとして覚えない"""
        self.app._on_send_cmd("C10010")
        self.app._on_send_cmd("XC1234")
        self.assertIsNone(self.app.jig.sent_ch)
        self.assertIsNone(self.app.control_panel.selected_cmd)

    def test_manual_command_non_ascii(self):
        """全角などは送らずに知らせ、受信は止めない"""
        self.app._on_send_cmd("Ｃ１００１")
        self.msg.showwarning.assert_called_once()
        self.msg.showerror.assert_not_called()
        self.assertEqual(self.board.written, [])
        self.assertIsNotNone(self.app.reader)

    def test_error_shown_once(self):
        """受信のエラーと送信のエラーが重なっても、知らせるのは 1 回"""
        self.app.rx_queue.put(("error", serial.SerialException("ClearCommError failed")))

        def unplugged(data):
            raise serial.SerialException("WriteFile failed")

        self.board.write = unplugged
        self.app._on_send_channel("1001")
        self.pump(0.4)
        self.msg.showerror.assert_called_once()

    def test_update_survives_exception(self):
        """画面の更新で例外が出ても、定期更新は続く"""
        calls = []
        original = self.app.wave_chart.show

        def flaky(*args):
            calls.append(1)
            if len(calls) == 1:
                raise RuntimeError("描画のエラー")
            original(*args)

        self.app.wave_chart.show = flaky
        self.app.report_callback_exception = lambda *a: None
        self.pump(0.5)
        self.assertGreater(len(calls), 2)

    def test_no_data_when_board_stops(self):
        """基盤が出力をやめたら 1 秒で受信なしになり、波形が消える"""
        self.pump(0.5)
        self.assertGreater(self.app.jig.packet_count, 0)
        self.board.sending = False
        self.pump(1.6)
        self.assertEqual(self.app.jig.recv(self.clock()), Recv.NO_DATA)
        self.assertTrue(np.isnan(self.app.jig.wave).all())
        # 基盤が戻っても、受信なしになったことは下の数字に赤で残る
        self.board.sending = True
        self.pump(0.5)
        self.assertEqual(self.app.jig.recv(self.clock()), Recv.RECEIVING)
        self.assertEqual(self.app.info_bar.no_data_box.value.cget("text"), "1")
        self.assertEqual(self.app.info_bar.no_data_box.value.cget("fg"), T.RED)

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

    def test_counts_shown_and_red(self):
        """抜け・化け・基盤エラーを数えて出し、1 つでもあれば赤くする。ふだんは 0"""
        self.pump(0.5)
        info = self.app.info_bar
        for box in (info.lost_box, info.bad_box, info.err_box, info.no_data_box):
            self.assertEqual(box.value.cget("text"), "0")
        self.board.drop = self.board.garble = self.board.board_err = True
        # 偽の基盤は乱数で不良を入れるので、3 つとも出るまで回す（上限 8 秒）
        jig = self.app.jig
        end = time.monotonic() + 8
        while time.monotonic() < end and not (jig.lost_count and jig.bad_count and jig.board_err_count):
            self.pump(0.5)
        self.assertGreater(self.app.jig.lost_count, 0)
        self.assertGreater(self.app.jig.bad_count, 0)
        self.assertGreater(self.app.jig.board_err_count, 0)
        for box in (info.lost_box, info.bad_box, info.err_box):
            self.assertEqual(box.value.cget("fg"), T.RED)

    def test_restart_clears_previous(self):
        """停止 → 開始で、前の波形と状態が残らない"""
        with mock.patch.object(fake_board, "FOLLOW_SEC", 0.2):
            self.app._on_send_channel("1001")
            self.pump(0.6)
            self.board.drop = self.board.garble = self.board.board_err = True
            self.pump(1.0)
        self.app._on_toggle()  # 停止
        self.app._on_toggle()  # 開始（新しい基盤）
        self.board.sending = False
        self.app.update()
        self.assertTrue(np.isnan(self.app.jig.wave).all())
        self.assertIsNone(self.app.jig.board_ch)
        self.assertEqual(self.app.jig.lost_count, 0)
        self.assertEqual(self.app.jig.bad_count, 0)
        self.assertEqual(self.app.jig.board_err_count, 0)
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
