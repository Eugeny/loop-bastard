#!/usr/bin/env python
import mido
import pygame
import pygame.freetype
import sys
import time
import threading
from dataclasses import dataclass
from mido.ports import multi_receive


NOTES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
OCTAVES = list(range(11))
NOTES_IN_OCTAVE = len(NOTES)


pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=256)

def number_to_note(number: int):
    octave = number // NOTES_IN_OCTAVE
    note = NOTES[number % NOTES_IN_OCTAVE]
    return note, octave


class Tempo(threading.Thread):
    bar_size = 4
    bars = 4
    bpm = 120
    start_time = 0

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
            print(self.get_pos(), self.get_q(), q)
            if q[2] == 1:
                self.metronome_b_sound.play()
            else:
                self.metronome_sound.play()
            time.sleep(self.metronome_sound.get_length())
            print(time.time())


tempo = Tempo()
tempo.start()


@dataclass
class SequencerNote:
    time: int
    note: int
    velocity: int
    length: float = None


class Sequencer(threading.Thread):
    bars = 4
    notes = []
    running = False
    start_time = 0

    def __init__(self):
        super().__init__(daemon=True)
        self.lock = threading.RLock()
        self.reset()
        self.start()

    def get_time(self):
        return (tempo.get_time() - self.start_time) % self.get_length()

    def get_length(self):
        return tempo.q_to_time((1, self.bars + 1, 1))

    def get_q(self):
        return tempo.pos_to_q(tempo.time_to_pos(self.get_time()))

    def reset(self):
        with self.lock:
            self.notes = []

    def start(self):
        self.start_time = tempo.get_time()
        self.running = True

    def add_note_on(self, msg):
        with self.lock:
            n = SequencerNote(
                time=self.get_time(),
                note=msg.note,
                velocity=msg.velocity,
                length=None
            )
            self.notes.append(n)

    def add_note_off(self, msg):
        with self.lock:
            new = None
            for n in self.notes:
                if n.note == msg.note and not n.length:
                    new = n
                    n.length = self.get_time() - n.time
                    while n.length < 0:
                        n.length += self.get_length()

            for old in self.notes[:]:
                if old.note == msg.note and old.length:
                    if old.time < new.time and old.time + old.length > new.time:
                        self.notes.remove(old)
                    elif old.time > new.time and old.time < new.time + new.length:
                        self.notes.remove(old)

    def cleanup(self):
        with self.lock:
            self.notes = sorted(self.notes, key=lambda x: x.time)
            dif_notes = sorted(set(x.note for x in sequencer.notes))
            for pitch in dif_notes:
                last = None
                for n in self.notes[:]:
                    if n.note == pitch and n.length:
                        if last and last.time + last.length > n.time and last.time + last.length < n.time + n.length:
                            self.notes.remove(n)
                        elif last and last.time > n.time and last.time < n.time + n.length:
                            self.notes.remove(n)
                        elif last and last.time < n.time and last.time + last.length > n.time + n.length:
                            self.notes.remove(n)
                        else:
                            last = n

    def get_notes_at(self, time):
        time %= self.get_length()
        for n in self.notes:
            if n.time <= time and ((n.time + n.length) if n.length else self.get_time()) >= time:
                yield n

    def run(self):
        pass


sequencer = Sequencer()


class Display(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        pygame.init()
        self.screen = pygame.display.set_mode((800, 400))
        self.font = pygame.freetype.SysFont('Arial', 12)

    def run(self):
        while True:
            time.sleep(1/60)

            self.screen.fill((0, 0, 20))
            seq_w = 800
            seq_h = 300
            seq_surf = self.screen.subsurface((0, 0, seq_w, seq_h))

            def time_to_x(t):
                return seq_w * t / sequencer.get_length()

            for i in range(1, sequencer.bars + 1):
                color = (10, 10, 10) if (i % 2) else (20, 20, 20)
                seq_surf.fill(color, rect=(
                    time_to_x(tempo.q_to_time((1, i, 1))),
                    0,
                    time_to_x(tempo.q_to_time((1, 2, 1))),
                    seq_h,
                ))

            for i in range(1, sequencer.bars * tempo.bar_size + 1):
                seq_surf.fill((30, 30, 30), rect=(
                    time_to_x(tempo.q_to_time((1, 1, i))),
                    0,
                    1,
                    seq_h,
                ))

            with sequencer.lock:
                dif_notes = sorted(set(x.note for x in sequencer.notes))
                if len(dif_notes):
                    note_h = seq_h / max(10, len(dif_notes))
                    notes_y = {note: seq_h - (idx + 1) * seq_h / len(dif_notes) for idx, note in enumerate(dif_notes)}

                    def draw_note(note, x, w):
                        c = note.velocity / 128
                        color = (50 + c * 180, 50, 220 -c * 180)
                        note_rect = (x, notes_y[note.note], w, note_h)
                        pygame.draw.rect(
                            seq_surf,
                            color,
                            note_rect,
                        )
                        pygame.draw.rect(
                            seq_surf,
                            (color[0] / 3, color[1] / 3, color[2] / 3),
                            pygame.Rect(note_rect).inflate(-2, -2),
                        )
                        name, o = number_to_note(note.note)
                        text = f'{name} {o}'
                        size = min(20, note_h * 0.7)
                        if x >= 0:
                            text_rect = self.font.get_rect(text, size=size)
                            if note_rect[2] > text_rect[2] + 10 and note_rect[3] > text_rect[3] + 10:
                                self.font.render_to(
                                    seq_surf,
                                    (x + 5, notes_y[note.note] + 5, w, note_h),
                                    text,
                                    color,
                                    size=size,
                                )

                    for n in sequencer.notes:
                        w = n.length or (sequencer.get_time() - n.time)
                        if w < 0:
                            w += sequencer.get_length()

                        draw_note(n, time_to_x(n.time), time_to_x(w))
                        if n.time + w > sequencer.get_length():
                            draw_note(n, time_to_x(n.time - sequencer.get_length()), time_to_x(w))

            # Time indicator
            seq_surf.fill(
                (255, 255, 255),
                (time_to_x(sequencer.get_time()), 0, 1, seq_h)
            )

            pygame.display.flip()


class MidiReceiver(threading.Thread):
    def __init__(self, ports):
        super().__init__(daemon=True)
        self.stop_flag = False
        self.ports = [mido.open_input(name) for name in ports]

    def run(self):
        for message in multi_receive(self.ports):
            self.process(message)
            print('Received {}'.format(message))
            if self.stop_flag:
                break

    def process(self, msg: mido.Message):
        if msg.type == 'note_on':
            sequencer.add_note_on(msg)
        if msg.type == 'note_off':
            sequencer.add_note_off(msg)

    def stop(self):
        self.stop_flag = True


class InputManager(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.known_ports = []
        self.receiver_thread = None

    def run(self):
        while True:
            ports = mido.get_input_names()
            if ports != self.known_ports:
                if self.receiver_thread:
                    self.receiver_thread.stop()

                for port in ports:
                    if port not in self.known_ports:
                        print('Connected', port)
                for port in self.known_ports:
                    if port not in ports:
                        print('Disconnected', port)

                self.known_ports = ports

                self.receiver_thread = MidiReceiver(ports)
                self.receiver_thread.start()
            time.sleep(0.1)


im = InputManager()
im.start()

Display().start()
Sequencer().start()

try:
    while True:
        time.sleep(0.1)
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    sequencer.reset()
            if event.type == pygame.QUIT:
                sys.exit()

except KeyboardInterrupt:
    sys.exit(0)
