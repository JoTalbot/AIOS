class AndroidDeviceManager:
    """Android node lifecycle management foundation."""

    def __init__(self):
        self.devices = {}

    def register(self, device_id, connector):
        self.devices[device_id] = connector

    def list_devices(self):
        return list(self.devices.keys())
