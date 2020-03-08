from rx.subject import Subject
from RPi import GPIO
import threading
import time


class Button:
    def __init__(self, pin):
        self.pin = pin
        self.press = Subject()
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        self.last = GPIO.input(pin)

    def update(self):
        v = GPIO.input(self.pin)
        if v and not self.last:
            self.press.on_next(None)
        self.last = v


class Rotary:
    def __init__(self, pin_clk, pin_dt):
        self.pin_clk = pin_clk
        self.pin_dt = pin_dt
        self.left = Subject()
        self.right = Subject()
        GPIO.setup(pin_clk, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(pin_dt, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        self.clk_last = GPIO.input(pin_clk)
        self.pending = None

    def update(self):
        clk = GPIO.input(self.pin_clk)
        dt = GPIO.input(self.pin_dt)
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


class Controls(threading.Thread):
    def __init__(self, app):
        super().__init__(daemon=True)
        self.app = app
        GPIO.setmode(GPIO.BCM)
        self.play_button = Button(21)
        self.stop_button = Button(20)
        self.record_button = Button(16)
        self.rotary_param = Rotary(13, 26)
        self.rotary_value = Rotary(5, 6)
        self.items = [
            self.play_button,
            self.stop_button,
            self.record_button,
            self.rotary_param,
            self.rotary_value,
        ]

    def run(self):
        while True:
            time.sleep(1 / 1000)
            for i in self.items:
                i.update()
