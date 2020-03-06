import mido
import threading
import time
from dataclasses import dataclass
from rx.subject import Subject


@dataclass
class SequencerEvent:
    time: float
    message: mido.Message


class SequencerPlayer(threading.Thread):
    def __init__(self, sequencer):
        super().__init__(daemon=True)
        self.sequencer = sequencer
        self.stop_flag = False

    def stop(self):
        self.stop_flag = True

    def run2(self):
        next_idx = 0
        while True:
            if not self.sequencer.events:
                time.sleep(1)
                continue
            if next_idx >= len(self.sequencer.events):
                next_idx = 0

            next_time = self.sequencer.events[next_idx].time

            wait_time = next_time - self.sequencer.get_time()
            if wait_time < 0 and next_idx == 0:
                wait_time = self.sequencer.normalize_time(wait_time)
            if wait_time > 0:
                time.sleep(wait_time)
            if self.stop_flag:
                break

            self.sequencer.output.on_next(self.sequencer.events[next_idx].message)
            next_idx += 1

    def run(self):
        last_time = 0
        next_time = 0
        while True:
            next_time = self.sequencer.get_time() + 1 / 200
            next_wall_time = time.time() + 1 / 200

            for event in self.sequencer.events:
                if (event.time >= last_time and event.time < next_time) or (event.time - self.sequencer.get_length() >= last_time and event.time - self.sequencer.get_length() < next_time):
                    self.sequencer.output.on_next(event.message)

            wait_time = next_wall_time - time.time()
            if wait_time > 0:
                time.sleep(wait_time)
            if self.stop_flag:
                break

            last_time = self.sequencer.normalize_time(next_time)


class Sequencer:
    def __init__(self, app):
        self.app = app

        self.bars = 4
        self.events = []
        self.running = False
        self.recording = False
        self.start_time = 0
        self.stop_flag = False
        self.open_note_on_events = {}
        self.output = Subject()
        self.player_thread = None
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
        if self.recording:
            self.stop_recording()
            return
        self.start_time = self.app.tempo.get_time()
        self.running = True
        self.player_thread = SequencerPlayer(self)
        self.player_thread.start()

    def record(self):
        if not self.running:
            self.start()
        self.recording = True

    def stop_recording(self):
        self.recording = False
        self.close_open_notes()

    def stop(self):
        self.running = False
        self.recording = False
        self.close_open_notes()
        if self.player_thread:
            self.player_thread.stop()
            self.player_thread = None

        for i in range(0, 128):
            self.app.output_manager.send_to_all(mido.Message(type='note_off', note=i))

    def close_open_notes(self):
        for note in self.open_note_on_events.keys():
            self.events.append(SequencerEvent(
                time=self.get_time(),
                message=mido.Message(type='note_off', note=note)
            ))
            self.cleanup()

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

    def process_message(self, message):
        if not self.recording:
            return

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
                    if message.note in self.open_note_on_events:
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

    def quantize(self):
        q = self.app.tempo.q_to_time((1, 2, 1))
        for x in self.events:
            x.time = round(x.time / q) * q
