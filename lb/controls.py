import pygame
import threading
import time
import wiringpi
from rx.subject import Subject


class Button:
    def __init__(self, pin=None, key=None):
        self.pin = pin
        self.key = key
        self.press = Subject()
        wiringpi.pinMode(pin, 0)
        wiringpi.pullUpDnControl(pin, 2)
        self.last = 1 - wiringpi.digitalRead(self.pin)

    def update(self):
        v = 1 - wiringpi.digitalRead(self.pin)
        if v and not self.last:
            self.press.on_next(None)
        self.last = v

    def process_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == self.key:
            self.press.on_next(None)


class Rotary:
    def __init__(self, pin_dt, pin_clk, key_left=None, key_right=None):
        self.pin_clk = pin_clk
        self.pin_dt = pin_dt
        self.key_left = key_left
        self.key_right = key_right
        self.left = Subject()
        self.right = Subject()
        self.pending = None

        wiringpi.pinMode(pin_clk, 0)
        wiringpi.pullUpDnControl(pin_clk, 2)
        wiringpi.pinMode(pin_dt, 0)
        wiringpi.pullUpDnControl(pin_dt, 2)
        self.clk_last = 1 - wiringpi.digitalRead(self.pin_clk)

    def update(self):
        clk = 1 - wiringpi.digitalRead(self.pin_clk)
        dt = 1 - wiringpi.digitalRead(self.pin_dt)
        if clk and not dt:
            self.pending = 'left'
        if not clk and dt:
            self.pending = 'right'
        if clk and dt:
            if self.pending == 'left':
                self.left.on_next(None)
            if self.pending == 'right':
                self.right.on_next(None)
            self.pending = None
        self.clk_last = clk

    def process_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == self.key_left:
            self.left.on_next(None)
        if event.type == pygame.KEYDOWN and event.key == self.key_right:
            self.right.on_next(None)


class Controls(threading.Thread):
    def __init__(self, app):
        super().__init__(daemon=True)
        self.app = app

        pin_base = 100
        i2c_addr = 0x20
        wiringpi.wiringPiSetup()
        wiringpi.mcp23017Setup(pin_base, i2c_addr)

        self.play_button = Button(21, key=pygame.K_SPACE)
        self.stop_button = Button(20, key=pygame.K_s)
        self.record_button = Button(16, key=pygame.K_r)
        self.clear_button = Button(19, key=pygame.K_c)
        self.ok_button = Button(2, key=pygame.K_RETURN)
        self.s_1_button = Button(17, key=pygame.K_1)
        self.s_2_button = Button(27, key=pygame.K_2)
        self.rotary_param = Rotary(13, 26, key_left=pygame.K_DOWN, key_right=pygame.K_UP)
        self.rotary_value = Rotary(108, 109, key_left=pygame.K_LEFT, key_right=pygame.K_RIGHT)
        self.items = [
            self.play_button,
            self.stop_button,
            self.clear_button,
            self.record_button,
            self.ok_button,
            self.s_1_button,
            self.s_2_button,
            self.rotary_param,
            self.rotary_value,
        ]

    def run(self):
        while True:
            time.sleep(1 / 1000)
            for i in self.items:
                i.update()

    def process_event(self, event):
        for i in self.items:
            i.process_event(event)
