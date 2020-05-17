extern crate loop_bastard_ui;
use sdl2::rect::Rect;

use loop_bastard_ui::View;
use super::{StatusBarView, View, ViewBase, ViewInner, RenderContext};

#[derive(View)]
pub struct RootView {
    inner: ViewInner,
    status_bar: StatusBarView,
}

impl RootView {
    pub fn new() -> Self {
        return Self {
            inner: ViewInner::new(),
            status_bar: StatusBarView::new(),
        };
    }
}

impl ViewBase for RootView {
    fn foreach_child<F>(&mut self, mut f: F) where F: FnMut(&mut dyn View) {
        f(&mut self.status_bar);
    }

    fn render(&mut self, _context: &mut RenderContext, _rect: &Rect) {
        self.status_bar.set_size(self.inner.w, 40);
    }
}
