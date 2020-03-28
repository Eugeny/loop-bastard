import mido
import threading
import time
from dataclasses import dataclass, replace
from rx.subject import Subject


@dataclass
class SequencerEvent:
    position: float
    message: mido.Message

    def clone(self):
        return replace(self)


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
        q = 4 / self.divisor
        for event in events:
            if event.message.type == 'note_on':
                dp = round(event.position / q) * q - event.position
                event.position += dp
                off = self.sequencer.get_off_event_for_on_event(events, event)
                if off:
                    off.position += dp
        return events


class GateLengthFilter(BaseFilter):
    multiplier = 1

    def filter(self, events):
        for event in events:
            if event.message.type == 'note_on':
                off_event = self.sequencer.get_off_event_for_on_event(events, event)
                if off_event:
                    length = off_event.position - event.position
                    is_wrapped = length < 0
                    if is_wrapped:
                        length += self.sequencer.get_length()
                    length *= self.multiplier
                    off_event.position = event.position + length
                    if is_wrapped:
                        off_event.position -= self.sequencer.get_length()
        return events


class OffsetFilter(BaseFilter):
    offset = 0

    def filter(self, events):
        for event in events:
            if event.message.type == 'note_on':
                off_event = self.sequencer.get_off_event_for_on_event(events, event)
                if off_event:
                    event.position += self.offset
                    off_event.position += self.offset
        return events


class Sequencer:
    def __init__(self, app):
        self.app = app

        self.bars = 4
        self.events = []
        self.filtered_events = []
        self.running = False
        self.recording = False
        self.start_position = 0
        self.stop_flag = False
        self.currently_recording_notes = {}
        self.currently_open_thru_notes = {}
        self.output = Subject()
        self.lock = threading.RLock()

        self.start_scheduled = False

        self.quantizer_filter = QuantizerFilter(self.app, self)
        self.offset_filter = OffsetFilter(self.app, self)
        self.gate_length_filter = GateLengthFilter(self.app, self)

        self.output_channel = 1
        self.thru = False

        self.currently_on = {}

        self.reset()

        self.app.input_manager.clock.subscribe(lambda _: self.on_clock())

    def on_clock(self):
        with self.lock:
            if not self.running:
                event_map = {}
            else:
                event_map = self.get_open_events_at_position(self.get_position(), events=self.filtered_events)
            self.set_notes_on({x.message.note: x.message for x in event_map.values()})

    def get_position(self):
        if not self.running:
            return 0
        return (self.app.tempo.get_position() - self.start_position) % self.get_length()

    def get_length(self):
        return self.bars * self.app.tempo.bar_size

    def reset(self):
        self.stop()
        with self.lock:
            self.events = []
            self.refresh()

    def schedule(self, fx):
        sp = int(self.app.tempo.get_position() / self.app.tempo.bar_size) + 1
        sp *= self.app.tempo.bar_size

        def w():
            time.sleep((sp - self.app.tempo.get_position()) * self.app.tempo.get_beat_time_length())
            fx(sp)

        threading.Thread(target=w).start()

    def schedule_start(self):
        self.start_scheduled = True
        self.schedule(lambda sp: self.start(start_position=sp))

    def schedule_record(self):
        if not self.running:
            self.schedule_start()
        self.recording = True

    def start(self, start_position=None):
        self.start_scheduled = False
        self.start_position = start_position or self.app.tempo.get_position()
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
            if n not in map and n not in self.currently_recording_notes and n not in self.currently_open_thru_notes:
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
                position=self.get_position(),
                message=mido.Message(type='note_off', note=note)
            ))
            self.refresh()

    def normalize_position(self, p):
        return (p + self.get_length()) % self.get_length()

    def get_events_between(self, start, end, events=None):
        if not events:
            events = self.events

        with self.lock:
            if end < start:
                end += self.get_length()

            for event in events[:]:
                if event.position >= start and event.position <= end:
                    yield event

            start -= self.get_length()
            end -= self.get_length()

            for event in events[:]:
                if event.position >= start and event.position <= end:
                    yield event

    def get_open_events_at_position(self, p, events=None):
        if not events:
            events = self.events
        with self.lock:
            m = {}
            for event in self.get_events_between(p + 0.1, p, events=events):
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
                if event.message.note == note and event.position >= start and event.position <= end and event != exclude:
                    self.events.remove(event)

    def is_note_open(self, event):
        return event in self.currently_recording_notes.values()

    def process_message(self, message):
        if self.thru:
            if message.type == 'note_on':
                self.output_message(message)
                self.currently_open_thru_notes[message.note] = message
            if message.type == 'note_off':
                self.output_message(message)
                if message.note in self.currently_open_thru_notes:
                    del self.currently_open_thru_notes[message.note]

        if not self.recording:
            return

        with self.lock:
            position = self.get_position()
            self.refresh()
            if message.type in ['note_on', 'note_off']:
                event = SequencerEvent(
                    position=position,
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
                            self.currently_recording_notes[message.note].position,
                            position,
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
            self.events = sorted(self.events, key=lambda x: x.position)

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
