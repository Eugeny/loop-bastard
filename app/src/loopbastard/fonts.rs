lazy_static! {
    pub static ref ttf_context: sdl2::ttf::Sdl2TtfContext = sdl2::ttf::init().unwrap();
}

thread_local! {
    pub static font: sdl2::ttf::Font<'static, 'static> = ttf_context.load_font("bryant.ttf", 24).unwrap();
}
