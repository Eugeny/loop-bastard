import mido
import time
import threading
from rx.subject import Subject


class OutputManager(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.known_ports = []
        self.open_ports = {}
        self.message = Subject()
        self.recently_sent = []

    def has_output(self):
        return len(self.known_ports) > 0

    def run(self):
        while True:
            ports = mido.get_output_names()
            if ports != self.known_ports:
                for port in ports:
                    if port not in self.known_ports:
                        print('Connected output', port)
                        self.open_ports[port] = mido.open_output(port)
                for port in self.known_ports:
                    if port not in ports:
                        print('Disconnected output', port)
                        self.open_ports[port].close()
                        del self.open_ports[port]

                self.known_ports = ports

            time.sleep(0.1)

    def send_to_all(self, message):
        self.message.on_next(message)
        print('Sent', message)
        for port in self.open_ports.values():
            port.send(message)
        self.recently_sent.append((time.time(), message))
        self.recently_sent = self.recently_sent[-50:]
