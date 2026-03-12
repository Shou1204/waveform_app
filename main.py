from serial_reader import SerialReader
from packet import PktKey

# 確認したいCOMポートに変更してください
PORT = "COM7"

reader = SerialReader(port=PORT)
reader.open()
reader.sync()

for _ in range(5):
    reader.sync()
    packet = reader.read()
    if packet:
        print(f"シーケンスNo: {packet[PktKey.SEQ_NO]}")
        print(f"チャンネル:   {packet[PktKey.CHANNEL]}")
        print(f"ECGデータ:    {packet[PktKey.ECG]}")
        print("---")

reader.close()
