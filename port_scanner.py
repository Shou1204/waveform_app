from serial.tools import list_ports


class PortScanner:

    @staticmethod
    def get_ports():
        """使用可能なCOMポートのリストを返す"""
        ports = [port.device for port in list_ports.comports()]
        return ports if ports else [""]
