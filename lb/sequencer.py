import mido
import threading
import time
from dataclasses import dataclass, replace
from rx.subject import Subject


@dataclass
class SequencerEvent:
    time: float
    message: mido.Message

    def clone(self):
        return replace(self)


class SequencerPlayer(threading.Thread):
    def __init__(self, sequencer):
        super().__init__(daemon=True)
        self.sequencer = sequencer

    def run(self):
        cycle_len = self.sequencer.app.tempo.get_beat_length() / 100
        while True:
            time.sleep(cycle_len)
            if not self.sequencer.running:
                event_map = {}
            else:
                event_map = self.sequencer.get_open_events_at(self.sequencer.get_time(), events=self.sequencer.filtered_events)
            self.sequencer.set_notes_on({x.message.note: x.message for x in event_map.values()})

    def run2(self):
        next_idx = 0
        while True:
            if not self.sequencer.events:
                time.sleep(1)
                continue
            if next_idx >= len(self.sequencer.events):
                next_idx = 0

            event = self.sequencer.events[next_idx]
            next_time = event.time

            wait_time = next_time - self.sequencer.get_time()
            if wait_time < 0 and next_idx == 0:
                wait_time = self.sequencer.normalize_time(wait_time)
            if wait_time > 0:
                time.sleep(wait_time)
            if self.stop_flag:
                self.sequencer.off_everything()
                break

            self.sequencer.output_message(event.message)
            next_idx += 1

    def run3(self):
        last_time = 0
        next_time = 0
        cycle_len = self.sequencer.app.tempo.get_beat_length() / 100
        while True:
            next_time = self.sequencer.get_time() + cycle_len
            next_wall_time = time.time() + cycle_len

            for event in self.sequencer.events:
                if (event.time >= last_time and event.time < next_time) or (event.time - self.sequencer.get_length() >= last_time and event.time - self.sequencer.get_length() < next_time):
                    self.sequencer.output_message(event.message)

            wait_time = next_wall_time - time.time()
            if wait_time > 0:
                time.sleep(wait_time)
            if self.stop_flag:
                self.sequencer.off_everything()
                break

            last_time = self.sequencer.normalize_time(next_time)


class BaseFilter:
    def __init__(self, app, sequencer):
        self.app = app
        self.sequencer = sequencer

    def filter(self, events):
        return events


class QuantizerFilter(BaseFilter):
    enabled = False
    divisor = 8

    def filter(self, events):
        if not self.enabled:
            return events
        q = self.app.tempo.get_beat_length() * 4 / self.divisor
        for event in events:
            if event.message.type == 'note_on':
                dt = round(event.time / q) * q - event.time
                event.time += dt
                off = self.sequencer.get_off_event_for_on_event(events, event)
                off.time += dt
        return events


class GateLengthFilter(BaseFilter):
    multiplier = 1

    def filter(self, events):
        for event in events:
            if event.message.type == 'note_on':
                off_event = self.sequencer.get_off_event_for_on_event(events, event)
                if off_event:
                    length = off_event.time - event.time
                    is_wrapped = length < 0
                    if is_wrapped:
                        length += self.sequencer.get_length()
                    length *= self.multiplier
                    off_event.time = event.time + length
                    if is_wrapped:
                        off_event.time -= self.sequencer.get_length()
        return events


class OffsetFilter(BaseFilter):
    offset = 0

    def filter(self, events):
        offset = self.offset * self.app.tempo.get_beat_length()
        for event in events:
            if event.message.type == 'note_on':
                off_event = self.sequencer.get_off_event_for_on_event(events, event)
                if off_event:
                    event.time += offset
                    off_event.time += offset
        return events


