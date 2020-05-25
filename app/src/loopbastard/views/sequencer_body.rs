extern crate loop_bastard_ui;

use sdl2::rect::Rect;
use sdl2::pixels::Color;
use loop_bastard_ui::View;
use std::cmp::min;

use super::{View, ViewBase, ViewInner, RenderContext};
use crate::loopbastard::{Sequencer, SequencerEvent, TICKS_PER_BEAT, MessageKind};
use crate::loopbastard::util::{brighten_color, dim_color_u8, draw_rect};

#[derive(View)]
pub struct SequencerBodyView {
    index: usize,
    inner: ViewInner,
}

type NoteYCoords = [i32; 128];

impl SequencerBodyView {
    pub fn new(index: usize) -> Self {
        return Self {
            index: index,
            inner: ViewInner::new(),
        };
    }
}

#[inline]
fn position_to_x(sequencer: &Sequencer, position: u32, rect: &Rect) -> i32 {
    return rect.x() + (rect.width() * position / sequencer.length()) as i32 ;
}

impl ViewBase for SequencerBodyView {
    fn render(&mut self, context: &mut RenderContext, rect: &Rect) {
        // let border_size = 3;
        let state = context.app.state.borrow();
        let sequencer = &state.sequencers[self.index];
        let clock = context.app.clock.borrow();

        for i in 0..sequencer.length() / TICKS_PER_BEAT {
            context.canvas.set_draw_color(
                if i % 4 == 0 {Color::RGB(50, 50, 100)}
                else {Color::RGB(30, 30, 30)}
            );
            context.canvas.fill_rect(Rect::new(
                position_to_x(sequencer, i * TICKS_PER_BEAT, rect),
                rect.y(),
                1,
                self.inner.h,
            )).unwrap();
        }

        let mut notes_found = [false; 128];
        let mut notes_y: NoteYCoords = [0; 128];
        let note_height: u32;
        let mut note_count = 0;
        for event in sequencer.events.iter() {
            if event.message.kind == MessageKind::NoteOn {
                notes_found[event.message.note as usize] = true;
            }
        }
        for event in sequencer.recording_events.iter() {
            if event.message.kind == MessageKind::NoteOn {
                notes_found[event.message.note as usize] = true;
            }
        }
        for i in 0..128 {
            notes_found[i] |= sequencer.recording_open_events[i].is_some();
            if notes_found[i] {
                note_count += 1;
            }
        }

        if note_count > 0 {
            note_height = min(self.inner.h / note_count, self.inner.h / 10);
            {
                let mut y = self.inner.h;
                for i in 0..128 {
                    if notes_found[i] {
                        y -= note_height;
                        notes_y[i] = y as i32;
                    }
                }
            }

            let mut render_note = |event: &SequencerEvent| {
                let x1 = position_to_x(sequencer, event.position, rect);
                let x2 = position_to_x(sequencer, event.position + event.duration, rect);
                let note_rect = Rect::new(x1, self.inner.y + notes_y[event.message.note as usize], (x2 - x1) as u32, note_height);

                let color = Color::RGB(
                    (50 + event.message.velocity as u32 * 180 / 128) as u8,
                    50,
                    (220 - event.message.velocity as u32 * 180 / 128) as u8
                );
                let text_color = brighten_color(&color, 1.5);

                context.canvas.set_draw_color(dim_color_u8(&color, 2));
                context.canvas.fill_rect(note_rect).unwrap();
                context.canvas.set_draw_color(color);
                draw_rect(context.canvas, note_rect, 3);
            };

            for event in sequencer.events.iter() {
                render_note(event);
            }

            for event in sequencer.recording_events.iter() {
                render_note(event);
            }

            for note in 0..sequencer.recording_open_events.len() {
                match sequencer.recording_open_events[note] {
                    Some(event) => {
                        let mut tmp_event = event.clone();
                        tmp_event.duration = sequencer.normalize(sequencer.position, tmp_event.position);
                        render_note(&tmp_event);
                    }
                    None => ()
                }
            }
        }

        context.canvas.set_draw_color(Color::RGB(255, 255, 255));
        context.canvas.fill_rect(Rect::new(
            position_to_x(sequencer, sequencer.position, rect),
            rect.y(),
            3,
            self.inner.h,
        )).unwrap();
    }
}
