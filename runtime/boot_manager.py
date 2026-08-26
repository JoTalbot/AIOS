class BootManager:
    def __init__(self, kernel=None):
        self.kernel = kernel

    def boot(self):
        if self.kernel:
            self.kernel.start()
