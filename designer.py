#!/usr/bin/env python

import itertools
import numpy as np
from tkinter import *

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

    def __init__(self, root, led_image_factory, nr_of_leds = 100):
        self.nr_of_leds = nr_of_leds

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

    def set_leds(self, led_colors):
        self.leds = [self.led_image_factory.create_led(color) for color in led_colors]

        for label, led in zip(self.labels, self.leds):
            label.configure(image = led)
        
# The animation class is the base class for all animations. When defining a new
# animation, you can either override the pattern and position functions or you
# can override the frames function. Which one is easier depends on the kind of
# animation that you're implementing.
class Animation():
    def __init__(self):
        raise RuntimeError('No instance can be created of the abstract base class Animation')

    # This must be a generator function that returns the colors that make up the pattern for a certain frame.
    # The frame number provided is relative to the starting frame of the animation.
    def pattern(self, frame):
        raise RuntimeError('This method must be overridden in the concrete subclass')

    # This function must return the position of the pattern at the specified frame.
    # The frame number provided is relative to the starting frame of the animation.
    # Position 0 is just beyond the left of the led strip, position -1 is
    # exactly upto the right end of the led strip.
    def position(self, frame):
        raise RuntimeError('This method must be overridden in the concrete subclass')

    # This is a generator function that generates the visible part of the
    # pattern for each frame of the animation.
    # If this function is not overridden, it will fullfill its purpose using
    # the pattern and position functions.
    def frames(self, nr_of_leds):
        print('Starting animation %s' % type(self).__name__)
        frame_nr = 0
        previous_pattern = None
        while True:
            endpos = self.position(frame_nr)
            startpos = max(0, endpos - nr_of_leds)

            pattern = list(itertools.islice(self.pattern(frame_nr), startpos, endpos))
            pattern.reverse()
            pattern = (pattern + [None] * nr_of_leds)[:nr_of_leds]

            if pattern == previous_pattern:
                break

            yield pattern
            previous_pattern = pattern
            frame_nr += 1
        print('Finished animation %s' % type(self).__name__)

class BasicAnimation(Animation):
    def __init__(self, color):
        self.color = color

    def pattern(self, frame):
        period = 10
        on = 0
        while True:
            for i in range(period):
                if i <= on:
                    yield self.color
                else:
                    yield None
            on += 1

    def position(self, frame):
        return frame

class ReversedAnimation(Animation):
    def __init__(self, anim):
        self.anim = anim

    def frames(self, nr_of_leds):
        for pattern in self.anim.frames(nr_of_leds):
            yield list(reversed(pattern))

class AnimationDirector():
    def __init__(self, led_display, frame_duration = 5):
        self.frame = 0
        self.led_display = led_display
        self.led_colors = [(0,0,0)] * led_display.nr_of_leds
        self.frame_duration = frame_duration

        self.scheduled_animations = []
        self.active_animation_frames = []
        self.active_patterns = []

    def add_animation(self, start_frame, animation):
        self.scheduled_animations.append( (start_frame, animation) )

    def _blend_patterns(self, current_led_colors, active_patterns):
        blended_pattern = current_led_colors[:]

        for pattern in active_patterns:
            for i, color in enumerate(pattern):
                if color:
                    blended_pattern[i] = color

        return blended_pattern

    def _update_leds(self):
        new_active_animation_frames = [anim.frames(self.led_display.nr_of_leds) for start_frame, anim in self.scheduled_animations if start_frame == self.frame]
        self.active_animation_frames.extend(new_active_animation_frames)
        self.active_patterns.extend([None] * len(new_active_animation_frames))

        # Try to update the pattern for each active animation, or set the
        # frame_generator to None if the animation has ended
        for i, frame_generator in enumerate(self.active_animation_frames):
            if frame_generator:
                try:
                    self.active_patterns[i] = next(frame_generator)

                except StopIteration:
                    self.active_animation_frames[i] = None
        
        # Collect the finished animations up to the first one that has not
        # ended for blending into self.led_colors. Finished animations after
        # active ones must not be blended into self.led_colors, because they
        # must be applied on top of active ones.
        finished_animations = []
        for i, frame_generator in enumerate(self.active_animation_frames):
            if not frame_generator:
                finished_animations.append(i)
            else:
                break

        # Remove the active animation and pattern entry for finished animations
        # and add the final pattern to a list
        finished_patterns = []
        for i in reversed(finished_animations):
            del self.active_animation_frames[i]
            finished_patterns.insert(0, self.active_patterns[i])
            del self.active_patterns[i]

        # Blend all finished animations into self.led_colors state
        self.led_colors = self._blend_patterns(self.led_colors, finished_patterns)

        # Blend the rest of the animations and send the final colors to the leds
        final_colors = self._blend_patterns(self.led_colors, self.active_patterns)

        self.led_display.set_leds(final_colors)
        self.frame += 1
        print('frame %d' % self.frame)
        root.after(self.frame_duration, self._update_leds)

    def run_script(self):
        self.active_animations = []
        root.after(self.frame_duration, self._update_leds)


root = Tk()

led_image_factory = LedImageFactory('images/led_light_edge.gif')
led_display = LedDisplay(root, led_image_factory, nr_of_leds = 100)
director = AnimationDirector(led_display, frame_duration = 5)
director.add_animation(50, BasicAnimation((0,0,255)))
director.add_animation(100, ReversedAnimation(BasicAnimation((255,0,0))))
director.run_script()

root.mainloop()

