extern crate loop_bastard_ui;
use sdl2::rect::Rect;

use loop_bastard_ui::View;
use super::{StatusBarView, View, ViewBase, ViewInner, RenderContext, SequencersView};

#[derive(View)]
pub struct RootView {
    inner: ViewInner,
    status_bar: StatusBarView,
    sequencers: SequencersView,
}

impl RootView {
    pub fn new() -> Self {
        return Self {
            inner: ViewInner::new(),
            status_bar: StatusBarView::new(),
            sequencers: SequencersView::new(),
        };
    }
}

impl ViewBase for RootView {
    fn foreach_child<F>(&mut self, mut f: F) where F: FnMut(&mut dyn View) {
        f(&mut self.status_bar);
        f(&mut self.sequencers);
    }

    fn render(&mut self, _context: &mut RenderContext, _rect: &Rect) {
        let status_bar_h = 40;
        let sequencers_margin = 10;
        let top_h = 160;
        self.status_bar.set_position(0, 0);
        self.status_bar.set_size(self.inner.w, status_bar_h);
        self.sequencers.set_position(sequencers_margin, status_bar_h as i32 + sequencers_margin as i32);
        self.sequencers.set_size(self.inner.w / 2 - sequencers_margin as u32 * 2, top_h);
    }
}
