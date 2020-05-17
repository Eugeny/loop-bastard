extern crate log;
extern crate midir;
extern crate midi;
use std::sync::Arc;
use std::vec::Vec;
use std::sync::Mutex;
use std::time::{Instant, Duration};
use super::events::{AppEvent, EventLoop};
use midir::{MidiInput, MidiInputConnection};
use std::collections::HashMap;
use log::info;

const MIDI_NAME: &str = "LoopBastard";

#[derive(Debug, Clone)]
pub enum Message {
    ActiveSensing,
    Continue,
    NoteOff { channel: u8, note: u8, velocity: u8 },
    NoteOn { channel: u8, note: u8, velocity: u8 },
    SongPosition { position: u16 },
    Start,
    Unknown1 { message: u8 },
    Unknown2 { message: u8, a: u8 },
    Unknown3 { message: u8, a: u8, b: u8 },
    Stop,
    TimingClock,
}

impl Message {
    pub fn from(data: &[u8]) -> Message {
        return match data[0] {
            midi::constants::ACTIVE_SENSING => Message::ActiveSensing { },
            midi::constants::CONTINUE => Message::Continue { },
            midi::constants::SONG_POSITION_POINTER => Message::SongPosition { position: (data[1] as u16) << 7 + data[2] },
            midi::constants::START => Message::Start { },
            midi::constants::STOP => Message::Stop { },
            midi::constants::TIMING_CLOCK => Message::TimingClock { },
            _ => {
                match data[0] >> 4 {
                    midi::constants::NOTE_OFF => Message::NoteOff {
                        channel: data[0] & 0xF,
                        note: data[1], velocity: data[2]
                    },
                    midi::constants::NOTE_ON => Message::NoteOn {
                        channel: data[0] & 0xF,
                        note: data[1], velocity: data[2]
                    },
                    _ => match data.len() {
                        1 => Message::Unknown1 { message: data[0] },
                        2 => Message::Unknown2 { message: data[0], a: data[1] },
                        3 => Message::Unknown3 { message: data[0], a: data[1], b: data[2] },
                        _ => panic!("Message too long"),
                    }
                }
            }
        };
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
        let names: Vec<(usize, String)> = (0..self.midi_input.port_count()).into_iter().filter_map(|i| {
            self.midi_input.port_name(i).map(|x| (i, x)).ok()
        }).collect();

        for (index, name) in names.iter() {
            if !self.connections.contains_key(name) {
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
                    self.failed_ports.push(name.clone());
                }
            }
        }

        let mut dead_ports: Vec<String> = Vec::new();

        for (name, connection) in self.connections.iter_mut() {
            if names.iter().find(|&x| x.1 == *name).is_none() {
                dead_ports.push(name.clone());
                continue;
            }

            let mut queue = connection.message_queue.lock().unwrap();
            if queue.len() > 0 {
                connection.last_message = Instant::now();
            }

            for message in queue.iter() {
                event_loop.post(AppEvent::MIDIMessage(message.clone()));
            }
            queue.clear();
        }

        for name in dead_ports {
            info!("Lost input port: {}", &name);
            self.connections.remove(&name);
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
