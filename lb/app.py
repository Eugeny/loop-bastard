import math
from collections import defaultdict
from .controls import Controls
from .input_manager import InputManager
from .output_manager import OutputManager
from .sequencer import Sequencer
from .tempo import Tempo
from .display import Display


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
        if not self.app.selected_sequencer.quantizer_filter.enabled:
            return None
        return self.app.selected_sequencer.quantizer_filter.divisor

    def set(self, v):
        self.app.selected_sequencer.quantizer_filter.enabled = v is not None
        self.app.selected_sequencer.quantizer_filter.divisor = v or 32
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

        self.selected_sequencer = None
        self.selected_sequencer_bank = 0
        self.sequencer_is_empty = defaultdict(True)

        self.sequencer_bank_size = len(self.controls.number_buttons)
        self.sequencer_banks = len(self.controls.number_buttons)

        self.sequencers = []
        for i in range(self.sequencer_banks * self.sequencer_bank_size):
            self.add_sequencer()

        self.select_sequencer(self.sequencers[0])

        self.input_manager.message.subscribe(lambda x: self.process_message(x[0], x[1]))

        if True:
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
        self.scope_params = {
            'global': [
                MetronomeParam(self),
            ],
            'sequencer': [
                QuantizerParam(self),
                GateLengthParam(self),
                OffsetParam(self),
                LengthParam(self),
                TempoParam(self),
                MetronomeParam(self),
                InputChannelParam(self),
                OutputChannelParam(self),
            ],
            'note': [],
        }
        self.current_param = {
            'sequencer': self.scope_params['sequencer'][0],
        }

        self.controls.rotary_param.left.subscribe(lambda _: self.param_next())
        self.controls.rotary_param.right.subscribe(lambda _: self.param_prev())
        self.controls.rotary_value.left.subscribe(lambda _: self.value_dec())
        self.controls.rotary_value.right.subscribe(lambda _: self.value_inc())
        self.controls.play_button.press.subscribe(lambda _: self.on_play())
        self.controls.stop_button.press.subscribe(lambda _: self.on_stop())
        self.controls.record_button.press.subscribe(lambda _: self.on_record())
        self.controls.clear_button.press.subscribe(lambda _: self.on_clear())
        self.controls.ok_button.press.subscribe(lambda _: self.on_ok())

        for i in range(len(self.controls.number_buttons)):
            self.controls.number_buttons[i].press.subscribe((lambda i: lambda _: self.on_number(i))(i))

        self.display = Display(self)
        self.display.run()

    def add_sequencer(self):
        s = Sequencer(self)
        self.sequencers.append(s)
        s.output.subscribe(lambda msg: self.output_manager.send_to_all(msg))

    def select_sequencer(self, s):
        if self.sequencer_is_empty[s]:
            pass
        self.sequencer_is_empty[s] = False

        if self.selected_sequencer:
            self.selected_sequencer.thru = False
        self.selected_sequencer = s
        self.selected_sequencer.thru = True

    def process_message(self, port, msg):
        for s in self.sequencers:
            s.process_message(msg)

    def param_prev(self):
        i = self.scope_params[self.current_scope].index(self.current_param[self.current_scope])
        i = max(0, i - 1)
        self.current_param[self.current_scope] = self.scope_params[self.current_scope][i]

    def param_next(self):
        i = self.scope_params[self.current_scope].index(self.current_param[self.current_scope])
        i = min(len(self.scope_params[self.current_scope]) - 1, i + 1)
        self.current_param[self.current_scope] = self.scope_params[self.current_scope][i]

    def value_dec(self):
        i = self.current_param[self.current_scope].options.index(self.current_param[self.current_scope].get())
        i = max(0, i - 1)
        self.current_param[self.current_scope].set(self.current_param[self.current_scope].options[i])

    def value_inc(self):
        i = self.current_param[self.current_scope].options.index(self.current_param[self.current_scope].get())
        i = min(len(self.current_param[self.current_scope].options) - 1, i + 1)
        self.current_param[self.current_scope].set(self.current_param[self.current_scope].options[i])

    def on_number(self, i):
        if self.controls.shift_button.pressed:
            self.selected_sequencer_bank = i
        else:
            self.select_sequencer(self.sequencers[self.selected_sequencer_bank * self.sequencer_bank_size +i])

    def on_ok(self):
        self.current_param[self.current_scope].ok()

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

    def on_stop(self):
        if self.controls.shift_button.pressed:
            self.selected_sequencer.stop()
        else:
            self.selected_sequencer.schedule_stop()

    def on_record(self):
        if self.selected_sequencer.recording:
            self.selected_sequencer.stop_recording()
        else:
            self.selected_sequencer.schedule_record()
            for s in self.sequencers:
                if s != self.selected_sequencer:
                    s.schedule_stop()

    def on_clear(self):
        self.selected_sequencer.reset()
        self.sequencer_is_empty[self.selected_sequencer] = True
