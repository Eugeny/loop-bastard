import math
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

    def get_blink(self, type):
        if type == 'beat':
            a = self.app.tempo.get_time() % self.app.tempo.get_beat_length() / self.app.tempo.get_beat_length()
            return int(255 - a * 255)
        if type == 'fast':
            return 255 * int((time.time() % 0.125 * 8) * 1.9)

    def _draw_list(self, surface, items=None, index=None, bg=None, fg=None):
        w, h = surface.get_size()

        item_count = 3
        selected_position = 1
        display_items = [None] * item_count
        for i in range(item_count):
            src_index = i + index - selected_position
            if src_index >= 0 and src_index < len(items):
                display_items[i] = items[src_index]

        item_h = h // item_count
        for i in range(item_count):
            if display_items[i]:
                text_w = self.font.size(display_items[i])[0]
                if i == selected_position:
                    rect = (5, i * item_h, w - 20, item_h)
                    surface.fill(fg, rect)
                else:
                    rect = (10, i * item_h, w - 20, item_h)
                    surface.fill((fg[0] / 2, fg[1] / 2, fg[2] / 2), rect)

                surface.blit(self.font.render(
                    display_items[i],
                    True,
                    bg if i == selected_position else fg,
                ), (rect[0] + rect[2] // 2 - text_w // 2, rect[1]))

    def draw_param_selector(self, surface):
        w, h = surface.get_size()
        bg = (32, 64, 128)
        fg = (64, 128, 255)

        param = self.app.current_param[self.app.current_scope]
        params = self.app.scope_params[self.app.current_scope]

        # pygame.draw.rect(
        #     surface,
        #     bg,
        #     (0, 0, w, h),
        # )
        # pygame.draw.rect(
        #     surface,
        #     fg,
        #     (0, 0, w, h),
        #     5,
        # )

        self._draw_list(
            surface.subsurface((0, 0, w, h)),
            items=[x.name for x in params],
            index=params.index(param),
            bg=(0, 0, 0), fg=fg,
        )

        # text_w = self.font.size(param.name)[0]
        # surface.blit(self.font.render(
        #     param.name,
        #     True,
        #     (255, 255, 255)
        # ), (w // 4 - text_w // 2, h - 40))

    def draw_param_value(self, surface):
        w, h = surface.get_size()

        param = self.app.current_param[self.app.current_scope]
        fg = (255, 128, 64)

        if not param.is_on():
            fg = (128, 128, 128)

        # pygame.draw.rect(
        #     surface,
        #     bg,
        #     (0, 0, w, h),
        # )
        # pygame.draw.rect(
        #     surface,
        #     fg,
        #     (0, 0, w, h),
        #     5,
        # )

        if param.type == 'list':
            self._draw_list(
                surface.subsurface((5, 5, w - 10, h - 10)),
                items=[param.to_str(x) for x in param.options],
                index=param.options.index(param.get()),
                bg=(0, 0, 0), fg=fg,
            )

        if param.type == 'dial':
            text_w = self.font.size(param.to_str(param.get()))[0]
            surface.blit(self.font.render(
                param.to_str(param.get()),
                True,
                (255, 255, 255)
            ), (w // 2 - text_w // 2, h - 40))

            def index_to_angle(i):
                return -1.5 + 3 * i / (len(param.options) - 1)

            for i in range(0, len(param.options)):
                pygame.draw.line(
                    surface,
                    (255, 128, 64),
                    (w / 2 + 30 * math.sin(index_to_angle(i)), h / 2 - 30 * math.cos(index_to_angle(i))),
                    (w / 2 + 40 * math.sin(index_to_angle(i)), h / 2 - 40 * math.cos(index_to_angle(i))),
                    3,
                )
            option_index = param.options.index(param.get())
            pygame.draw.line(
                surface,
                (255, 255, 255),
                (w / 2 + 20 * math.sin(index_to_angle(option_index)), h / 2 - 20 * math.cos(index_to_angle(option_index))),
                (w / 2 + 40 * math.sin(index_to_angle(option_index)), h / 2 - 40 * math.cos(index_to_angle(option_index))),
                5,
            )

    def draw_status_bar(self, surface):
        surface.fill((128, 128, 128), rect=(5, surface.get_height() - 2, surface.get_width() - 10, 2))

        p = 0

        c = (255, 255, 255) if self.had_midi_in_activity else (128, 128, 128)
        if not self.app.input_manager.has_input():
            c = (255, 0, 0)
        surface.blit(self.font.render('IN', True, c), (p + 5, 5))
        p += 50

        # BPM
        surface.blit(
            self.font.render(
                str(self.app.tempo.bpm) + ' BPM',
                True,
                (128, 128, 128),
            ),
            (p + 5, 5),
        )
        p += 110

        # Beat display
        p += 5
        for i in range(self.app.tempo.bar_size):
            w = 0 if i == self.app.tempo.get_q()[2] - 1 else 2
            pygame.draw.rect(
                surface,
                (128, 128, 255),
                (p + 2, 10, 16, 16),
                w
            )
            p += 25
        p += 5

        c = (255, 255, 255) if self.had_midi_out_activity else (128, 128, 128)
        if not self.app.output_manager.has_output():
            c = (255, 0, 0)
        surface.blit(self.font.render('OUT', True, c), (surface.get_width() - 55, 5))

    def draw_bottom_bar(self, surface):
        surface.fill((128, 128, 128), rect=(5, 0, surface.get_width() - 10, 2))

        p = 0
        for v, name in [('global', 'GLOB'), ('sequencer', 'SEQ'), ('note', 'NOTE')]:
            w = self.font.size(name)[0]
            if self.app.current_scope == v:
                surface.fill((255, 255, 255), rect=(p, 0, w + 10, surface.get_height()))
                surface.blit(self.font.render(name, True, (0, 0, 0)), (p + 5, 5))
            else:
                surface.blit(self.font.render(name, True, (255, 255, 255)), (p + 5, 5))
            p += w + 10

    def draw_sequencer_icon(self, surface, sequencer):
        w, h = surface.get_size()

        if sequencer == self.app.selected_sequencer:
            pygame.draw.rect(
                surface,
                (32, 64, 128),
                (0, 0, w, h),
            )

        pygame.draw.rect(
            surface,
            (64, 128, 255) if sequencer == self.app.selected_sequencer else (64, 64, 64),
            (0, 0, w, h),
            5,
        )

        text = str(self.app.sequencers.index(sequencer) + 1)
        text_w = self.font_lg.size(text)[0]
        surface.blit(self.font_lg.render(
            text,
            True,
            (255, 255, 255)
        ), (w // 2 - text_w // 2, 10))

        self.img_play_sm.set_alpha(64)
        surface.blit(self.img_play_sm, (w // 2 - 16, h - 44))
        if sequencer.running:
            self.img_play_sm_active.set_alpha(self.get_blink('beat'))
            surface.blit(self.img_play_sm_active, (w // 2 - 16, h - 44))
        if sequencer.start_scheduled:
            self.img_play_sm_active.set_alpha(self.get_blink('fast'))
            surface.blit(self.img_play_sm_active, (w // 2 - 16, h - 44))

    def draw_sequencer(self, surface, sequencer):
        w, h = surface.get_size()

        toolbar_size = 64
        self.draw_sequencer_body(
            surface.subsurface((toolbar_size, 0, w - toolbar_size, h)),
            sequencer
        )
        self.img_play.set_alpha(64)
        surface.blit(self.img_play, (0, 0))
        if not sequencer.recording:
            if sequencer.start_scheduled:
                self.img_play_active.set_alpha(self.get_blink('fast'))
                surface.blit(self.img_play_active, (0, 0))
            elif sequencer.running:
                self.img_play_active.set_alpha(self.get_blink('beat'))
                surface.blit(self.img_play_active, (0, 0))

        self.img_record.set_alpha(64)
        surface.blit(self.img_record, (0, 64))
        if sequencer.recording:
            a = self.get_blink('beat')
            if sequencer.start_scheduled:
                a = self.get_blink('fast')

            self.img_record_active.set_alpha(a)
            surface.blit(self.img_record_active, (0, 64))

            a = self.get_blink('beat')
            pygame.draw.rect(
                surface, (a, 0, 0), (0, 0, w, h), 4
            )

    def draw_sequencer_body(self, surface, sequencer):
        def time_to_x(t):
            return surface.get_width() * t / sequencer.get_length()

        for i in range(1, sequencer.bars + 1):
            color = (10, 10, 10) if (i % 2) else (20, 20, 20)
            color = (0, 0, 0)
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

        q_time = self.app.tempo.get_beat_length() * 4 / sequencer.quantizer_filter.divisor
        q_color = (255, 128, 0) if sequencer.quantizer_filter.enabled else (128, 128, 128)
        for i in range(0, int(sequencer.get_length() / q_time)):
            surface.fill(q_color, (time_to_x(q_time * i), 0, 2, 5))

        with sequencer.lock:
            dif_notes = sorted(set(x.message.note for x in sequencer.filtered_events))
            if len(sequencer.filtered_events):
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
                        text_w, text_h = self.font_xs.size(text)
                        if note_rect[2] > text_w + 5 and note_rect[3] > text_h + 5:
                            surface.blit(
                                self.font_xs.render(
                                    text,
                                    True,
                                    text_color,
                                ),
                                (x + 5, notes_y[note.note] + 5, w, note_h),
                            )

                m = {}
                notes = []
                remaining_events = sequencer.filtered_events[:]
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

                for event in sequencer.filtered_events:
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
        self.font_xs = pygame.font.Font('bryant.ttf', 10)
        self.font = pygame.font.Font('bryant.ttf', 24)
        self.font_lg = pygame.font.Font('bryant.ttf', 36)
        self.img_play = pygame.image.load('images/play.png')
        self.img_play_active = self.img_play.copy()
        self.img_play_active.fill((0, 255, 64), special_flags=pygame.BLEND_MULT)
        self.img_record = pygame.image.load('images/record.png')
        self.img_record_active = self.img_record.copy()
        self.img_record_active.fill((255, 0, 64), special_flags=pygame.BLEND_MULT)
        self.img_play_sm = pygame.image.load('images/play-sm.png')
        self.img_play_sm_active = self.img_play_sm.copy()
        self.img_play_sm_active.fill((0, 255, 64), special_flags=pygame.BLEND_MULT)

        while True:
            self.screen.fill((0, 0, 20))

            self.draw_status_bar(
                self.screen.subsurface((0, 0, self.screen.get_width(), 40)),
            )

            self.draw_bottom_bar(
                self.screen.subsurface((0, self.screen.get_height() - 40, self.screen.get_width(), 40)),
            )

            self.draw_sequencer(
                self.screen.subsurface((0, 160, 800, 200)),
                self.app.selected_sequencer,
            )

            for s_index, s in enumerate(self.app.sequencers):
                self.draw_sequencer_icon(
                    self.screen.subsurface((10 + 60 * s_index, 50, 50, 100)),
                    s
                )

            self.draw_param_selector(
                self.screen.subsurface((self.screen.get_width() - 10 - 290, 50, 170, 100))
            )

            self.draw_param_value(
                self.screen.subsurface((self.screen.get_width() - 10 - 120, 50, 120, 100))
            )

            pygame.display.flip()
            self.had_play_activity = False
            self.had_midi_out_activity = False

            try:
                time.sleep(1 / 60)
                for event in pygame.event.get():
                    self.app.controls.process_event(event)
                    if event.type == pygame.QUIT:
                        sys.exit()

            except KeyboardInterrupt:
                sys.exit(0)
