import os
import pygame
import pygame.font
import time
import threading

os.environ['SDL_VIDEO_CENTERED'] = '1'

NOTES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
OCTAVES = list(range(11))
NOTES_IN_OCTAVE = len(NOTES)


def number_to_note(number: int):
    octave = number // NOTES_IN_OCTAVE
    note = NOTES[number % NOTES_IN_OCTAVE]
    return note, octave


class Display(threading.Thread):
    def __init__(self, app):
        super().__init__(daemon=True)
        self.app = app
        pygame.init()
        self.screen = pygame.display.set_mode((800, 400))
        self.font = pygame.font.Font('bryant.ttf', 8)

    def run(self):
        while True:
            time.sleep(1 / 60)

            self.screen.fill((0, 0, 20))
            seq_w = 600
            seq_h = 200
            seq_surf = self.screen.subsurface((100, 200, seq_w, seq_h))

            def time_to_x(t):
                return seq_w * t / self.app.sequencer.get_length()

            for i in range(1, self.app.sequencer.bars + 1):
                color = (10, 10, 10) if (i % 2) else (20, 20, 20)
                seq_surf.fill(color, rect=(
                    time_to_x(self.app.tempo.q_to_time((1, i, 1))),
                    0,
                    time_to_x(self.app.tempo.q_to_time((1, 2, 1))),
                    seq_h,
                ))

            for i in range(1, self.app.sequencer.bars * self.app.tempo.bar_size + 1):
                seq_surf.fill((30, 30, 30), rect=(
                    time_to_x(self.app.tempo.q_to_time((1, 1, i))),
                    0,
                    1,
                    seq_h,
                ))

            with self.app.sequencer.lock:
                dif_notes = sorted(set(x.message.note for x in self.app.sequencer.events))
                if len(self.app.sequencer.events):
                    note_h = seq_h / max(10, len(dif_notes))
                    notes_y = {note: seq_h - (idx + 1) * seq_h / len(dif_notes) for idx, note in enumerate(dif_notes)}

                    def draw_note(note, x, w):
                        c = note.velocity / 128
                        color = (50 + c * 180, 50, 220 - c * 180)
                        text_color = (
                            max(int(color[0] * 1.2), 255),
                            max(int(color[1] * 1.2), 255),
                            max(int(color[2] * 1.2), 255),
                        )
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
                            if note_rect[2] > text_rect[2] + 5 and note_rect[3] > text_rect[3]:
                                seq_surf.blit(
                                    self.font.render(
                                        text,
                                        True,
                                        text_color,
                                    ),
                                    (x + 5, notes_y[note.note] + 5, w, note_h),
                                )

                    m = {}
                    notes = []
                    remaining_events = self.app.sequencer.events[:]
                    for event in remaining_events[:]:
                        if event.message.type == 'note_on':
                            m[event.message.note] = event
                            remaining_events.remove(event)
                        if event.message.type == 'note_off':
                            if event.message.note in m:
                                notes.append((m[event.message.note], event.time - m[event.message.note].time))
                                remaining_events.remove(event)
                                del m[event.message.note]
                    for event in remaining_events:
                        if event.message.type == 'note_off':
                            if event.message.note in m:
                                notes.append((m[event.message.note], event.time + self.app.sequencer.get_length() - m[event.message.note].time))
                                del m[event.message.note]

                    for event in self.app.sequencer.events:
                        if event.message.type == 'note_on' and self.app.sequencer.is_note_open(event):
                            length = self.app.sequencer.get_time() - event.time
                            length = self.app.sequencer.normalize_time(length)
                            notes.append((event, length))

                    for (event, length) in notes:
                        draw_note(
                            event.message,
                            time_to_x(event.time),
                            time_to_x(length),
                        )
                        if event.time + length > self.app.sequencer.get_length():
                            draw_note(
                                event.message,
                                time_to_x(event.time - self.app.sequencer.get_length()),
                                time_to_x(length),
                            )

            # Time indicator
            seq_surf.fill(
                (255, 255, 255),
                (time_to_x(self.app.sequencer.get_time()), 0, 1, seq_h)
            )

            pygame.display.flip()
