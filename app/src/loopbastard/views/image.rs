extern crate loop_bastard_ui;

use sdl2::rect::Rect;
use sdl2::render::{TextureQuery, BlendMode, Texture};
use sdl2::pixels::Color;
use loop_bastard_ui::View;
use std::path::Path;

use super::{View, ViewBase, ViewInner, RenderContext, TextureStore};


#[derive(View)]
pub struct ImageView {
    inner: ViewInner,
    texture: Option<Texture>,
    image: Path,
    color: Color,
    width: u32,
    height: u32,
}

impl ImageView {
    pub fn new(path: &Path, color: Color) -> Self {
        return Self {
            inner: ViewInner::new(),
            texture: None,
            path: path,
            color: color,
            width: 0,
            height: 0,
        };
    }

    pub fn set_image(&mut self, path: &Path) {
        if self.path != path {
            self.path = path;
            self.texture = None;
        }
    }

    pub fn set_color(&mut self, color: Color) {
        self.color = color;
    }

    fn reload (&mut self, context: &mut RenderContext) {
        self.texture = context.texture_cache.get_image(context.canvas, self.image);
        let TextureQuery { width, height, .. } = self.image.query();
        self.width = width;
        self.height = height;
    }
}

impl ViewBase for ImageView {
    fn render(&mut self, context: &mut RenderContext, rect: &Rect) {
        if self.texture.is_none() {
            self.reload(context);
        }
        self.texture.set_color_mod(self.color.r, self.color.g, self.color.b);
        self.texture.set_blend_mode(BlendMode::Blend);

        let mut destination = Rect::new(
            rect.left() + self.inner.w / 2 - self.width / 2,
            rect.top() + self.inner.h / 2 - self.height / 2,
            self.width,
            self.height
        );
        context.canvas.copy(texture, None, destination).unwrap();
    }
}
