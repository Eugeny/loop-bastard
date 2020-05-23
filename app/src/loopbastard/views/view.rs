extern crate sdl2;
use sdl2::rect::Rect;
use super::App;
use super::TextureCache;
use crate::loopbastard::events::AppEvent;
pub type Canvas = sdl2::render::Canvas<sdl2::video::Window>;

pub struct RenderContext<'a> {
    pub app: &'a App,
    pub texture_cache: &'a mut TextureCache,
    pub canvas: &'a mut Canvas,
}

pub struct ViewInner {
    pub x: i32,
    pub y: i32,
    pub w: u32,
    pub h: u32,
    pub enabled: bool,
}

impl ViewInner {
    pub fn new() -> Self {
        return Self {
            x: 0, y: 0, w: 0, h: 0,
            enabled: true,
        }
    }
}

#[allow(unused)]
pub trait View {
    fn get_inner(&self) -> &ViewInner;
    fn get_inner_mut(&mut self) -> &mut ViewInner;
    fn render_recursive(&mut self, context: &mut RenderContext, rect: &Rect) {}
    fn handle_event_recursive(&mut self, app: &App, event: &AppEvent) {}
    fn set_position(&mut self, x: i32, y: i32);
    fn set_size(&mut self, w: u32, h: u32);
    fn set_enabled(&mut self, enabled: bool);
}

#[allow(unused)]
pub trait ViewBase {
    fn render(&mut self, context: &mut RenderContext, rect: &Rect) {}
    fn handle_event(&mut self, app: &App, event: &AppEvent) {}
    fn foreach_child<F>(&mut self, mut f: F) where F: FnMut(&mut (dyn View)) {}
    fn foreach_event_handler<F>(&mut self, mut f: F) where F: FnMut(&mut (dyn View)) { self.foreach_child(f); }
}
