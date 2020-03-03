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

        self.display = Display(self)
        self.display.start()

        self.sequencer = Sequencer(self)

        self.input_manager.message.subscribe(lambda msg: self.sequencer.add(msg))
        self.sequencer.output.subscribe(lambda msg: self.output_manager.send_to_all(msg))

        self.sequencer.start()

        try:
            while True:
                time.sleep(0.1)
                for event in pygame.event.get():
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_r:
                            self.sequencer.reset()
                        if event.key == pygame.K_q:
                            self.sequencer.start()
                        if event.key == pygame.K_w:
                            self.sequencer.stop()
                        if event.key == pygame.K_e:
                            self.sequencer.record()
                    if event.type == pygame.QUIT:
                        sys.exit()

        except KeyboardInterrupt:
            sys.exit(0)
