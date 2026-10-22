"""検査基盤のふりをする（ハードなしで表示アプリを動かすため）

シリアルポート（pyserial の Serial）と同じ形で使える。`python main.py --fake` で
ポートの一覧に「FAKE」が出て、これにつながる。

まねしていること
- 100ms ごとに100バイトのパケットを出す（ECG 30データ）
- 基盤の CH とダミーの CH が同じときだけ同期する。違えば同期状態 0 で、ECG は空（0x1000）
- チャンネル変更命令（STX 'C' 4桁 ETX）を受けると、基盤の CH がすぐ変わり、
  ダミーは FOLLOW_SEC 秒後に付いてくる（実機では同期し直すまで3〜4秒）
- 電源を入れた直後は、基盤の CH が 0、ダミーは 6001 で三角波（実機と同じ）

試験の場面は属性で切り替える
- link_ok = False … 基盤 → ダミーの線が抜けている（ダミーが付いてこない）
- sending = False … 基盤が出力をやめる
- garble = True … ときどきバイトが化ける
"""

import math
import random
import re
import threading
import time

import serial

PERIOD_SEC = 0.1  # パケットの周期
SAMPLES = 30  # 1パケットのECGデータ数
FOLLOW_SEC = 3.0  # 基盤の CH が変わってから、ダミーが付いてくるまで
SPI_BYTES = 75  # 100ms ごとのSPI受信バイト数
NO_ECG = 0x1000  # ECG が足りないときに基盤が入れる値


def wave_value(wave, i):
    """波形の i 番目の値（中心0、およそ±1000）"""
    if wave == 1001:  # 三角波（150点で1周）
        p = i % 150
        return round((p - 37.5) / 37.5 * 1005) if p < 75 else round((112.5 - p) / 37.5 * 1005)
    if wave == 1002:  # 矩形波
        return 1020 if (i % 150) < 75 else -1020
    if wave == 1003:  # sin波（300点で1周）
        return round(970 * math.sin(2 * math.pi * (i % 300) / 300))
    return 0  # 6001 波形なし


def build_packet(ecg_raw, ch=1001, sync=3, seq=0):
    """検査基盤（to_host.c）と同じ形の100バイトを作る。ecg_raw は 0〜2047（とフラグ）の30個"""
    p = bytearray(100)
    p[0] = 0xF0
    p[1], p[2] = (100 >> 7) & 0x7F, 100 & 0x7F
    p[10], p[11] = (ch >> 7) & 0x7F, ch & 0x7F
    p[22], p[23], p[24] = (seq >> 14) & 0x7F, (seq >> 7) & 0x7F, seq & 0x7F
    p[27] = sync
    p[28] = SPI_BYTES
    for i, v in enumerate(ecg_raw):
        p[38 + i * 2] = (v >> 7) & 0x7F
        p[39 + i * 2] = v & 0x7F
    p[98] = sum(p[0:98]) & 0x7F  # 基盤と同じく開始コードも足す
    p[99] = 0xFF
    return bytes(p)


class FakeSerial:

    def __init__(self, port="FAKE", baudrate=115200, timeout=0.1, **_):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.is_open = True

        self.board_ch = 0
        self.dummy_ch = 6001
        self.dummy_wave = 1001  # 電源を入れた直後のダミーは三角波
        self.link_ok = True
        self.sending = True
        self.garble = False
        self.written = []  # 書き込まれたバイト列（試験で見る）

        self._lock = threading.Lock()
        self._buf = bytearray()
        self._next_at = time.monotonic() + PERIOD_SEC
        self._seq = 0
        self._idx = 0
        self._pending = None  # (ch, 付いてくる時刻)

    def _generate(self):
        """時刻が来た分のパケットを作ってためる"""
        now = time.monotonic()
        while self._next_at <= now:
            self._next_at += PERIOD_SEC

            # ダミーが基盤の CH に付いてくる
            if self._pending and now >= self._pending[1]:
                if self.link_ok:
                    self.dummy_ch = self.dummy_wave = self._pending[0]
                self._pending = None

            if not self.sending:
                continue

            if self.board_ch == self.dummy_ch:
                ecg = [1024 + wave_value(self.dummy_wave, self._idx + k) for k in range(SAMPLES)]
                self._idx += SAMPLES
                sync = 3
            else:
                ecg = [NO_ECG] * SAMPLES
                sync = 0

            pkt = bytearray(build_packet(ecg, self.board_ch, sync, self._seq))
            self._seq += 1
            if self.garble and random.random() < 0.3:
                pkt[random.randrange(1, 99)] |= 0x80
            self._buf += pkt

    @property
    def in_waiting(self):
        with self._lock:
            self._generate()
            return len(self._buf)

    def read(self, size=1):
        if not self.is_open:
            raise serial.SerialException("ポートが閉じています")
        with self._lock:
            self._generate()
            wait = 0 if self._buf else min(self.timeout, max(0.0, self._next_at - time.monotonic()))
        if wait:
            time.sleep(wait)
        with self._lock:
            self._generate()
            out = bytes(self._buf[:size])
            del self._buf[:size]
        return out

    def write(self, data):
        if not self.is_open:
            raise serial.SerialException("ポートが閉じています")
        with self._lock:
            self.written.append(bytes(data))
            m = re.fullmatch(rb"\x02C(\d{4})\x03", bytes(data))
            if m:
                self.board_ch = int(m.group(1))
                self._pending = (self.board_ch, time.monotonic() + FOLLOW_SEC)
        return len(data)

    def close(self):
        self.is_open = False
