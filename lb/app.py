import math
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


class App:
    def __init__(self):
        self.input_manager = InputManager(self)
        self.input_manager.start()
        self.output_manager = OutputManager()
        self.output_manager.start()
        self.tempo = Tempo()
        self.tempo.start()
        self.controls = Controls(self)
        self.controls.start()
        self.selected_sequencer = None

        self.sequencers = []
        for i in range(6):
            self.add_sequencer()
        self.select_sequencer(self.sequencers[0])

        self.input_manager.message.subscribe(lambda x: self.process_message(x[0], x[1]))

        if True:
            for i in range(16):
                import mido
                from lb.sequencer import SequencerEvent
                self.sequencers[0].events.append(
                    SequencerEvent(message=mido.Message('note_on', note=64+i), time=i/3.7),
                )
                self.sequencers[0].events.append(
                    SequencerEvent(message=mido.Message('note_off', note=64+i), time=i/3.7+.35),
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
                MetronomeParam(self),
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
        self.controls.s_1_button.press.subscribe(lambda _: self.select_sequencer(self.sequencers[0]))
        self.controls.s_2_button.press.subscribe(lambda _: self.select_sequencer(self.sequencers[1]))
        self.controls.ok_button.press.subscribe(lambda _: self.on_ok())

        self.display = Display(self)
        self.display.run()

    def add_sequencer(self):
        s = Sequencer(self)
        self.sequencers.append(s)
        s.output.subscribe(lambda msg: self.output_manager.send_to_all(msg))

    def select_sequencer(self, s):
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

    def on_ok(self):
        self.current_param[self.current_scope].ok()

    def on_play(self):
        if self.selected_sequencer.running:
            if self.selected_sequencer.recording:
                self.selected_sequencer.stop_recording()
                return
        self.selected_sequencer.schedule_start()
        for s in self.sequencers:
            if s != self.selected_sequencer:
                s.schedule_stop()

    def on_stop(self):
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
