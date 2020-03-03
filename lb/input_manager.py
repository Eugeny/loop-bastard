from rx.subject import Subject
import mido
import threading
import time
from mido.ports import multi_receive


class MidiReceiver(threading.Thread):
    message = Subject()

    def __init__(self, ports):
        super().__init__(daemon=True)
        self.stop_flag = False
        self.ports = [mido.open_input(name) for name in ports]

    def run(self):
        for message in multi_receive(self.ports):
            self.message.on_next(message)
            print('Received {}'.format(message))
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

    def run(self):
        while True:
            ports = mido.get_input_names()
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
                self.receiver_thread.message.subscribe(self.message)
            time.sleep(0.1)
