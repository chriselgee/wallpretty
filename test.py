#!/usr/bin/env python3
# With thanks for demo code from:
# https://github.com/adafruit/Adafruit_Python_WS2801
# Simple demo of of the WS2801/SPI-like addressable RGB LED lights.
import time
import RPi.GPIO as GPIO
import argparse

# Import the WS2801 module.
import Adafruit_WS2801
import Adafruit_GPIO.SPI as SPI

# for coloring output
OV = '\x1b[0;33m' # verbose
OR = '\x1b[0;34m' # routine
OE = '\x1b[1;31m' # error
OM = '\x1b[0m'    # mischief managed

parser = argparse.ArgumentParser()
parser.add_argument("-b", "--back2front", help="whether to do the back-to-front pixel stacking (default=False)", action="store_true")
parser.add_argument("-c", "--count", type=int, default=1, help="number of cycles through the program (default=1)")
parser.add_argument("-f", "--flashes", type=int, default=0, help="number of flashes during cycles (default=0)")
parser.add_argument("-p", "--pixels", type=int, default=200, help="number of pixels in LED set (default=200)")
parser.add_argument("-v", "--verbosity", action="count", default=0, help="be more verbose")
args = parser.parse_args()

# Configure the count of pixels:
PIXEL_COUNT = args.pixels

if args.verbosity > 0:
  print("Running program for {} pixels".format(args.pixels))

# Alternatively specify a hardware SPI connection on /dev/spidev0.0:
SPI_PORT   = 0
SPI_DEVICE = 0
pixels = Adafruit_WS2801.WS2801Pixels(PIXEL_COUNT, spi=SPI.SpiDev(SPI_PORT, SPI_DEVICE), gpio=GPIO)

# Define an X,Y grid for pixels with 0,0 in the lower left
pgrid = [[]]
for i in range(int(PIXEL_COUNT / 10)):
    row = []
    for j in range(10):
        if (i % 2 == 1): # account for wire snaking back and forth
            row.insert(j,j + (i*10) + 1)
        else:
            row.insert((j),(i * 10 + 10) - j)
    pgrid.insert(i,row)

# Define the wheel function to interpolate between different hues.
def wheel(pos):
    if pos < 85:
        return Adafruit_WS2801.RGB_to_color(pos * 3, 255 - pos * 3, 0)
    elif pos < 170:
        pos -= 85
        return Adafruit_WS2801.RGB_to_color(255 - pos * 3, 0, pos * 3)
    else:
        pos -= 170
        return Adafruit_WS2801.RGB_to_color(0, pos * 3, 255 - pos * 3)

