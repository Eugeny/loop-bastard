extern crate crossbeam_utils;
extern crate sdl2;

use super::views::{View, TextureCache, RenderContext};
use super::{App, AsyncTicking};
use sdl2::pixels::Color;
use sdl2::event::Event;
use sdl2::keyboard::Keycode;
use sdl2::rect::Rect;
use sdl2::render::BlendMode;
use super::events::{AppEvent, EventHandler, EventLoop};

pub struct Display {
    pub root_view: Box<dyn View>,
    event_pump: sdl2::EventPump,
    canvas: sdl2::render::Canvas<sdl2::video::Window>,
    texture_cache: TextureCache,
}

impl Display {
    pub fn new(root: Box<dyn View>) -> Self {
        let context = sdl2::init().unwrap();
        let video_subsystem = context.video().unwrap();

        let window = video_subsystem.window("rust-sdl2 demo", 800, 480)
            .position_centered()
            .build()
            .unwrap();

        let mut canvas = window.into_canvas().build().unwrap();
        context.mouse().show_cursor(false);
        canvas.set_draw_color(Color::RGB(0, 0, 0));
        canvas.clear();
        canvas.present();

        let event_pump = context.event_pump().unwrap();

        return Display {
            root_view: root,
            event_pump: event_pump,
            canvas: canvas,
            texture_cache: TextureCache::new(),
        };
    }

    fn render(&mut self, app: &App) {
        self.canvas.set_draw_color(Color::RGB(0, 0, 0));
        self.canvas.clear();
        self.canvas.set_blend_mode(BlendMode::Blend);

        let output_size = self.canvas.output_size().unwrap();
        let rect = Rect::new(0, 0, output_size.0, output_size.1);
        self.root_view.set_position(0, 0);
        self.root_view.set_size(rect.width(), rect.height());
        let mut context: RenderContext = RenderContext {
            canvas: &mut self.canvas,
            app: app,
            texture_cache: &mut self.texture_cache,
        };
        self.root_view.render_recursive(&mut context, &rect);

        self.canvas.present();
    }
}

impl EventHandler for Display {
    fn handle_event(&mut self, app: &App, event: &AppEvent, event_loop: &mut EventLoop) {
        match event {
            AppEvent::UpdateDisplay => {
                self.render(app);
                for sdl_event in self.event_pump.poll_iter() {
                    match sdl_event {
                        Event::Quit {..} |
                        Event::KeyDown { keycode: Some(Keycode::Escape), .. } => {
                            ::std::process::exit(0);
                        },
                        _ => {
                            event_loop.post(AppEvent::SDLEvent(sdl_event))
                        }
                    }
                }
            }
            _ => (),
        }
    }
}
