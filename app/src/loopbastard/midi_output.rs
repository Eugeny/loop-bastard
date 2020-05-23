extern crate log;
extern crate midir;
extern crate midi;
use super::{App, MIDI_NAME};
use super::events::{AppEvent, EventLoop, EventHandler};
use std::vec::Vec;
use std::collections::HashMap;
use midir::{MidiOutput, MidiOutputConnection};
use log::{info, debug};

pub struct MIDIOutput {
    midi_output: MidiOutput,
    connections: HashMap<String, MidiOutputConnection>,
    failed_ports: Vec<String>,
}

impl MIDIOutput {
    pub fn new() -> Self {
        return Self {
            midi_output: MidiOutput::new(MIDI_NAME).unwrap(),
            connections: HashMap::new(),
            failed_ports: Vec::new(),
        };
    }
}

impl EventHandler for MIDIOutput {
    fn handle_event(&mut self, _app: &App, event: &AppEvent, _event_loop: &mut EventLoop) {
        match event {
            AppEvent::MIDIIOScan => {
                let names: Vec<(usize, String)> = (0..self.midi_output.port_count()).into_iter().filter_map(|i| {
                    self.midi_output.port_name(i).map(|x| (i, x)).ok()
                }).collect();

                for (index, name) in names.iter() {
                    if !self.connections.contains_key(name) && !name.contains(MIDI_NAME) {
                        info!("New output port: {}", name);

                        let connection = MidiOutput::new(MIDI_NAME).unwrap().connect(*index, name);
                        if connection.is_ok() {
                            self.connections.insert(name.clone(), connection.unwrap());
                        } else {
                            self.failed_ports.push(name.clone());
                        }
                    }
                }

                let mut dead_ports: Vec<String> = Vec::new();

                for name in self.connections.keys() {
                    if names.iter().find(|&x| x.1 == *name).is_none() {
                        dead_ports.push(name.clone());
                        continue;
                    }
                }

                for name in dead_ports {
                    info!("Lost output port: {}", &name);
                    self.connections.remove(&name);
                }
            },
            AppEvent::MIDIOutputMessage(message) => {
                debug!("Output message: {:?}", message);
                for (_, output) in self.connections.iter_mut() {
                    let (data, len) = message.to_bytes();
                    output.send(&data[0..len]).unwrap();
                }
            },
            _ => (),
        };
    }
}
