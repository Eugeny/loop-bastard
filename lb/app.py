import json
import logging
import math
import os
import threading
from collections import defaultdict
from .controls import Controls
from .input_manager import InputManager
from .output_manager import OutputManager
from .sequencer import Sequencer
from .tempo import Tempo
from .display import Display
from .util import number_to_note, list_next, list_prev


class MetronomeParam:
    name = 'Metronome'
    type = 'list'

    def __init__(self, app):
        self.app = app
        self.options = [False, True]

    def get(self):
        return self.app.tempo.enable_metronome

    def set(self, v):
        self.app.tempo.enable_metronome = v

    def ok(self):
        self.app.tempo.enable_metronome = not self.app.tempo.enable_metronome

    def is_on(self):
        return self.app.tempo.enable_metronome

    def to_str(self, v):
        return 'On' if v else 'Off'


class QuantizerParam:
    name = 'Quantizer'
    type = 'list'

    def __init__(self, app):
        self.app = app
        self.options = [1, 2, 4, 8, 16, 32, None]

    def get(self):
        return self.app.selected_sequencer.quantizer_filter.divisor

    def set(self, v):
        self.app.selected_sequencer.quantizer_filter.divisor = v
        self.app.selected_sequencer.refresh()

    def ok(self):
        pass

    def is_on(self):
        return self.get() is not None

    def to_str(self, v):
        if not v:
            return 'Off'
        return f'1/{v}'


class GateLengthParam:
    name = 'Gate length'
    type = 'dial'

    def __init__(self, app):
        self.app = app
        self.options = [x / 10 for x in range(1, 9)] + [math.sqrt(x / 10) for x in range(10, 170, 8)]

    def get(self):
        return self.app.selected_sequencer.gate_length_filter.multiplier

    def set(self, v):
        self.app.selected_sequencer.gate_length_filter.multiplier = v
        self.app.selected_sequencer.refresh()

    def ok(self):
        pass

    def is_on(self):
        return self.get() != 1

    def to_str(self, v):
        return f'{v:.1f}x'


class OffsetParam:
    name = 'Offset'
    type = 'dial'

    def __init__(self, app):
        self.app = app
        self.options = [x / 10 for x in range(-10, 11)]

    def get(self):
        return self.app.selected_sequencer.offset_filter.offset

    def set(self, v):
        self.app.selected_sequencer.offset_filter.offset = v
        self.app.selected_sequencer.refresh()

    def ok(self):
        pass

    def is_on(self):
        return self.get() != 0

    def to_str(self, v):
        if v > 0:
            return f'+{v:.1f}'
        return f'-{v:.1f}'


class LengthParam:
    name = 'Length'
    type = 'dial'

    def __init__(self, app):
        self.app = app
        self.options = list(range(1, 17))

    def get(self):
        return self.app.selected_sequencer.bars

    def set(self, v):
        self.app.selected_sequencer.bars = v

    def ok(self):
        pass

    def is_on(self):
        return True

    def to_str(self, v):
        return f'{v} bars'


class TempoParam:
    name = 'Tempo'
    type = 'dial'

    def __init__(self, app):
        self.app = app
        self.options = list(range(60, 201))

    def get(self):
        return self.app.input_manager.internal_clock.bpm

    def set(self, v):
        self.app.input_manager.internal_clock.bpm = v

    def ok(self):
        pass

    def is_on(self):
        return self.app.input_manager.active_clock

    def to_str(self, v):
        return 'External' if self.app.input_manager.active_clock else f'{v} BPM'


class InputChannelParam:
    name = 'Input ch.'
    type = 'midi-channel'

    def __init__(self, app):
        self.app = app
        self.options = [None] + list(range(1, 17))

    def get(self):
        return self.app.selected_sequencer.input_channel

    def set(self, v):
        self.app.selected_sequencer.input_channel = v

    def ok(self):
        self.set(None if self.get() else 1)

    def is_on(self):
        return True

    def to_str(self, v):
        return 'All' if not v else f'Ch. {v}'


class OutputChannelParam:
    name = 'Output ch.'
    type = 'midi-channel'

    def __init__(self, app):
        self.app = app
        self.options = list(range(1, 17))

    def get(self):
        return self.app.selected_sequencer.output_channel

    def set(self, v):
        self.app.selected_sequencer.output_channel = v

    def ok(self):
        pass

    def is_on(self):
        return True

    def to_str(self, v):
        return f'Ch. {v}'


class BaseNoteParam:
    def _get_events(self):
        sequencer = self.app.selected_sequencer
        if self.app.selected_event is None:
            return None, None
        e_on = self.app.selected_event
        e_off = sequencer.get_off_event_for_on_event(sequencer.events, self.app.selected_event)
        return e_on, e_off


