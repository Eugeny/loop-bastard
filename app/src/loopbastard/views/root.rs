extern crate loop_bastard_ui;
use sdl2::rect::Rect;
use std::rc::Rc;

use loop_bastard_ui::View;
use super::{StatusBarView, Canvas, View, ViewBase, ViewInner, App};

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
    fn foreach_child<F>(&mut self, mut f: F) where F: FnMut(&mut View) {
        f(&mut self.status_bar);
    }

    fn render(&mut self, app: &mut App, canvas: &mut Canvas, rect: &Rect) {
        self.status_bar.set_size(self.inner.w, 40);
    }
}
