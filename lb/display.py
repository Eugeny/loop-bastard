import os
import pygame
import pygame.font
import time
import threading
import sys

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

        self.had_midi_in_activity = False
        self.had_midi_out_activity = False

        self.app.input_manager.message.subscribe(lambda _: self._on_midi_in())
        self.app.output_manager.message.subscribe(lambda _: self._on_midi_out())

    def _on_midi_in(self):
        self.had_midi_in_activity = True

    def _on_midi_out(self):
        self.had_midi_out_activity = True

    def draw_status_bar(self, surface):
        surface.fill((20, 20, 20))

        if self.app.input_manager.has_input():
            self.img_midi_in.set_alpha(255 if self.had_midi_in_activity else 128)
            surface.blit(self.img_midi_in, (2, 2))
        else:
            surface.blit(self.img_midi_in_disconnected, (2, 2))

        if self.app.output_manager.has_output():
            self.img_midi_out.set_alpha(255 if self.had_midi_out_activity else 128)
            surface.blit(self.img_midi_out, (surface.get_width() - 34, 2))
        else:
            surface.blit(self.img_midi_out_disconnected, (surface.get_width() - 34, 2))

    def draw_sequencer(self, surface, sequencer):
        def time_to_x(t):
            return surface.get_width() * t / sequencer.get_length()

        for i in range(1, sequencer.bars + 1):
            color = (10, 10, 10) if (i % 2) else (20, 20, 20)
            color = (0,0,0)
            surface.fill(color, rect=(
                time_to_x(self.app.tempo.q_to_time((1, i, 1))),
                0,
                time_to_x(self.app.tempo.q_to_time((1, 2, 1))),
                surface.get_height(),
            ))

        for i in range(1, sequencer.bars * self.app.tempo.bar_size + 1):
            color = (50, 50, 100) if (i % 4 == 1) else (30, 30, 30)
            surface.fill(color, rect=(
                time_to_x(self.app.tempo.q_to_time((1, 1, i))),
                0,
                1,
                surface.get_height(),
            ))

        with sequencer.lock:
            dif_notes = sorted(set(x.message.note for x in sequencer.events))
            if len(sequencer.events):
                note_h = surface.get_height() / max(10, len(dif_notes))
                notes_y = {note: surface.get_height() - (idx + 1) * surface.get_height() / len(dif_notes) for idx, note in enumerate(dif_notes)}

                def draw_note(note, x, w):
                    c = note.velocity / 128
                    color = (50 + c * 180, 50, 220 - c * 180)
                    text_color = (
                        min(int(color[0] * 1.5), 255),
                        min(int(color[1] * 1.5), 255),
                        min(int(color[2] * 1.5), 255),
                    )
                    note_rect = (x, notes_y[note.note], w, note_h)
                    pygame.draw.rect(
                        surface,
                        color,
                        note_rect,
                    )
                    pygame.draw.rect(
                        surface,
                        (color[0] / 3, color[1] / 3, color[2] / 3),
                        pygame.Rect(note_rect).inflate(-2, -2),
                    )
                    name, o = number_to_note(note.note)
                    text = f'{name} {o}'
                    if x >= 0:
                        text_w, text_h = self.font.size(text)
                        if note_rect[2] > text_w + 5 and note_rect[3] > text_h + 5:
                            surface.blit(
                                self.font.render(
                                    text,
                                    True,
                                    text_color,
                                ),
                                (x + 5, notes_y[note.note] + 5, w, note_h),
                            )

                m = {}
                notes = []
                remaining_events = sequencer.events[:]
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
                            notes.append((m[event.message.note], event.time + sequencer.get_length() - m[event.message.note].time))
                            del m[event.message.note]

                for event in sequencer.events:
                    if event.message.type == 'note_on' and sequencer.is_note_open(event):
                        length = sequencer.get_time() - event.time
                        length = sequencer.normalize_time(length)
                        notes.append((event, length))

                for (event, length) in notes:
                    draw_note(
                        event.message,
                        time_to_x(event.time),
                        time_to_x(length),
                    )
                    if event.time + length > sequencer.get_length():
                        draw_note(
                            event.message,
                            time_to_x(event.time - sequencer.get_length()),
                            time_to_x(length),
                        )

        # Time indicator
        surface.fill(
            (255, 255, 255),
            (time_to_x(sequencer.get_time()), 0, 1, surface.get_height())
        )

    def run(self):
        pygame.init()
        pygame.mouse.set_visible(0)
        self.screen = pygame.display.set_mode((800, 400))
        self.font = pygame.font.Font('bryant.ttf', 10)
        self.img_midi_in = pygame.image.load('images/midi-in.png')
        self.img_midi_out = pygame.image.load('images/midi-out.png')
        self.img_midi_in_disconnected = self.img_midi_in.copy()
        self.img_midi_in_disconnected.fill((255, 0, 0), special_flags=pygame.BLEND_MULT)
        self.img_midi_out_disconnected = self.img_midi_out.copy()
        self.img_midi_out_disconnected.fill((255, 0, 0), special_flags=pygame.BLEND_MULT)

        while True:
            self.screen.fill((0, 0, 20))

            self.draw_status_bar(
                self.screen.subsurface((0, 0, self.screen.get_width(), 36)),
            )

            self.draw_sequencer(
                self.screen.subsurface((100, 200, 600, 200)),
                self.app.sequencer,
            )

            pygame.display.flip()
            self.had_midi_in_activity = False
            self.had_midi_out_activity = False

            try:
                time.sleep(1 / 60)
                for event in pygame.event.get():
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_r:
                            self.app.sequencer.reset()
                        if event.key == pygame.K_q:
                            self.app.sequencer.start()
                        if event.key == pygame.K_w:
                            self.app.sequencer.stop()
                        if event.key == pygame.K_e:
                            self.app.sequencer.record()
                        if event.key == pygame.K_m:
                            self.app.tempo.enable_metronome = not self.app.tempo.enable_metronome
                    if event.type == pygame.QUIT:
                        sys.exit()

            except KeyboardInterrupt:
                sys.exit(0)