class NotePitchParam(BaseNoteParam):
    name = 'Pitch'
    type = 'list'

    def __init__(self, app):
        self.app = app
        self.options = list(range(128))

    def get(self):
        on, _ = self._get_events()
        if on:
            return on.message.note
        return 0

    def set(self, v):
        on, off = self._get_events()
        if on:
            on.message.note = v
            off.message.note = v
        self.app.selected_sequencer.refresh()

    def ok(self):
        pass

    def is_on(self):
        return True

    def to_str(self, v):
        note, octave = number_to_note(v)
        return f'{note}{octave}'


class NoteLengthParam(BaseNoteParam):
    name = 'Length'
    type = 'dial'

    def __init__(self, app):
        self.app = app
        self.options = list(range(1, 32 * 16))

    def get(self):
        on, off = self._get_events()
        if on:
            return round(32 * (off.position - on.position))
        return 0

    def set(self, v):
        on, off = self._get_events()
        if on:
            off.position = on.position + v / 32
        self.app.selected_sequencer.refresh()

    def ok(self):
        pass

    def is_on(self):
        return True

    def to_str(self, v):
        return f'{v:.1f}'


class NoteVelocityParam(BaseNoteParam):
    name = 'Velocity'
    type = 'dial'

    def __init__(self, app):
        self.app = app
        self.options = list(range(128))

    def get(self):
        on, _ = self._get_events()
        if on:
            return on.message.velocity
        return 0

    def set(self, v):
        on, _ = self._get_events()
        if on:
            on.message.velocity = v
        self.app.selected_sequencer.refresh()

    def ok(self):
        pass

    def is_on(self):
        return True

    def to_str(self, v):
        return str(v)


