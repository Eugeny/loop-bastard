import mido
import threading
import time
from dataclasses import dataclass
from rx.subject import Subject


@dataclass
class SequencerEvent:
    time: float
    message: mido.Message


class Sequencer(threading.Thread):
    bars = 2
    events = []
    running = False
    recording = False
    start_time = 0
    stop_flag = False
    open_note_on_events = {}
    output = Subject()

    def __init__(self, app):
        super().__init__(daemon=True)
        self.app = app
        self.lock = threading.RLock()
        self.reset()

    def get_time(self):
        if not self.running:
            return 0
        return (self.app.tempo.get_time() - self.start_time) % self.get_length()

    def get_length(self):
        return self.app.tempo.q_to_time((1, self.bars + 1, 1))

    def get_q(self):
        return self.app.tempo.pos_to_q(self.app.tempo.time_to_pos(self.get_time()))

    def reset(self):
        with self.lock:
            self.events = []

    def start(self):
        self.start_time = self.app.tempo.get_time()
        self.running = True
        super().start()
        self.stop_flag = False

    def record(self):
        self.recording = True
        self.start()

    def stop(self):
        self.running = False
        self.recording = False
        self.stop_flag = True
        #for i in range(0, 128):

    def normalize_time(self, t):
        return (t + self.get_length()) % self.get_length()

    def remove_notes_between(self, note, start, end, exclude):
        with self.lock:
            if end < start:
                end += self.get_length()
            for event in self.events[:]:
                if event.message.note == note and event.time >= start and event.time <= end and event != exclude:
                    self.events.remove(event)

    def remove_notes_at(self, note, time):
        with self.lock:
            m = {}
            for event in self.events[:]:
                if event.message.note == note:
                    if event.time <= time:
                        if event.message.type == 'note_on':
                            m[event.message.note] = event
                        if event.message.type == 'note_off':
                            del m[event.message.note]
                    else:
                        if event.message.type == 'note_off' and event.message.note in m:
                            self.events.remove(m[event.message.note])
                            del m[event.message.note]
                            self.events.remove(event)
            self.cleanup()

    def is_note_open(self, event):
        return event in self.open_note_on_events.values()

    def add(self, message):
        with self.lock:
            time = self.get_time()
            self.cleanup()
            if message.type in ['note_on', 'note_off']:
                event = SequencerEvent(
                    time=time,
                    message=message,
                )
                if message.type == 'note_on':
                    self.open_note_on_events[message.note] = event
                    self.events.append(event)
                if message.type == 'note_off':
                    if self.open_note_on_events[message.note]:
                        self.remove_notes_between(
                            message.note,
                            self.open_note_on_events[message.note].time,
                            time,
                            self.open_note_on_events[message.note],
                        )
                        del self.open_note_on_events[message.note]
                        self.events.append(event)

            self.cleanup()

    def cleanup(self):
        with self.lock:
            self.events = sorted(self.events, key=lambda x: x.time)

            m = {}
            for event in self.events[:]:
                if event.message.type == 'note_on':
                    m[event.message.note] = event
                if event.message.type == 'note_off':
                    if event.message.note in m:
                        del m[event.message.note]

    def run(self):
        next_idx = 0
        while True:
            if not self.events:
                time.sleep(1)
                continue
            if next_idx >= len(self.events):
                next_idx = 0
            next_time = self.events[next_idx].time
            time.sleep(self.normalize_time(next_time - self.get_time()))
            if self.stop_flag:
                break

            self.output.on_next(self.events[next_idx].message)
            next_idx += 1
