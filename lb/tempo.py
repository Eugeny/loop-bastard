import pygame
import time
import threading


class Tempo(threading.Thread):
    bar_size = 4
    bars = 4
    bpm = 120
    start_time = 0
    enable_metronome = True

    def __init__(self):
        super().__init__(daemon=True)
        self.start_time = time.time()
        self.metronome_sound = pygame.mixer.Sound('metronome.wav')
        self.metronome_b_sound = pygame.mixer.Sound('metronome_b.wav')

    def get_time(self):
        return time.time() - self.start_time

    def time_to_pos(self, t):
        return t * self.bpm / 60

    def pos_to_time(self, p):
        return p / self.bpm * 60

    def get_pos(self):
        return self.time_to_pos(time.time() - self.start_time)

    def pos_to_q(self, p):
        p = int(p)
        parts = p // (self.bars * self.bar_size)
        p %= self.bars * self.bar_size
        bars = p // self.bar_size
        beat = p % self.bar_size
        return (parts + 1, bars + 1, beat + 1)

    def get_q(self):
        return self.pos_to_q(self.get_pos())

    def q_to_time(self, q):
        beat_len = self.get_beat_length()
        return (q[0] - 1) * self.bar_size * self.bars * beat_len + (q[1] - 1) * \
            self.bar_size * beat_len + (q[2] - 1) * beat_len

    def get_beat_length(self):
        return 60 / self.bpm

    def run(self):
        while True:
            next_tick = self.pos_to_time(round(self.get_pos()) + 1)
            time.sleep(next_tick - self.get_time())
            q = self.pos_to_q(round(self.get_pos()))
            if self.enable_metronome:
                if q[2] == 1:
                    self.metronome_b_sound.play()
                else:
                    self.metronome_sound.play()
            time.sleep(self.metronome_sound.get_length())
            # print(time.time())
