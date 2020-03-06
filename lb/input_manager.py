from rx.subject import Subject
import mido
import threading
import time
from mido.ports import multi_receive


class MidiReceiver(threading.Thread):
    def __init__(self, ports):
        super().__init__(daemon=True)
        self.stop_flag = False
        self.message = Subject()
        self.ports = [mido.open_input(name) for name in ports]

    def run(self):
        for port, message in multi_receive(self.ports, yield_ports=True):
            self.message.on_next([port, message])
            print('{} -> {}'.format(port, message))
            if self.stop_flag:
                break

    def stop(self):
        self.stop_flag = True
        self.message.on_completed()


class InputManager(threading.Thread):
    message = Subject()

    def __init__(self):
        super().__init__(daemon=True)
        self.known_ports = []
        self.receiver_thread = None

    def has_input(self):
        return len(self.known_ports) > 0

    def run(self):
        while True:
            ports = [x for x in mido.get_input_names() if 'Through' not in x]
            if ports != self.known_ports:
                if self.receiver_thread:
                    self.receiver_thread.stop()

                for port in ports:
                    if port not in self.known_ports:
                        print('Connected', port)
                for port in self.known_ports:
                    if port not in ports:
                        print('Disconnected', port)

                self.known_ports = ports

                self.receiver_thread = MidiReceiver(ports)
                self.receiver_thread.start()
                self.receiver_thread.message.subscribe(lambda m: self.message.on_next(m))
            time.sleep(0.1)
