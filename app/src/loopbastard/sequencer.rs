use super::{App, Message, MessageKind};
use super::events::{AppEvent, EventHandler, EventLoop};
use std::vec::Vec;

#[derive(PartialEq, Clone, Eq, Debug)]
pub struct SequencerEvent {
    pub position: u32,
    pub message: Message,
    // pub created_at: u32,
    // pub ignore: bool,
}

pub trait Filter {
    fn filter(&self, events: &mut Vec<SequencerEvent>, sequencer: &Sequencer);
}

pub struct QuantizerFilter {
    pub divisor: u32
}

#[derive(PartialEq, Clone, Eq, Debug)]
pub enum SequencerAction {
    Start, Stop, Record,
}

#[inline]
fn div_round(a: u32, b: u32) -> u32 {
    return a / b + (a % b * 2 / b);
}

fn get_off_event_index_for_on_event<'a>(events: &'a mut Vec<SequencerEvent>, s: usize) -> Option<usize> {
    if s >= events.len() || events[s].message.kind != MessageKind::NoteOn {
        return None;
    }

    match events.iter().position(|x| *x == events[s]) {
        Some(position) => {
            for i in position..events.len() {
                if events[i].message.kind == MessageKind::NoteOff && events[i].message.note == events[s].message.note {
                    return Some(i)
                }
            }
            for i in 0..position {
                if events[i].message.kind == MessageKind::NoteOff && events[i].message.note == events[s].message.note {
                    return Some(i)
                }
            }
        },
        _ => return None,
    }
    return None;
}

impl Filter for QuantizerFilter {
    fn filter(&self, events: &mut Vec<SequencerEvent>, _sequencer: &Sequencer) {
        if self.divisor == 0 {
            return;
        }
        let q = 24 * 4 / self.divisor;
        for i in 0..events.len() {
            let dp = div_round(events[i].position, q) * q - events[i].position;
            events[i].position += dp;
            if let Some(index) = get_off_event_index_for_on_event(events, i) {
                events[index].position += dp
            }
        }
    }
}

pub struct Sequencer {
    position: u32,
    open_notes: [bool; 128],
    pub input_channel: u8,
    pub output_channel: u8,
    pub length: u32,
    pub events: Vec<SequencerEvent>,
    pub running: bool,
    pub recording: bool,
    pub scheduled_action: Option<SequencerAction>,
}

type FullNoteSet = [Option<Message>; 128];
const EMPTY_NOTE_SET: FullNoteSet = [None; 128];

impl Sequencer {
    pub fn new() -> Self {
        return Self {
            position: 0,
            length: 4 * 24 * 4,
            input_channel: 0,
            output_channel: 1,
            open_notes: [false; 128],
            events: Vec::new(),
            running: false,
            recording: false,
            scheduled_action: None,
        }
    }

    pub fn perform(&mut self, action: SequencerAction) {
        match action {
            SequencerAction::Start => {
                self.running = true;
                self.recording = false;
                self.position = 0;
            },
            SequencerAction::Stop => {
                self.running = false;
                self.recording = false;
                self.position = 0;
            },
            SequencerAction::Record => {
                self.running = true;
                self.recording = true;
                self.position = 0;
            },
        }
    }

    pub fn schedule(&mut self, action: SequencerAction) {
        self.scheduled_action = Some(action)
    }

    fn get_open_events_at_position(&self, position: u32, note_set: &mut FullNoteSet) {
        *note_set = EMPTY_NOTE_SET;
        for event in &self.events {
            if event.position >= position {
                break;
            }
            if event.message.kind == MessageKind::NoteOn {
                note_set[event.message.note as usize] = Some(event.message);
            } else if event.message.kind == MessageKind::NoteOff {
                note_set[event.message.note as usize] = None;
            }
        }
    }

    fn set_note_on(&mut self, message: &Message, event_loop: &mut EventLoop) {
        self.open_notes[message.note as usize] = true;
        let mut message = message.clone();
        message.channel = self.output_channel;
        event_loop.post(AppEvent::MIDIOutputMessage(message))
    }

    fn set_note_off(&mut self, note: u8, event_loop: &mut EventLoop) {
        self.open_notes[note as usize] = false;
        let mut message = Message::new(MessageKind::NoteOff);
        message.channel = self.output_channel;
        message.note = note;
        event_loop.post(AppEvent::MIDIOutputMessage(message))
    }

    fn set_notes_on(&mut self, note_set: &FullNoteSet, event_loop: &mut EventLoop) {
        for note in 0..128 {
            match &note_set[note] {
                Some(message) => if !self.open_notes[note] {
                    self.set_note_on(&message, event_loop);
                },
                None => if self.open_notes[note] {
                    self.set_note_off(note as u8, event_loop);
                },
            }
        }
    }
}

impl EventHandler for Sequencer {
    fn handle_event(&mut self, _app: &App, event: &AppEvent, event_loop: &mut EventLoop) {
        match event {
            AppEvent::GlobalQuantizerStep => {
                if let Some(action) = self.scheduled_action.clone() {
                    self.perform(action);
                    self.scheduled_action = None;
                }
            },
            AppEvent::ClockTick => {
                let mut temp_note_set = EMPTY_NOTE_SET;
                if self.running {
                    self.get_open_events_at_position(self.position, &mut temp_note_set);
                    self.set_notes_on(&temp_note_set, event_loop);
                } else {
                    self.set_notes_on(&EMPTY_NOTE_SET, event_loop);
                }
                self.position += 1;
                self.position = self.position % self.length;
            },
            _ => (),
        }
    }
}