class App:
    def __init__(self):
        self.input_manager = InputManager(self)
        self.output_manager = OutputManager()
        self.controls = Controls(self)
        self.tempo = Tempo(self)

        self.input_manager.start()
        self.output_manager.start()
        self.controls.start()
        self.tempo.start()

        self.saved_state_path = 'state.json'
        self.selected_sequencer = None
        self.selected_sequencer_bank = 0
        self.seleted_event = None
        self.sequencer_is_empty = defaultdict(lambda: True)

        self.sequencer_bank_size = len(self.controls.number_buttons)
        self.sequencer_banks = len(self.controls.number_buttons)

        self.sequencers = []
        for i in range(self.sequencer_banks * self.sequencer_bank_size):
            s = Sequencer(self)
            self.sequencers.append(s)
            s.output.subscribe(lambda msg: self.output_manager.send_to_all(msg))

        self.state_file_lock = threading.RLock()
        self.enable_state_saving = False

        self.select_sequencer(self.sequencers[0])

        self.input_manager.message.subscribe(lambda x: self.process_message(x[0], x[1]))

        if False:
            for i in range(16):
                import mido
                from lb.sequencer import SequencerEvent
                self.sequencers[0].events.append(
                    SequencerEvent(message=mido.Message('note_on', note=64+i), position=i/3.7),
                )
                self.sequencers[0].events.append(
                    SequencerEvent(message=mido.Message('note_off', note=64+i), position=i/3.7+.35),
                )
            self.sequencers[0].refresh()

        self.current_scope = 'sequencer'
        self.metronome_param = MetronomeParam(self)
        self.tempo_param = TempoParam(self)
        self.scope_params = {
            'global': [
                MetronomeParam(self),
            ],
            'sequencer': [
                QuantizerParam(self),
                GateLengthParam(self),
                OffsetParam(self),
                LengthParam(self),
                self.tempo_param,
                self.metronome_param,
                InputChannelParam(self),
                OutputChannelParam(self),
            ],
            'note': [
                NotePitchParam(self),
                NoteLengthParam(self),
                NoteVelocityParam(self),
            ],
        }
        self.current_param = {
            'sequencer': self.scope_params['sequencer'][0],
            'note': self.scope_params['note'][0],
        }

        self.controls.rotary_param.left.subscribe(lambda _: self.param_next())
        self.controls.rotary_param.right.subscribe(lambda _: self.param_prev())
        self.controls.rotary_value.left.subscribe(lambda _: self.value_dec())
        self.controls.rotary_value.right.subscribe(lambda _: self.value_inc())
        self.controls.play_button.press.subscribe(lambda _: self.on_play())
        self.controls.stop_button.press.subscribe(lambda _: self.on_stop())
        self.controls.record_button.press.subscribe(lambda _: self.on_record())
        self.controls.clear_button.press.subscribe(lambda _: self.on_clear())
        self.controls.scope_button.press.subscribe(lambda _: self.on_scope())
        self.controls.ok_button.press.subscribe(lambda _: self.on_ok())

        for i in range(len(self.controls.number_buttons)):
            self.controls.number_buttons[i].press.subscribe((lambda i: lambda _: self.on_number(i))(i))

        self.load_state()
        self.enable_state_saving = True

        self.display = Display(self)
        self.display.run()

    def select_sequencer(self, s):
        if self.selected_sequencer:
            self.selected_sequencer.close_open_notes()
            self.selected_sequencer.thru = False
            if self.sequencer_is_empty[s]:
                s.load_state(self.selected_sequencer.save_state())
                s.events = []
                s.refresh()

        self.sequencer_is_empty[s] = False
        self.selected_event = None

        self.selected_sequencer = s
        self.selected_sequencer.thru = True
        self.save_state()

    def process_message(self, port, msg):
        for s in self.sequencers:
            s.process_message(msg)

    def param_prev(self):
        if self.controls.shift_button.pressed:
            self.current_scope = 'note'
            events = [x for x in self.selected_sequencer.events if x.message.type == 'note_on']
            self.selected_event = list_prev(events, self.selected_event)
        else:
            self.current_param[self.current_scope] = list_prev(self.scope_params[self.current_scope], self.current_param[self.current_scope])

    def param_next(self):
        if self.controls.shift_button.pressed:
            self.current_scope = 'note'
            events = [x for x in self.selected_sequencer.events if x.message.type == 'note_on']
            self.selected_event = list_next(events, self.selected_event)
        else:
            self.current_param[self.current_scope] = list_next(self.scope_params[self.current_scope], self.current_param[self.current_scope])

    def value_dec(self):
        self.current_param[self.current_scope].set(
            list_prev(
                self.current_param[self.current_scope].options,
                self.current_param[self.current_scope].get()
            )
        )
        self.sequencer_is_empty[self.selected_sequencer] = False
        self.save_state()

    def value_inc(self):
        self.current_param[self.current_scope].set(
            list_next(
                self.current_param[self.current_scope].options,
                self.current_param[self.current_scope].get()
            )
        )
        self.sequencer_is_empty[self.selected_sequencer] = False
        self.save_state()

    def on_number(self, i):
        if self.controls.shift_button.pressed:
            self.selected_sequencer_bank = i
            self.select_sequencer(self.sequencers[self.selected_sequencer_bank * self.sequencer_bank_size])
        else:
            self.select_sequencer(self.sequencers[self.selected_sequencer_bank * self.sequencer_bank_size + i])

    def on_ok(self):
        self.current_param[self.current_scope].ok()
        self.save_state()

    def on_play(self):
        if self.selected_sequencer.running:
            if self.selected_sequencer.recording:
                self.selected_sequencer.stop_recording()
                return

        if self.controls.shift_button.pressed:
            self.selected_sequencer.start()
        else:
            self.selected_sequencer.schedule_start()

        for s in self.sequencers:
            if s != self.selected_sequencer and s.output_channel == self.selected_sequencer.output_channel:
                if self.controls.shift_button.pressed:
                    s.stop()
                else:
                    s.schedule_stop()
        self.save_state()

    def on_stop(self):
        if self.controls.shift_button.pressed:
            self.selected_sequencer.stop()
        else:
            self.selected_sequencer.schedule_stop()
        self.save_state()

    def on_record(self):
        self.sequencer_is_empty[self.selected_sequencer] = False
        if self.selected_sequencer.recording:
            self.selected_sequencer.stop_recording()
        else:
            for s in self.sequencers:
                if s.recording:
                    s.stop_recording()
                if s != self.selected_sequencer and s.output_channel == self.selected_sequencer.output_channel:
                    if self.controls.shift_button.pressed:
                        s.stop()
                    else:
                        s.schedule_stop()

            self.selected_sequencer.schedule_record()
        self.save_state()

    def on_clear(self):
        self.selected_sequencer.reset()
        self.sequencer_is_empty[self.selected_sequencer] = True
        self.save_state()

    def on_scope(self):
        if self.current_scope == 'sequencer':
            if len(self.selected_sequencer.events):
                self.current_scope = 'note'
                self.selected_event = None
        else:
            self.current_scope = 'sequencer'
            self.selected_event = None

    def save_state(self):
        if not self.enable_state_saving:
            return
        with self.state_file_lock:
            state = dict(
                sequencers=[None if self.sequencer_is_empty[s] else s.save_state() for s in self.sequencers],
                metronome=self.metronome_param.get(),
                tempo=self.tempo_param.get(),
            )
            tmp_path = self.saved_state_path + '.tmp'
            with open(tmp_path, 'w') as f:
                json.dump(state, f)
            os.rename(tmp_path, self.saved_state_path)

    def load_state(self):
        with self.state_file_lock:
            if not os.path.exists(self.saved_state_path):
                return

            with open(self.saved_state_path) as f:
                try:
                    state = json.load(f)
                except Exception as e:
                    logging.error('State load failed: %s', e)
                    return

            for index, s_state in enumerate(state['sequencers']):
                self.sequencer_is_empty[self.sequencers[index]] = not s_state
                if s_state:
                    self.sequencers[index].load_state(s_state)

            self.metronome_param.set(state['metronome'])
            self.tempo_param.set(state['tempo'])
