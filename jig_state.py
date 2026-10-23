"""治具の状態（受信・同期・波形）を決める。画面には触らない"""

from enum import Enum

import numpy as np

from packet import PktKey

# 画面に表示するサンプル数（サンプル数=秒数x300）
DISPLAY_SAMPLES = 1500
# 上書き位置の先を空ける幅（サンプル数）
GAP_SAMPLES = 25
# この秒数データが来なければ「受信なし」にする
NO_DATA_SEC = 1.0
# 同期状態の「同期済み」（検査基盤の SyncSts_e の SYNC_READY）
SYNC_READY = 3
# 通し番号が 0 に戻る値（検査基盤の to_host.c の MAX_TX_FORM_IDX。48時間）
SEQ_WRAP = 1728000


class Recv(Enum):
    STOPPED = "stopped"  # 停止中
    WAITING = "waiting"  # 開始した直後で、まだ1つも来ていない
    RECEIVING = "receiving"  # 受信中
    NO_DATA = "no_data"  # 受信なし（NO_DATA_SEC 以上来ていない）


class Sync(Enum):
    UNKNOWN = "unknown"  # 分からない（停止中・受信なし・まだ来ていない）
    SYNCED = "synced"  # 同期済み
    NOT_SYNCED = "not_synced"  # 未同期


class JigState:

    def __init__(self):
        self.running = False
        self._reset()

    def _reset(self):
        """表示する中身をすべて消す"""
        self.wave = np.full(DISPLAY_SAMPLES, np.nan)
        self.cursor = 0
        self.packet_count = 0
        self.lost_count = 0  # 抜け（通し番号が飛んだ回数）
        self.bad_count = 0  # 化け（形の崩れたパケットの数）
        self.board_err_count = 0  # 基盤エラー（基盤がダミーから受けたフレームのエラーの合計）
        self.no_data_count = 0  # 受信なし（受信なしになった回数）
        self.last_seq = None
        self.board_ch = None
        self.sent_ch = None
        self.sync_sts = None
        self.started_at = None
        self.last_rx_at = None
        self.no_data_counted = False

    def start(self, now):
        """受信を開始する。前の波形と状態は消す"""
        self._reset()
        self.running = True
        self.started_at = now

    def stop(self):
        """受信を停止する。波形はそのまま残す"""
        self.running = False

    def sent(self, ch):
        """チャンネルを送ったことを覚える"""
        self.sent_ch = ch

    def on_packet(self, packet, now):
        """パケットを1つ受け取る"""
        if not self.running:
            return

        for value in packet[PktKey.ECG]:
            self.wave[self.cursor] = value
            self.cursor = (self.cursor + 1) % DISPLAY_SAMPLES

        # 上書き位置の先を空ける
        for i in range(GAP_SAMPLES):
            self.wave[(self.cursor + i) % DISPLAY_SAMPLES] = np.nan

        # 通し番号が前の +1 でなければ抜け（基盤の電源の入れ直しも 1 回と数える）
        seq = packet[PktKey.SEQ_NO]
        if self.last_seq is not None and seq != (self.last_seq + 1) % SEQ_WRAP:
            self.lost_count += 1
        self.last_seq = seq

        self.packet_count += 1
        self.board_err_count += packet[PktKey.ERR_CNT]
        self.board_ch = packet[PktKey.CHANNEL]
        self.sync_sts = packet[PktKey.SYNC_STS]
        self.last_rx_at = now
        self.no_data_counted = False

    def on_bad(self, count):
        """形の崩れたパケット（チェックサム・終了コードの誤り）を数える"""
        if self.running:
            self.bad_count += count

    def tick(self, now):
        """定期処理。受信なしになった回数を数える（波形は消さずに残す）"""
        if self.recv(now) == Recv.NO_DATA and not self.no_data_counted:
            self.no_data_counted = True
            self.no_data_count += 1

    def recv(self, now):
        """受信の状態"""
        if not self.running:
            return Recv.STOPPED
        last = self.last_rx_at if self.last_rx_at is not None else self.started_at
        if now - last >= NO_DATA_SEC:
            return Recv.NO_DATA
        if self.last_rx_at is None:
            return Recv.WAITING
        return Recv.RECEIVING

    def sync(self, now):
        """同期の状態。受信中のときだけ分かる"""
        if self.recv(now) != Recv.RECEIVING:
            return Sync.UNKNOWN
        if self.sync_sts == SYNC_READY:
            return Sync.SYNCED
        return Sync.NOT_SYNCED
