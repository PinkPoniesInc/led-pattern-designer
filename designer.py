#!/usr/bin/env python

import numpy as np
from tkinter import *

FRAME_DURATION_MS = 50

class LedImageFactory():
    def __init__(self, template_filename):
        red_led = PhotoImage(file=template_filename)

        self.height = red_led.height()
        self.width = red_led.width()

        pixels = []
        for y in range(red_led.height()):
            for x in range(red_led.width()):
                pixels.append(red_led.get(x, y))
        nppixels = np.reshape(pixels, (self.height * self.width, 3))

        self.color = nppixels[...,[0, 0, 0]] / 255
        self.highlight = (255 - nppixels[...,[2, 2, 2]]) / 255

    def create_led(self, color):
        color = color * self.color
        color = 255 - ((255 - color) * self.highlight)

        np.set_printoptions(threshold=np.nan)

        header = 'P6 %d %d 255 ' % (self.width, self.height)
        xdata = header.encode() + color.astype(np.uint8).tobytes()

        led = PhotoImage(width=self.width, height=self.height, data=xdata, format='PPM')
        return led

class LedDisplay():

    def __init__(self, root, led_image_factory, nr_of_leds):
        outerframe = Frame(root, padx = 20, pady = 20, background='black')
        outerframe.pack(fill=BOTH, expand=1)
        innerframe = Frame(outerframe, background='black')
        innerframe.pack(fill=Y, expand=1)

        self.led_image_factory = led_image_factory
        self.leds = [self.led_image_factory.create_led((0,0,0))] * nr_of_leds

        self.labels = []
        for l in self.leds:
            w = Label(innerframe, borderwidth = 0, image = l)
            w.pack(side=LEFT)
            self.labels.append(w)

        root.after(FRAME_DURATION_MS, self.updateleds)

    def updateleds(self):
        from random import random
        randomcolor = (random() * 255, random() * 255, random() * 255)
        
        self.leds = [self.led_image_factory.create_led(randomcolor)] + self.leds[:-1]

        for label, led in zip(self.labels, self.leds):
            label.configure(image = led)

        root.after(FRAME_DURATION_MS, self.updateleds)


root = Tk()

led_image_factory = LedImageFactory('images/led_light_edge.gif')
led_display = LedDisplay(root, led_image_factory, 100)

root.mainloop()

