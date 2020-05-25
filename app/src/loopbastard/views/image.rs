extern crate loop_bastard_ui;

use sdl2::rect::Rect;
use sdl2::render::{TextureQuery, BlendMode};
use sdl2::pixels::Color;
use loop_bastard_ui::View;

use super::{View, ViewBase, ViewInner, RenderContext};


#[derive(View)]
pub struct ImageView {
    inner: ViewInner,
    path: String,
    color: Color,
}

impl ImageView {
    pub fn new(path: String, color: Color) -> Self {
        return Self {
            inner: ViewInner::new(),
            path: path,
            color: color,
        };
    }

    pub fn set_image(&mut self, path: String) {
        if self.path != path {
            self.path = path;
        }
    }

    pub fn set_color(&mut self, color: Color) {
        self.color = color;
    }
}

impl ViewBase for ImageView {
    fn render(&mut self, context: &mut RenderContext, rect: &Rect) {
        let texture = context.texture_cache.get_image(context.canvas, &self.path);
        let TextureQuery { width, height, .. } = texture.query();

        texture.set_color_mod(self.color.r, self.color.g, self.color.b);
        texture.set_blend_mode(BlendMode::Blend);

        let destination = Rect::new(
            rect.left() + (self.inner.w as i32 / 2 - width as i32 / 2),
            rect.top() + (self.inner.h as i32 / 2 - height as i32 / 2),
            width,
            height
        );
        context.canvas.copy(&texture, None, destination).unwrap();
    }
}
