from rx.subject import Subject
import mido
import threading
import time


class InternalClock(threading.Thread):
    def __init__(self, app):
        super().__init__(daemon=True)
        self.bpm = 120
        self.app = app
        self.clock = Subject()

    def _wait(self, until):
        try:
            time.sleep(until - time.time() - 0.001)
        except ValueError:
            return
        while time.time() < until:
            pass

    def run(self):
        while True:
            t_last = time.time()
            self.clock.on_next(None)
            self._wait(t_last + 60 / self.bpm / 24)


class MidiReceiver(threading.Thread):
    def __init__(self, port):
        super().__init__(daemon=True)
        self.stop_flag = False
        self.message = Subject()
        self.clock_found = Subject()
        self.clock = Subject()
        self.clock_lost = Subject()
        self.clock_set = Subject()
        self.clocks_received = None
        self.last_clock_time = None
        self.port_name = port
        self.port = mido.open_input(port)

    def run(self):
        for message in self.port:
            if message.type == 'songpos':
                self.clock_set.on_next(message.pos * 24)
                print('{}: MIDI clock set: {}'.format(self.port_name, message.pos))
            elif message.type == 'clock':
                if not self.last_clock_time:
                    self.clock_found.on_next(None)
                    self.clocks_received = 0
                    print('{}: MIDI clock found'.format(self.port_name))
                self.clocks_received += 1
                self.clock.on_next(None)
                self.last_clock_time = time.time()
            else:
                self.message.on_next(message)
                print('{} -> {}'.format(self.port_name, message))

            if self.stop_flag:
                break

            if self.last_clock_time and time.time() - self.last_clock_time > 1:
                self.last_clock_time = None
                self.clock_lost.on_next(None)
                self.clocks_received = None
                print('{}: MIDI clock lost'.format(self.port_name))

    def stop(self):
        self.stop_flag = True
        self.message.on_completed()
        if self.last_clock_time:
            self.clock_lost.on_next(None)


class InputManager(threading.Thread):
    def __init__(self, app):
        super().__init__(daemon=True)
        self.app = app
        self.known_ports = []
        self.receivers = {}
        self.message = Subject()
        self.internal_clock = InternalClock(app)
        self.active_clock = None
        self.clock_found = Subject()
        self.clock = Subject()
        self.clock_lost = Subject()
        self.clock_set = Subject()
        self.internal_clock.clock.subscribe(lambda _: self.on_internal_clock())

    def start(self):
        super().start()
        self.internal_clock.start()

    def has_input(self):
        return len(self.known_ports) > 0

    def on_internal_clock(self):
        if not self.active_clock:
            self.clock.on_next(None)

    def on_clock(self, receiver):
        if not self.active_clock:
            self.active_clock = receiver
            self.clock_found.on_next(None)
            print('New active clock: {}'.format(receiver.port_name))
        self.clock.on_next(None)

    def on_clock_lost(self, receiver):
        self.active_clock = None
        self.clock_lost.on_next(None)
        print('Lost external clock')

    def on_message(self, port, message):
        for x in self.app.output_manager.recently_sent:
            if x[1] == message and time.time() - x[0] < 0.1:
                return
        self.message.on_next([port, message])

    def run(self):
        while True:
            ports = [x for x in mido.get_input_names() if 'Through' not in x]
            if ports != self.known_ports:
                for port in ports:
                    if port not in self.known_ports:
                        print('Connected', port)
                        receiver = MidiReceiver(port)
                        receiver.start()
                        receiver.message.subscribe(lambda message: self.on_message(port, message))
                        receiver.clock.subscribe(lambda _: self.on_clock(receiver))
                        receiver.clock_lost.subscribe(lambda _: self.on_clock_lost(receiver))
                        receiver.clock_set.subscribe(self.clock_set.on_next)
                        self.receivers[port] = receiver

                for port in self.known_ports:
                    if port not in ports:
                        print('Disconnected', port)
                        if port in self.receivers:
                            self.receivers[port].stop()
                            del self.receivers[port]

                self.known_ports = ports

            time.sleep(0.1)