class Sequencer:
    def __init__(self, app):
        self.app = app

        self.bars = 4
        self.events = []
        self.filtered_events = []
        self.running = False
        self.recording = False
        self.start_time = 0
        self.stop_flag = False
        self.currently_recording_notes = {}
        self.output = Subject()
        self.player_thread = None
        self.lock = threading.RLock()

        self.start_scheduled = False

        self.quantizer_filter = QuantizerFilter(self.app, self)
        self.offset_filter = OffsetFilter(self.app, self)
        self.gate_length_filter = GateLengthFilter(self.app, self)

        self.output_channel = 1
        self.thru = False

        self.currently_on = {}
        self.player_thread = SequencerPlayer(self)
        self.player_thread.start()

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
        self.stop()
        with self.lock:
            self.events = []

    def schedule(self, fx):
        st = int(self.app.tempo.get_time() / self.app.tempo.get_bar_length()) + 1
        st *= self.app.tempo.get_bar_length()

        def w():
            time.sleep(st - self.app.tempo.get_time())
            fx(st)

        threading.Thread(target=w).start()

    def schedule_start(self):
        self.start_scheduled = True
        self.schedule(lambda st: self.start(start_time=st))

    def schedule_record(self):
        if not self.running:
            self.schedule_start()
        self.recording = True

    def start(self, start_time=None):
        self.start_scheduled = False
        self.start_time = start_time or self.app.tempo.get_time()
        self.running = True

    def record(self):
        if not self.running:
            self.start()
        self.recording = True

    def stop_recording(self):
        self.recording = False
        self.close_open_notes()

    def schedule_stop(self):
        self.schedule(lambda st: self.stop())

    def stop(self):
        self.running = False
        if self.recording:
            self.recording = False
            self.close_open_notes()

        self.off_everything()

    def set_notes_on(self, map):
        for n in list(self.currently_on.keys()):
            if n not in map:
                self.output_message(mido.Message(type='note_off', note=n))
        for n in map:
            if n not in self.currently_on:
                self.output_message(map[n])

    def off_everything(self):
        for n in list(self.currently_on.keys()):
            self.output_message(mido.Message(type='note_off', note=n))

    def output_message(self, message: mido.Message):
        message = message.copy(channel=self.output_channel)
        self.output.on_next(message)

        if message.type == 'note_on':
            self.currently_on[message.note] = message
        if message.type == 'note_off':
            if message.note in self.currently_on:
                del self.currently_on[message.note]

    def close_open_notes(self):
        for note in self.currently_recording_notes.keys():
            self.events.append(SequencerEvent(
                time=self.get_time(),
                message=mido.Message(type='note_off', note=note)
            ))
            self.refresh()

    def normalize_time(self, t):
        return (t + self.get_length()) % self.get_length()

    def get_events_between(self, start, end, events=None):
        if not events:
            events = self.events

        with self.lock:
            if end < start:
                end += self.get_length()

            for event in self.events[:]:
                if event.time >= start and event.time <= end:
                    yield event

            start -= self.get_length()
            end -= self.get_length()

            for event in self.events[:]:
                if event.time >= start and event.time <= end:
                    yield event

    def get_open_events_at(self, t, events=None):
        if not events:
            events = self.events
        with self.lock:
            m = {}
            for event in self.get_events_between(t + 0.1, t, events=events):
                if event.message.type == 'note_on':
                    m[event.message.note] = event
                if event.message.type == 'note_off' and event.message.note in m:
                    del m[event.message.note]
        return m

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
            self.refresh()

    def is_note_open(self, event):
        return event in self.currently_recording_notes.values()

    def process_message(self, message):
        if self.thru:
            if message.type in ['note_on', 'note_off']:
                self.output_message(message)

        if not self.recording:
            return

        with self.lock:
            time = self.get_time()
            self.refresh()
            if message.type in ['note_on', 'note_off']:
                event = SequencerEvent(
                    time=time,
                    message=message,
                )
                if message.type == 'note_on':
                    self.currently_recording_notes[message.note] = event
                    self.currently_on[message.note] = event
                    self.events.append(event)
                if message.type == 'note_off':
                    if message.note in self.currently_recording_notes:
                        self.remove_notes_between(
                            message.note,
                            self.currently_recording_notes[message.note].time,
                            time,
                            self.currently_recording_notes[message.note],
                        )
                        del self.currently_recording_notes[message.note]
                        self.events.append(event)
                    if message.note in self.currently_on:
                        del self.currently_on[message.note]

            self.refresh()

    def get_off_event_for_on_event(self, events, event):
        for e in events[events.index(event):]:
            if e.message.type == 'note_off' and e.message.note == event.message.note:
                return e
        for e in events[:events.index(event)]:
            if e.message.type == 'note_off' and e.message.note == event.message.note:
                return e

    def refresh(self):
        with self.lock:
            self.events = sorted(self.events, key=lambda x: x.time)

            m = {}
            for event in self.events[:]:
                if event.message.type == 'note_on':
                    m[event.message.note] = event
                if event.message.type == 'note_off':
                    if event.message.note in m:
                        del m[event.message.note]

            events = [x.clone() for x in self.events]
            events = self.offset_filter.filter(events)
            events = self.gate_length_filter.filter(events)
            events = self.quantizer_filter.filter(events)
            self.filtered_events = events
