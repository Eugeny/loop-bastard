extern crate loop_bastard_ui;

use sdl2::rect::Rect;
use sdl2::pixels::Color;
use loop_bastard_ui::View;

use super::{View, ViewBase, ViewInner, RenderContext, TextView, Alignment};
use crate::loopbastard::util::draw_rect;

#[derive(View)]
pub struct BankView {
    index: usize,
    inner: ViewInner,
    title_text: TextView,
    index_text: TextView,
}

impl BankView {
    pub fn new(index: usize) -> Self {
        return Self {
            index: index,
            inner: ViewInner::new(),
            title_text: TextView::new("Bank", Color::RGB(255, 255, 255)),
            index_text: TextView::new("-", Color::RGB(255, 255, 255)),
        };
    }
}

impl ViewBase for BankView {
    fn render(&mut self, context: &mut RenderContext, rect: &Rect) {
        let padding = 10;
        let state = context.app.state.borrow();
        let selected = state.selected_bank == self.index;
        let border_color = if selected { Color::RGB(0, 128, 255) } else { Color::RGB(128, 128, 128) };
        let background = Color::RGB(border_color.r / 4, border_color.g / 4, border_color.b / 4);
        let border_size = 6;

        context.canvas.set_draw_color(background);
        context.canvas.fill_rect(*rect).unwrap();
        context.canvas.set_draw_color(border_color);
        draw_rect(context.canvas, *rect, border_size);

        self.title_text.set_size(self.inner.w, self.inner.h);
        self.title_text.set_position(0, padding as i32);
        self.title_text.set_font_size(24);
        self.title_text.set_alignment(Alignment::Center);

        self.index_text.set_size(self.inner.w, self.inner.h / 2 - padding);
        self.index_text.set_position(0, (self.inner.h / 2) as i32);
        self.index_text.set_font_size(48);
        self.index_text.set_alignment(Alignment::Center);
        self.index_text.set_text(format!("{}", self.index + 1));
    }

    fn foreach_child<F>(&mut self, mut f: F) where F: FnMut(&mut dyn View) {
        f(&mut self.title_text);
        f(&mut self.index_text);
    }
}
