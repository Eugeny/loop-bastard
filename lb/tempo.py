import pygame
import time
import threading


class Tempo(threading.Thread):
    bar_size = 4
    bars = 4
    enable_metronome = False
    last_clock_time = None
    external_ticks = 0

    def __init__(self, app):
        super().__init__(daemon=True)
        self.reset()
        self.app = app
        self.metronome_sound = pygame.mixer.Sound('metronome.wav')
        self.metronome_b_sound = pygame.mixer.Sound('metronome_b.wav')
        self.app.input_manager.clock_set.subscribe(self.on_clock_set)
        self.app.input_manager.clock.subscribe(lambda _: self.on_clock())

    def get_time(self):
        return 1 / 24 / 2 * self.external_ticks

    def get_position(self):
        return self.external_ticks / 24

    def position_to_time(self, p):
        return p / self.bpm * 60

    def pos_to_q(self, p):
        p = int(p)
        parts = p // (self.bars * self.bar_size)
        p %= self.bars * self.bar_size
        bars = p // self.bar_size
        beat = p % self.bar_size
        return (parts + 1, bars + 1, beat + 1)

    def get_q(self):
        return self.pos_to_q(self.get_position())

    def get_beat_time_length(self):
        return 60 / self.bpm

    def get_bar_time_length(self):
        return 60 / self.bpm * self.bar_size

    def run(self):
        while True:
            next_tick = self.position_to_time(round(self.get_position()) + 1)
            time.sleep(next_tick - self.get_time())
            q = self.pos_to_q(round(self.get_position()))
            if self.enable_metronome:
                if q[2] == 1:
                    self.metronome_b_sound.play()
                else:
                    self.metronome_sound.play()
            time.sleep(self.metronome_sound.get_length())

    def reset(self):
        self.last_clock_time = None
        self.bpm = 120

    def on_clock(self):
        lct = self.last_clock_time
        self.last_clock_time = time.time()
        if lct:
            dt = time.time() - lct
            bpm = 1 / 24 * 60 / dt
            self.bpm = bpm
        self.external_ticks += 1

    def on_clock_set(self, ticks):
        self.external_ticks = ticks
