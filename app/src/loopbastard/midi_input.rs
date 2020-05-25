extern crate log;
extern crate midir;
extern crate midi;
use std::sync::Arc;
use std::vec::Vec;
use std::sync::Mutex;
use std::time::{Instant, Duration};
use super::App;
use super::events::{AppEvent, EventLoop, EventHandler};
use midir::{MidiInput, MidiInputConnection};
use std::collections::HashMap;
use log::{info, debug, warn};

pub const MIDI_NAME: &str = "LoopBastard";

#[derive(Debug, Copy, Clone, Eq, PartialEq)]
pub enum MessageKind {
    ActiveSensing,
    Continue,
    NoteOff,
    NoteOn,
    SongPosition,
    Start,
    Unknown1,
    Unknown2,
    Unknown3,
    Stop,
    TimingClock,
}

#[derive(Debug, Copy, Clone, Eq, PartialEq)]
pub struct Message {
    pub kind: MessageKind,
    pub channel: u8,
    pub note: u8,
    pub velocity: u8,
    pub position: u16,
    pub message: u8,
    pub a: u8,
    pub b: u8,
}

impl Message {
    pub fn new(kind: MessageKind) -> Self {
        return Self {
            kind: kind,
            channel: 0,
            note: 0,
            velocity: 0,
            position: 0,
            message: 0,
            a: 0,
            b: 0,
        }
    }

    pub fn from(data: &[u8]) -> Message {
        let mut m = Self::new(MessageKind::Unknown1);
        match data[0] {
            midi::constants::ACTIVE_SENSING => { m.kind = MessageKind::ActiveSensing; },
            midi::constants::CONTINUE => { m.kind = MessageKind::Continue; },
            midi::constants::SONG_POSITION_POINTER => {
                m.kind = MessageKind::SongPosition;
                m.position = ((data[1] as u16) << 7) + data[2] as u16;
            },
            midi::constants::START => { m.kind = MessageKind::Start; },
            midi::constants::STOP => { m.kind = MessageKind::Stop; },
            midi::constants::TIMING_CLOCK => { m.kind = MessageKind::TimingClock; },
            _ => {
                match data[0] >> 4 {
                    midi::constants::NOTE_OFF => {
                        m.kind = MessageKind::NoteOff;
                        m.channel = (data[0] & 0x0F) + 1;
                        m.note = data[1];
                        m.velocity = data[2];
                    },
                    midi::constants::NOTE_ON => {
                        m.kind = MessageKind::NoteOn;
                        println!("{:?} {:?} {:?}", data[0], data[0] & 0xf, data[0] & 0x0f);
                        m.channel = (data[0] & 0x0F) + 1;
                        m.note = data[1];
                        m.velocity = data[2];
                    },
                    _ => match data.len() {
                        1 => { m.message = data[0]; },
                        2 => { m.kind = MessageKind::Unknown2; m.message = data[0]; m.a = data[1]; },
                        3 => { m.kind = MessageKind::Unknown3; m.message = data[0]; m.a = data[1]; m.b = data[2]; },
                        _ => panic!("Message too long"),
                    }
                }
            }
        };
        return m;
    }

    pub fn to_bytes(&self) -> ([u8; 3], usize) {
        match &self.kind {
            MessageKind::ActiveSensing => ([midi::constants::ACTIVE_SENSING, 0, 0], 1),
            MessageKind::Continue => ([midi::constants::CONTINUE, 0, 0], 1),
            MessageKind::SongPosition => ([midi::constants::SONG_POSITION_POINTER, (self.position >> 7) as u8, (self.position & 0x7f) as u8], 3),
            MessageKind::Start => ([midi::constants::START, 0, 0], 1),
            MessageKind::Stop => ([midi::constants::STOP, 0, 0], 1),
            MessageKind::TimingClock => ([midi::constants::TIMING_CLOCK, 0, 0], 1),
            MessageKind::NoteOn => ([(midi::constants::NOTE_ON << 4) + self.channel - 1, self.note, self.velocity], 3),
            MessageKind::NoteOff => ([(midi::constants::NOTE_OFF << 4) + self.channel - 1, self.note, self.velocity], 3),
            MessageKind::Unknown1 => ([self.message, 0, 0], 1),
            MessageKind::Unknown2 => ([self.message, self.a, 0], 2),
            MessageKind::Unknown3 => ([self.message, self.a, self.b], 3),
        }
    }
}

struct MIDIInputConnection {
    pub last_message: Instant,
    _connection: MidiInputConnection<()>,
    message_queue: Arc<Mutex<Vec<Message>>>,
}

pub struct MIDIInput {
    midi_input: MidiInput,
    connections: HashMap<String, MIDIInputConnection>,
    failed_ports: Vec<String>,
}

impl MIDIInput {
    pub fn new() -> MIDIInput {
        return MIDIInput {
            midi_input: MidiInput::new(MIDI_NAME).unwrap(),
            connections: HashMap::new(),
            failed_ports: Vec::new(),
        };
    }

    pub fn tick(&mut self, event_loop: &mut EventLoop) {
        for (name, connection) in self.connections.iter_mut() {
            let mut queue = connection.message_queue.lock().unwrap();
            if queue.len() > 0 {
                connection.last_message = Instant::now();
            }

            for message in queue.iter() {
                event_loop.post(AppEvent::MIDIMessage(message.clone()));
                if message.kind != MessageKind::TimingClock {
                    debug!("Messsage [{}]: {:?}", name, message);
                }
            }
            queue.clear();
        }
    }

    pub fn has_input (&self) -> bool {
        return self.connections.len() > 0
    }

    pub fn has_recent_input (&self) -> bool {
        let now = Instant::now();
        for connection in self.connections.values() {
            if now - connection.last_message < Duration::from_millis(20) {
                return true;
            }
        }
        return false;
    }
}

impl EventHandler for MIDIInput {
    fn handle_event(&mut self, _app: &App, event: &AppEvent, _event_loop: &mut EventLoop) {
        match event {
            AppEvent::MIDIIOScan => {
                let names: Vec<(usize, String)> = (0..self.midi_input.port_count()).into_iter().filter_map(|i| {
                    self.midi_input.port_name(i).map(|x| (i, x)).ok()
                }).collect();

                for (index, name) in names.iter() {
                    if !self.connections.contains_key(name) && !name.contains(MIDI_NAME) {
                        info!("New input port: {}", name);

                        let queue = Arc::new(Mutex::new(Vec::new()));
                        let q = queue.clone();
                        let connection = MidiInput::new(MIDI_NAME).unwrap().connect(*index, name, move |_, message, _| {
                            q.lock().unwrap().push(Message::from(message));
                        }, ());

                        if connection.is_ok() {
                            self.connections.insert(name.clone(), MIDIInputConnection {
                                _connection: connection.unwrap(),
                                last_message: Instant::now(),
                                message_queue: queue,
                            });
                        } else {
                            warn!("Input is failing: {}", name);
                            self.failed_ports.push(name.clone());
                        }
                    }
                }

                let mut dead_ports: Vec<String> = Vec::new();

                for name in self.connections.keys() {
                    if names.iter().find(|&x| x.1 == *name).is_none() {
                        dead_ports.push(name.clone());
                    }
                }

                for name in dead_ports {
                    info!("Lost input port: {}", &name);
                    self.connections.remove(&name);
                }
            },
            _ => (),
        }
    }
}
