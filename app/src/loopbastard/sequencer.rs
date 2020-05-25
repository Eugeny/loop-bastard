use super::{App, Message, MessageKind, TICKS_PER_BEAT};
use super::events::{AppEvent, EventHandler, EventLoop};
use std::vec::Vec;
use std::cmp::max;

#[derive(PartialEq, Clone, Copy, Eq, Debug)]
pub struct SequencerEvent {
    pub position: u32,
    pub duration: u32,
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
        let q = TICKS_PER_BEAT * 4 / self.divisor;
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
    open_notes: [bool; 128],
    pub position: u32,
    pub input_channel: u8,
    pub output_channel: u8,
    pub _length: u32,

    pub events: Vec<SequencerEvent>,
    pub recording_events: Vec<SequencerEvent>,
    pub recording_open_events: FullNoteSet,

    pub running: bool,
    pub recording: bool,
    is_first_recording: bool,
    pub scheduled_action: Option<SequencerAction>,
}

type FullNoteSet = [Option<SequencerEvent>; 128];
const EMPTY_NOTE_SET: FullNoteSet = [None; 128];

impl Sequencer {
    pub fn new() -> Self {
        return Self {
            position: 0,
            _length: 4 * TICKS_PER_BEAT,
            input_channel: 0,
            output_channel: 1,
            open_notes: [false; 128],
            recording_events: Vec::new(),
            recording_open_events: EMPTY_NOTE_SET,
            events: Vec::new(),
            running: false,
            recording: false,
            is_first_recording: false,
            scheduled_action: None,
        }
    }

    pub fn perform(&mut self, action: SequencerAction) {
        match action {
            SequencerAction::Start => {
                if self.recording {
                    self.commit_recording();
                    self.recording = false;
                } else {
                    self.position = 0;
                }
                self.running = true;
            },
            SequencerAction::Stop => {
                if self.recording {
                    self.commit_recording();
                }
                self.running = false;
                self.recording = false;
                self.position = 0;
            },
            SequencerAction::Record => {
                if self.recording {
                    self.commit_recording();
                }
                self.running = true;
                self.recording = true;
                self.is_first_recording = self.events.len() == 0;
            },
        }
        self.scheduled_action = None;
    }

    pub fn schedule(&mut self, action: SequencerAction) {
        self.scheduled_action = Some(action)
    }

    pub fn length(&self) -> u32 {
        return max(self.position, self._length)
    }

    fn get_open_events_at_position(&self, position: u32, note_set: &mut FullNoteSet) {
        *note_set = EMPTY_NOTE_SET;
        for event in &self.events {
            if event.position >= position {
                break;
            }
            if event.position + event.duration < position {
                continue;
            }
            note_set[event.message.note as usize] = Some(*event);
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
                Some(event) => if !self.open_notes[note] {
                    self.set_note_on(&event.message, event_loop);
                },
                None => if self.open_notes[note] {
                    self.set_note_off(note as u8, event_loop);
                },
            }
        }
    }

    fn sort_events(&mut self) {
        self.events.sort_by(|a, b| { a.position.cmp(&b.position) })
    }

    #[inline]
    pub fn normalize(&self, end: u32, start: u32) -> u32 {
        return (end + self._length - start) % self._length;
    }

    fn close_recording_event(&mut self, event: SequencerEvent) {
        self.recording_events.push(SequencerEvent {
            position: event.position,
            duration: self.normalize(self.position, event.position),
            message: event.message.clone(),
        });
        self.recording_open_events[event.message.note as usize] = None;
    }

    fn commit_recording(&mut self) {
        if self.is_first_recording {
            self._length = self.position
        }

        for i in 0..self.recording_open_events.len() {
            match self.recording_open_events[i] {
                Some(event) => self.close_recording_event(event),
                None => (),
            }
        }
        self.recording_open_events = EMPTY_NOTE_SET;
        self.events.append(&mut self.recording_events);
        self.sort_events();
    }
}

impl EventHandler for Sequencer {
    fn handle_event(&mut self, _app: &App, event: &AppEvent, event_loop: &mut EventLoop) {
        match event {
            AppEvent::MIDIMessage(message) => {
                if self.recording && (self.input_channel == 0 || message.channel == self.input_channel) {
                    if message.kind == MessageKind::NoteOn || message.kind == MessageKind::NoteOff {
                        let seq_event = self.recording_open_events[message.note as usize].clone();
                        if seq_event.is_some() {
                            self.close_recording_event(seq_event.unwrap());
                        }
                    }
                    if message.kind == MessageKind::NoteOn {
                        let seq_event = self.recording_open_events[message.note as usize].clone();
                        if seq_event.is_some() {
                            self.close_recording_event(seq_event.unwrap());
                        }
                        self.recording_open_events[message.note as usize] = Some(SequencerEvent {
                            position: self.position,
                            duration: 0,
                            message: message.clone(),
                        });
                    }
                }
            },

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
                    self.position += 1;
                    if !(self.recording && self.is_first_recording) {
                        self.position = self.position % self._length;
                    } else {
                        self._length = max(self._length, self.position);
                    }
                } else {
                    self.set_notes_on(&EMPTY_NOTE_SET, event_loop);
                }
            },
            _ => (),
        }
    }
}
