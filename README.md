# 受信ユニット検査治具（波形表示アプリ）

検査基盤から UART（115200bps）で来る波形を表示し、チャンネル変更命令を送る。

## 動かし方
- `python main.py` … 起動する
- `python main.py --fake` … ハードなしで動かす。ポートの一覧に「FAKE」が出て、検査基盤のふり（`fake_board.py`）につながる
- `python -m PyInstaller --noconfirm main.spec` … `dist\main.exe` を作る

## 試験
- `python -m unittest discover -s tests -v`
- `tests/test_view.py` は窓を作るので、画面のある PC で回す

## ファイル
| ファイル | 中身 |
|---|---|
| `main.py` | 入口 |
| `view.py` | 窓・開始と停止・送信・定期更新 |
| `view_control_panel.py` | 左の操作パネル（① ポート → ② 受信 → ③ 波形を送る） |
| `view_status.py` | 上の状態表示（受信・同期）と下の数字（CH・パケット） |
| `view_wave_chart.py` | 波形表示（matplotlib。左から右へ上書き） |
| `jig_state.py` | 受信・同期・波形の状態を決める（画面には触らない） |
| `serial_reader.py` | COM ポートとパケットの切り出し |
| `packet.py` | パケットの項目の位置 |
| `fake_board.py` | 検査基盤のふり（試験と `--fake` 用） |
| `theme.py` | 色と文字 |
