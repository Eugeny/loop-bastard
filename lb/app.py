import pygame
import time
import sys
from .input_manager import InputManager
from .output_manager import OutputManager
from .sequencer import Sequencer
from .tempo import Tempo
from .display import Display


class App:
    def __init__(self):
        self.input_manager = InputManager()
        self.input_manager.start()
        self.output_manager = OutputManager()
        self.output_manager.start()
        self.tempo = Tempo()
        self.tempo.start()

        self.sequencer = Sequencer(self)

        self.input_manager.message.subscribe(lambda x: self.process_message(x[0], x[1]))
        self.sequencer.output.subscribe(lambda msg: self.output_manager.send_to_all(msg))

        self.display = Display(self)
        self.display.run()

    def process_message(self, port, msg):
        self.sequencer.process_message(msg)
        # if msg.type not in ['note_on', 'note_off']:
        #     self.output_manager.send_to_all(msg)
