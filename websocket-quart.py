#!/usr/bin/env python3
from functools import wraps
from quart import Quart, render_template, websocket, copy_current_websocket_context, request
import asyncio
import json
import argparse
import time

# Import the WS2801 module and GPIO
import RPi.GPIO as GPIO
import Adafruit_WS2801
import Adafruit_GPIO.SPI as SPI

# import specific fancy functions
from ws2801_funcs import *

OV = '\x1b[0;33m' # verbose
OR = '\x1b[0;34m' # routine
OE = '\x1b[1;31m' # error
OM = '\x1b[0m'    # mischief managed

debuggin = True


app = Quart(__name__)
connected = set()


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


# Define an Y,X tgrid for pixels with 0,0 in the lower left
# Assumes back and forth layout of LEDs, starting in lower-right
ROW_LENGTH = 10
tgrid = []
for i in range(int(PIXEL_COUNT / ROW_LENGTH)):
    row = []
    for j in range(ROW_LENGTH):
        if (i % 2 == 1): # account for wire snaking back and forth
            row.insert(j,j + (i*ROW_LENGTH))
        else:
            row.insert((j),(i * ROW_LENGTH + ROW_LENGTH) - j -1)
    tgrid.insert(i,row)

# transpose to pgrid so we can use X,Y instead of Y,X to address pixels
pgrid=[]
for i in range(len(tgrid[0])):
    row=[]
    for j in range(len(tgrid)):
        row.insert(j,tgrid[j][i])
    pgrid.insert(i,row)

def collect_websocket(func):
    # when someone connects to /ws, add to inventory of websockets
    @wraps(func)
    async def wrapper(*args, **kwargs):
        if debuggin: print(f'{OV}entered wrapper(){OM}')
        global connected
        connected.add(websocket._get_current_object())
        try:
            return await func(*args, **kwargs)
        finally:
            connected.remove(websocket._get_current_object())
    return wrapper


async def broadcast(message):
    # broadcast a message to all connected websockets
    if debuggin: print(f'{OV}entered broadcast(){OM}')
    for websock in connected:
        await websock.send(message)


async def consumer():
    # what to do with incoming websocket messages
    while True:
        if debuggin: print(f'{OV}entered consumer(){OM}')
        data = await websocket.receive()
        # await broadcast(data)
        if debuggin: print(f'{OV}received data {OR}{data}{OM}', end='')
        try:
            dataj = json.loads(data)
            if dataj["Type"] == "Chat":
                if debuggin: print(f'{OV}, broadcasting as chat {OM}')
                if dataj["Data"].lower() == "rainbow":
                    rainbow_cycle(pixels)
                    brightness_decrease(pixels)
                if dataj["Data"].lower() == "clear":
                    pixels.clear()
                    pixels.show()
                await broadcast(f'{{"Type":"Chat","Data":"{dataj["Data"]}"}}')
            if dataj["Type"] == "Pixel":
                # update the board
                x = int(dataj['Data'].split('[')[1].split(',')[0])
                y = int(dataj['Data'].split('[')[1].split(',')[1])
                colorBlob = dataj['Data'].split('(')[1][:-2] # like "255, 0, 0"
                r = int(colorBlob.split(',')[0])
                g = int(colorBlob.split(',')[1])
                b = int(colorBlob.split(',')[2])
                if debuggin: print (f'{OV}Setting pixel with dataj {OR}{dataj}{OM}')
                pixels.set_pixel(pgrid[x][y],Adafruit_WS2801.RGB_to_color( r, g, b ))
                pixels.show()
                if debuggin: print(f'{OV}, broadcasting as pixel {OM}')
                await broadcast(f'{{"Type":"Pixel","Data":"{dataj["Data"]}"}}')
        except Exception as ex: # catch exceptions
            print(f'{OE}*** Exception in websocket-quart.py, consumer(): {OR}{ex}{OM}') 
            # return {"Success":False, "Error":f"{inspect.currentframe().f_code.co_name}-Exception: {ex}"}



async def producer():
    # sends sample messages out on a schedule
    while True:
        if debuggin: print(f'{OV}entered producer(){OM}')
        message = f'{{"Type":"System","Data":"I\'m watching"}}'
        await asyncio.sleep(60)
        await websocket.send(message)
        if debuggin: print(f'{OV}sent message {OR}{message}{OM}')


@app.websocket('/ws')
# defines what to do when websockets are requested from a client
@collect_websocket
async def ws():
    if debuggin: print(f'{OV}entered ws(){OM}')
    await broadcast('{"Type":"System","Data":"Someone connected"}')
    # await broadcast(b'{"Type":"System","Data":"This is a byte string yo!"}')
    consumer_task = asyncio.ensure_future( # copy websocket to consumer()
        copy_current_websocket_context(consumer)(),
    )
    producer_task = asyncio.ensure_future( # copy websocket to producer()
        copy_current_websocket_context(producer)(),
    )
    try:
        result = await asyncio.gather(consumer_task, producer_task)
        if debuggin: print(f'{OV}result is {OR}{result}{OM}')
    finally:
        consumer_task.cancel()
        producer_task.cancel()

@app.route('/')
# defines behavior for clients requesting /
async def index():
    if debuggin: print(f'{OV}/ requested via {OR}{request.method}{OM}')
    width = 10 # manually setting size of grid
    height = 20
    # build a list of x, y values for render to iterate through, e.g. 0,0 through 9,19
    xs, ys = [], []
    for i in range(width):
            xs += [i,]
    for i in range(height):
            ys += [(height - i - 1),]
    return await render_template('index.html', xs=xs, ys=ys, height=height)

if __name__ == '__main__':
    pixels.clear()
    pixels.show()
    app.run(host="0.0.0.0", port=5000)