# Define rainbow cycle function to do a cycle of all hues.
def rainbow_cycle_successive(pixels, wait=0.001):
    if args.verbosity > 1: print("rainbow_cycle_successive(pixels={p},wait={w})".format(p=pixels,w=wait))
    for i in range(pixels.count()):
        # tricky math! we use each pixel as a fraction of the full 96-color wheel
        # (thats the i / strip.numPixels() part)
        # Then add in j which makes the colors go around per pixel
        # the % 96 is to make the wheel cycle around
        pixels.set_pixel(i, wheel(((i * 256 // pixels.count())) % 256) )
        pixels.show()
        if wait > 0:
            time.sleep(wait)

def rainbow_cycle(pixels, wait=0.005):
    if args.verbosity > 1: print("rainbow_cycle(pixels={p},wait={w})".format(p=pixels,w=wait))
    for j in range(256): # one cycle of all 256 colors in the wheel
        for i in range(pixels.count()):
            pixels.set_pixel(i, wheel(((i * 256 // pixels.count()) + j) % 256) )
        pixels.show()
        if wait > 0:
            time.sleep(wait)

def rainbow_colors(pixels, wait=0.05):
    if args.verbosity > 1: print("rainbow_colors(pixels={p},wait={w})".format(p=pixels,w=wait))
    for j in range(256): # one cycle of all 256 colors in the wheel
        for i in range(pixels.count()):
            pixels.set_pixel(i, wheel(((256 // pixels.count() + j)) % 256) )
        pixels.show()
        if wait > 0:
            time.sleep(wait)

def brightness_decrease(pixels, wait=0.01, step=1):
    if args.verbosity > 1: print("brightness_decrease(pixels={p},wait={w},step={s})".format(p=pixels,w=wait,s=step))
    for j in range(int(256 // step)):
        for i in range(pixels.count()):
            r, g, b = pixels.get_pixel_rgb(i)
            r = int(max(0, r - step))
            g = int(max(0, g - step))
            b = int(max(0, b - step))
            pixels.set_pixel(i, Adafruit_WS2801.RGB_to_color( r, g, b ))
        pixels.show()
        if wait > 0:
            time.sleep(wait)

def blink_color(pixels, blink_times=5, wait=0.005, color=(255,0,0)):
    if args.verbosity > 1: print("blink_color(pixels={p},blink_times={b},wait={w},color={c})".format(p=pixels,b=blink_times,w=wait,c=[color[0],color[1],color[2]]))
    for i in range(blink_times):
        # blink two times, then wait
        pixels.clear()
        for j in range(2):
            for k in range(pixels.count()):
                pixels.set_pixel(k, Adafruit_WS2801.RGB_to_color( color[0], color[1], color[2] ))
            pixels.show()
            time.sleep(0.08)
            pixels.clear()
            pixels.show()
            time.sleep(0.08)
        time.sleep(wait)

def checker_board(pixels, blink_times=5, wait=0.005, color=(255,0,0)):
    if args.verbosity > 1: print("blink_color(pixels={p},blink_times={b},wait={w},color={c})".format(p=pixels,b=blink_times,w=wait,c=[color[0],color[1],color[2]]))
    for i in range(blink_times):
        # blink two times, then wait
        pixels.clear()
        for j in range(2):
            for k in range(pixels.count()):
                if k % 2 == 1:
                    pixels.set_pixel(k, Adafruit_WS2801.RGB_to_color( color[0], color[1], color[2] ))
                else:
                    pixels.set_pixel(k, Adafruit_WS2801.RGB_to_color( 0, 0, 0 ))
            pixels.show()
            time.sleep(0.08)
            pixels.clear()
            for k in range(pixels.count()):
                if k % 2 == 0:
                    pixels.set_pixel(k, Adafruit_WS2801.RGB_to_color( color[0], color[1], color[2] ))
                else:
                    pixels.set_pixel(k, Adafruit_WS2801.RGB_to_color( 0, 0, 0 ))
            pixels.show()
            time.sleep(0.08)
            pixels.clear()
        time.sleep(wait)

def appear_from_back(pixels, color=(255, 0, 0)):
    if args.verbosity > 1: print("appear_from_back(pixels={p},color={c})".format(p=pixels,c=[color[0],color[1],color[2]]))
    pos = 0
    for i in range(pixels.count()):
        for j in reversed(range(i, pixels.count())):
            pixels.clear()
            # first set all pixels at the begin
            for k in range(i):
                pixels.set_pixel(k, Adafruit_WS2801.RGB_to_color( color[0], color[1], color[2] ))
            # set then the pixel at position j
            pixels.set_pixel(j, Adafruit_WS2801.RGB_to_color( color[0], color[1], color[2] ))
            pixels.show()
            # time.sleep(0.00002)

if __name__ == "__main__":
    # Clear all the pixels to turn them off.
    pixels.clear()
    pixels.show()  # Make sure to call show() after changing any pixels!
    for c in range(args.count):
        checker_board(pixels, blink_times = 6, color=(255,255,255))
        rainbow_cycle_successive(pixels, wait=0.01)
        rainbow_cycle(pixels, wait=0.01)
        brightness_decrease(pixels)
        if args.back2front: appear_from_back(pixels)
        for i in range(args.flashes):
            blink_color(pixels, blink_times = 1, color=(255, 0, 0))
            blink_color(pixels, blink_times = 1, color=(0, 255, 0))
            blink_color(pixels, blink_times = 1, color=(0, 0, 255))
        rainbow_colors(pixels)
        brightness_decrease(pixels)
        
