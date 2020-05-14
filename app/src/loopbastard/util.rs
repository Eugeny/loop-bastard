use crossbeam_utils::thread::Scope;

pub trait WithThread where Self: std::marker::Send {
    fn run(&mut self);
    fn start<'a> (&'a mut self, scope: &Scope<'a>) {
        scope.spawn(move |_| {
            self.run()
        });
    }
}
