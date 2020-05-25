extern crate loop_bastard_ui;
use sdl2::rect::Rect;

use loop_bastard_ui::View;
use super::{StatusBarView, View, ViewBase, ViewInner, RenderContext, SequencersView, SequencerBodyView};

#[derive(View)]
pub struct RootView {
    inner: ViewInner,
    status_bar: StatusBarView,
    sequencers: SequencersView,
    sequencer_bodies: Vec<SequencerBodyView>,
}

impl RootView {
    pub fn new() -> Self {
        return Self {
            inner: ViewInner::new(),
            status_bar: StatusBarView::new(),
            sequencers: SequencersView::new(),
            sequencer_bodies: Vec::new(),
        };
    }
}

impl ViewBase for RootView {
    fn foreach_child<F>(&mut self, mut f: F) where F: FnMut(&mut dyn View) {
        f(&mut self.status_bar);
        f(&mut self.sequencers);
        for s in self.sequencer_bodies.iter_mut() {
            f(s);
        }
    }

    fn render(&mut self, context: &mut RenderContext, _rect: &Rect) {
        let status_bar_h = 40;
        let status_bar_margin = 10;
        let sequencers_margin = 10;
        let sequencers_w = self.inner.w * 4 / 10;
        let top_h = 120;
        let sequencer_body_margin = 10;
        let state = context.app.state.borrow();
        self.status_bar.set_position(0, 0);
        self.status_bar.set_size(self.inner.w, status_bar_h);
        self.sequencers.set_position(sequencers_margin, status_bar_h as i32 + status_bar_margin as i32);
        self.sequencers.set_size(sequencers_w, top_h);

        for i in self.sequencer_bodies.len()..state.sequencers.len() {
            self.sequencer_bodies.push(SequencerBodyView::new(i));
        }

        for (index, s) in self.sequencer_bodies.iter_mut().enumerate() {
            s.set_size(
                self.inner.w - sequencer_body_margin * 2,
                self.inner.h - sequencer_body_margin * 2 - status_bar_h - status_bar_margin - top_h,
            );
            s.set_position(sequencer_body_margin as i32, (status_bar_h + status_bar_margin + top_h + sequencer_body_margin) as i32);
            s.set_enabled(index == state.selected_sequencer);
        }
    }
}
