mod loopbastard;
use loopbastard::App;

#[macro_use]
extern crate lazy_static;

pub fn main() {
    App::new().run();
}
