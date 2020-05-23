extern crate loop_bastard_ui;

use sdl2::rect::Rect;
use loop_bastard_ui::View;
use std::cmp::min;

use super::{App, View, ViewBase, ViewInner, RenderContext, SequencerView, BankView};
use crate::loopbastard::Button;
use crate::loopbastard::events::AppEvent;
use crate::loopbastard::util::arrange_spaced;

#[derive(View)]
pub struct SequencersView {
    inner: ViewInner,
    sequencers: Vec<SequencerView>,
    banks: Vec<BankView>,
    bank_size: usize,
    last_selected_in_bank: Vec<usize>,
}

impl SequencersView {
    pub fn new() -> Self {
        return Self {
            inner: ViewInner::new(),
            sequencers: Vec::new(),
            banks: Vec::new(),
            bank_size: 4,
            last_selected_in_bank: Vec::new(),
        };
    }
}

impl ViewBase for SequencersView {
    fn render(&mut self, context: &mut RenderContext, rect: &Rect) {
        let state = context.app.state.borrow();
        for i in self.sequencers.len()..state.sequencers.len() {
            self.sequencers.push(SequencerView::new(i));
        }
        for i in self.banks.len()..(self.sequencers.len() / self.bank_size) {
            self.banks.push(BankView::new(i));
            self.last_selected_in_bank.push(i * self.bank_size);
        }

        let start_index = state.selected_bank * self.bank_size;
        let end_index = min(self.sequencers.len(), self.bank_size + start_index);
        arrange_spaced(&mut self.sequencers[start_index..end_index], 5, rect);
        arrange_spaced(&mut self.banks, 5, rect);

        let controls = context.app.controls.borrow();
        for i in 0..self.banks.len() {
            self.banks[i].set_enabled(controls.shift_button.pressed);
        }
        for i in 0..self.sequencers.len() {
            self.sequencers[i].set_enabled(!controls.shift_button.pressed && i >= start_index && i < end_index);
        }
    }

    fn handle_event(&mut self, app: &App, event: &AppEvent) {
        match event {
            AppEvent::ButtonPress(Button::Number(number)) => {
                let mut state = app.state.borrow_mut();
                let controls = app.controls.borrow();

                if controls.shift_button.pressed {
                    self.last_selected_in_bank[state.selected_bank] = state.selected_sequencer;
                    state.selected_bank = number - 1;
                    state.selected_sequencer = self.last_selected_in_bank[state.selected_bank];
                } else {
                    let start_index = state.selected_bank * self.bank_size;
                    state.selected_sequencer = start_index + number - 1;
                }
            }
            _ => ()
        }
    }

    fn foreach_child<F>(&mut self, mut f: F) where F: FnMut(&mut dyn View) {
        for i in 0..self.sequencers.len() {
            f(&mut self.sequencers[i]);
        }
        for i in 0..self.banks.len() {
            f(&mut self.banks[i]);
        }
    }
}
