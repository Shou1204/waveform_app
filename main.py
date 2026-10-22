import ctypes
import sys

# 高解像度の画面で文字がにじまないようにする（窓を作る前に呼ぶ）
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

from view import View  # noqa: E402

if "--fake" in sys.argv:
    # ハードなしで動かす（ポートの一覧に FAKE が出る）
    import serial

    from fake_board import FakeSerial

    def factory(port, **kwargs):
        return FakeSerial(port, **kwargs) if port == "FAKE" else serial.Serial(port=port, **kwargs)

    app = View(serial_factory=factory, extra_ports=["FAKE"])
else:
    app = View()

app.mainloop()
