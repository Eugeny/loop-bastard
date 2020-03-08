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
        self.clk_last = GPIO.input(clk)

    def update(self):
        clk = GPIO.input(self.gpio_clk)
        dt = GPIO.input(self.gpio_dt)
        if clk != self.clk_last:
            if dt != clk:
                self.right.on_next()
            else:
                self.left.on_next()
        self.clk_last = clk


class Controls(threading.Thread):
    def __init__(self, app):
        self.app = app
        GPIO.setmode(GPIO.BCM)
        self.rotary_value = Rotary(5, 6)
        self.items = [
            self.rotary_value
        ]

    def run(self):
        while True:
            time.sleep(1 / 100)
            for i in self.items:
                i.update()
