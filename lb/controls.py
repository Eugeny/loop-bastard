from rx.subject import Subject
from RPi import GPIO
import threading
import time


class Rotary:
    def __init__(self, gpio_clk, gpio_dt):
        self.gpio_clk = gpio_clk
        self.gpio_dt = gpio_dt
        self.left = Subject()
        self.right = Subject()
        GPIO.setup(gpio_clk, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(gpio_dt, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        self.clk_last = GPIO.input(gpio_clk)
        self.pending = None

    def update(self):
        clk = GPIO.input(self.gpio_clk)
        dt = GPIO.input(self.gpio_dt)
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
        self.rotary_param = Rotary(13, 26)
        self.rotary_value = Rotary(5, 6)
        self.items = [
            self.rotary_param,
            self.rotary_value,
        ]

    def run(self):
        while True:
            time.sleep(1 / 1000)
            for i in self.items:
                i.update()
