extern crate loop_bastard_ui;

use sdl2::rect::Rect;
use sdl2::pixels::Color;
use loop_bastard_ui::View;

use super::{View, ViewBase, ViewInner, RenderContext, TextView, Alignment, ImageView};
use crate::loopbastard::SequencerAction;
use crate::loopbastard::util::{get_beat_color, get_blink_color, draw_rect, dim_color};

#[derive(View)]
pub struct SequencerView {
    index: usize,
    inner: ViewInner,
    index_text: TextView,
    icon: ImageView,
}

impl SequencerView {
    pub fn new(index: usize) -> Self {
        return Self {
            index: index,
            inner: ViewInner::new(),
            index_text: TextView::new("-", Color::RGB(255, 255, 255)),
            icon: ImageView::new(String::from("images/play.png"), Color::RGB(0, 0, 0)),
        };
    }
}

impl ViewBase for SequencerView {
    fn render(&mut self, context: &mut RenderContext, rect: &Rect) {
        // let border_size = 3;
        let padding = 10;
        let seq = &context.app.state.borrow().sequencers[self.index];
        let clock = context.app.clock.borrow();
        let state = context.app.state.borrow();
        let selected = self.index == state.selected_sequencer;

        let mut border_color = if selected { Color::RGB(0, 128, 255) } else { Color::RGB(128, 128, 128) };
        border_color = match (seq.scheduled_action.clone(), seq.running, seq.recording) {
            (None, false, false) =>
                border_color,
            (None, true, false) =>
                get_beat_color(&clock, &Color::RGB(0, 255, 0), &border_color),
            (Some(SequencerAction::Start), _, _) =>
                get_blink_color(&clock, &Color::RGB(0, 255, 0), &border_color),
            (None, _, true) =>
                get_beat_color(&clock, &Color::RGB(255, 0, 0), &border_color),
            (Some(SequencerAction::Stop), _, _) =>
                get_blink_color(&clock, &Color::RGB(128, 128, 128), &border_color),
            (Some(SequencerAction::Record), _, _) =>
                get_blink_color(&clock, &Color::RGB(255, 0, 0), &border_color),
        };

        let background = dim_color(&border_color, 4.0);
        let border_size = 6;

        context.canvas.set_draw_color(background);
        context.canvas.fill_rect(*rect).unwrap();
        context.canvas.set_draw_color(border_color);
        draw_rect(context.canvas, *rect, border_size);

        self.index_text.set_size(self.inner.w, self.inner.h - padding * 2);
        self.index_text.set_position(0, padding as i32);
        self.index_text.set_font_size(48);
        self.index_text.set_alignment(Alignment::Center);
        self.index_text.set_text(format!("{}", self.index + 1));

        if state.sequencers[self.index].running {
            if state.sequencers[self.index].recording {
                self.icon.set_image(String::from("images/record.png"));
            } else {
                self.icon.set_image(String::from("images/play-sm.png"));
            }
        }

        self.icon.set_color(border_color);
        self.icon.set_position(0, self.inner.h as i32 / 2);
        self.icon.set_size(self.inner.w, self.inner.h / 2 - padding);
        self.icon.set_enabled(state.sequencers[self.index].running)
    }

    fn foreach_child<F>(&mut self, mut f: F) where F: FnMut(&mut dyn View) {
        f(&mut self.index_text);
        f(&mut self.icon);
    }
}
