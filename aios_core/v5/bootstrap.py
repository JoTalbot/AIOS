from .system import AIOSSystem


def create_system():
    system = AIOSSystem()
    return system


def boot():
    system = create_system()
    system.start()
    return system
