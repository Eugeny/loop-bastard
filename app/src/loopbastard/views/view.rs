extern crate sdl2;
use sdl2::rect::Rect;

pub type Canvas = sdl2::render::Canvas<sdl2::video::Window>;

pub struct ViewInner {
    pub x: i32,
    pub y: i32,
    pub w: u32,
    pub h: u32,
}

impl ViewInner {
    pub fn new() -> Self {
        return Self {
            x: 0, y: 0, w: 0, h: 0,
        }
    }
}

pub trait View {
    fn get_inner(&self) -> &ViewInner;
    fn get_inner_mut(&mut self) -> &mut ViewInner;
    fn layout_recursive(&mut self);
    fn render_recursive(&mut self, canvas: &mut Canvas, rect: &Rect);
    fn set_position(&mut self, x: i32, y: i32);
    fn set_size(&mut self, w: u32, h: u32);
}

pub trait ViewBase {
    fn layout(&mut self) {}
    fn render(&mut self, canvas: &mut Canvas, rect: &Rect) {}
    fn foreach_child<F>(&mut self, mut _f: F) where F: FnMut(&mut View) {}
}
