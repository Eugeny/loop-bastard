from .controls import Controls
from .input_manager import InputManager
from .output_manager import OutputManager
from .sequencer import Sequencer
from .tempo import Tempo
from .display import Display


class QuantizerParam:
    name = 'Q size'
    type = 'pow2'

    def __init__(self, app):
        self.app = app
        self.options = [1, 2, 4, 8, 16, 32]

    def get(self):
        return self.app.selected_sequencer.quantizer_div

    def set(self, v):
        self.app.selected_sequencer.quantizer_div = v

    def __str__(self):
        return f'1/{self.get()}'


class LengthParam:
    name = 'Length'
    type = 'int'

    def __init__(self, app):
        self.app = app
        self.options = list(range(1, 17))

    def get(self):
        return self.app.selected_sequencer.bars

    def set(self, v):
        self.app.selected_sequencer.bars = v

    def __str__(self):
        return f'{self.get()} bars'


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
        for i in range(4):
            self.add_sequencer()
        self.select_sequencer(self.sequencers[0])

        self.input_manager.message.subscribe(lambda x: self.process_message(x[0], x[1]))

        for i in range(16):
            import mido
            from lb.sequencer import SequencerEvent
            self.sequencers[0].events.append(
                SequencerEvent(message=mido.Message('note_on', note=64+i), time=i/3.7),
            )
            self.sequencers[0].events.append(
                SequencerEvent(message=mido.Message('note_off', note=64+i), time=i/3.7+.35),
            )
        self.sequencers[0].cleanup()

        self.current_scope = 'sequencer'
        self.scope_params = {
            'global': [],
            'sequencer': [
                QuantizerParam(self),
                LengthParam(self),
            ],
            'note': [],
        }
        self.current_param = {
            'sequencer': self.app.scope_params['sequencer'][0],
        }


        self.controls.rotary_value.left.subscribe(lambda _: self.value_dec())
        self.controls.rotary_value.right.subscribe(lambda _: self.value_inc())

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
