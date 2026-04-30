class PktKey:
    """パケットの項目名を定数で定義する"""

    STX = "stx"
    DATA_LEN = "data_len"
    VERSION = "version"
    PACE_MAKER = "pace_maker"
    BATTERY_LOW = "battery_low"
    NURSE_CALL = "nurse_call"
    LEAD_ERR = "lead_err"
    CHANNEL = "channel"
    ANTENNA = "antenna"
    POW_FREQ = "pow_freq"
    HAM_FIL = "ham_fil"
    DRIFT_FIL = "drift_fil"
    MUS_FIL = "mus_fil"
    MUS_STR = "mus_str"
    QRS_MODE = "qrs_mode"
    MAN_QRS = "man_qrs"
    ECG_DISP = "ecg_disp"
    AUTO_QRS = "auto_qrs"
    SEQ_NO = "seq_no"
    OPTION_MODE = "option_mode"
    SYNC_STS = "sync_sts"
    SPI_RX_BYTES = "spi_rx_bytes"
    UART_RX_BYTES = "uart_rx_bytes"
    UP_PROP_CNT = "up_prop_cnt"
    ERR_CNT = "err_cnt"
    ECG = "ecg"
    CHECKSUM = "checksum"
    ETX = "etx"


# (項目名, オフセット, サイズ) のテーブル
PACKET_FIELDS = [
    (PktKey.STX, 0, 1),
    (PktKey.DATA_LEN, 1, 2),
    (PktKey.VERSION, 3, 2),
    (PktKey.PACE_MAKER, 6, 1),
    (PktKey.BATTERY_LOW, 7, 1),
    (PktKey.NURSE_CALL, 8, 1),
    (PktKey.LEAD_ERR, 9, 1),
    (PktKey.CHANNEL, 10, 2),
    (PktKey.ANTENNA, 12, 1),
    (PktKey.POW_FREQ, 13, 1),
    (PktKey.HAM_FIL, 14, 1),
    (PktKey.DRIFT_FIL, 15, 1),
    (PktKey.MUS_FIL, 16, 1),
    (PktKey.MUS_STR, 17, 1),
    (PktKey.QRS_MODE, 18, 1),
    (PktKey.MAN_QRS, 19, 1),
    (PktKey.ECG_DISP, 20, 1),
    (PktKey.AUTO_QRS, 21, 1),
    (PktKey.SEQ_NO, 22, 3),
    (PktKey.OPTION_MODE, 25, 2),
    (PktKey.SYNC_STS, 27, 1),
    (PktKey.SPI_RX_BYTES, 28, 1),
    (PktKey.UART_RX_BYTES, 29, 1),
    (PktKey.UP_PROP_CNT, 30, 1),
    (PktKey.ERR_CNT, 31, 1),
    (PktKey.ETX, 99, 1),
]
