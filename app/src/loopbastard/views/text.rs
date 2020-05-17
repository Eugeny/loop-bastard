extern crate loop_bastard_ui;

use sdl2::rect::Rect;
use sdl2::render::{TextureQuery, BlendMode};
use sdl2::pixels::Color;
use loop_bastard_ui::View;
use std::path::Path;

use super::{View, ViewBase, ViewInner, RenderContext, TextureStore};


#[derive(Debug)]
pub enum Alignment {
    Left,
    Center,
    Right,
}

#[derive(View)]
pub struct TextView {
    inner: ViewInner,
    text: String,
    color: Color,
    texture_store: TextureStore,
    width: u32,
    height: u32,
    alignment: Alignment,
}

impl TextView {
    pub fn new(text: &str, color: Color) -> Self {
        return Self {
            inner: ViewInner::new(),
            text: String::from(text),
            color: color,
            texture_store: TextureStore::default(),
            width: 0,
            height: 0,
            alignment: Alignment::Center,
        };
    }

    pub fn set_text(&mut self, text: String) {
        if self.text != text {
            self.text = text;
            self.texture_store.clear();
        }
    }

    pub fn set_color(&mut self, color: Color) {
        self.color = color;
    }

    pub fn set_alignment(&mut self, alignment: Alignment) {
        self.alignment = alignment;
    }

    fn regenerate (&mut self, context: &mut RenderContext) {
        let font = context.texture_cache.get_ttf_context().load_font(Path::new("bryant.ttf"), 24).unwrap();
        let texture_creator = context.canvas.texture_creator();

        let surface = font
            .render(&self.text)
            .blended(Color::RGB(255,255,255))
            .map_err(|e| e.to_string())
            .unwrap();
        let font_texture = texture_creator
            .create_texture_from_surface(&surface)
            .map_err(|e| e.to_string())
            .unwrap();

        let TextureQuery { width, height, .. } = font_texture.query();
        self.width = width;
        self.height = height;
        self.texture_store.create_or_resize_texture(context.canvas, width, height);

        context.canvas.with_texture_canvas(self.texture_store.get_mut_ref(), |texture| {
            texture.set_draw_color(Color::RGBA(0, 0, 0, 0));
            texture.clear();
            texture
                .copy(
                    &font_texture,
                    None,
                    Rect::new(0, 0, width, height),
                )
                .unwrap();
        })
        .unwrap();
    }
}

impl ViewBase for TextView {
    fn render(&mut self, context: &mut RenderContext, rect: &Rect) {
        if self.texture_store.get_optional_ref().is_none() {
            self.regenerate(context);
        }
        let mut texture = self.texture_store.get_mut_ref();
        texture.set_color_mod(self.color.r, self.color.g, self.color.b);
        texture.set_blend_mode(BlendMode::Blend);

        let mut destination = Rect::new(rect.left(), rect.top(), self.width, self.height);
        match self.alignment {
            Alignment::Right => {
                destination.set_x(rect.right() - self.width as i32)
            },
            Alignment::Center => {
                destination.set_x(rect.left() + rect.width() as i32 / 2 - (self.width / 2) as i32)
            },
            _ => {},
        }
        context.canvas.copy(texture, None, destination).unwrap();
    }
}
