#!/usr/bin/env python
import pygame

from lb.app import App

pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=256)

App()
