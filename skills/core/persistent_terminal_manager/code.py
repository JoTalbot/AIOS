import os
import pty
import select
import threading
import time
import collections

class PersistentTerminal:
    def __init__(self, shell='/bin/bash'):
        self.master, self.slave = pty.openpty()
        self.pid = os.fork()
        
        if self.pid == 0:
            os.close(self.master)
            os.dup2(self.slave, 0)
            os.dup2(self.slave, 1)
            os.dup2(self.slave, 2)
            os.close(self.slave)
            os.execv(shell, [shell])
        else:
            os.close(self.slave)
            self.buffer = collections.deque(maxlen=10000)
            self.running = True
            self.last_output_time = time.time()
            self.thread = threading.Thread(target=self._read_output, daemon=True)
            self.thread.start()

    def _read_output(self):
        while self.running:
            try:
                r, w, e = select.select([self.master], [], [], 0.1)
                if self.master in r:
                    data = os.read(self.master, 1024).decode('utf-8', errors='ignore')
                    if data:
                        self.buffer.append(data)
                        self.last_output_time = time.time()
            except:
                break

    def send_input(self, data):
        os.write(self.master, data.encode('utf-8'))

    def get_output(self):
        return ''.join(self.buffer)

    def wait_idle(self, timeout=5.0, idle_time=0.5):
        start_time = time.time()
        while time.time() - start_time < timeout:
            if time.time() - self.last_output_time > idle_time:
                return True
            time.sleep(0.1)
        return False

    def stop(self):
        self.running = False
        os.close(self.master)

# Пример использования (тестовый запуск)
if __name__ == '__main__':
    term = PersistentTerminal()
    term.send_input('ls -la\n')
    if term.wait_idle():
        print('Output received:')
        print(term.get_output())
    term.stop()
