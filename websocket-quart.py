#!/usr/bin/env python3
from functools import wraps
import asyncio
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path
import copy
import re
# pip3 install quart
from quart import Quart, render_template, websocket, copy_current_websocket_context, request

# colorize output
OV = '\x1b[0;33m' # verbose
OR = '\x1b[0;34m' # routine
OE = '\x1b[1;31m' # error
OM = '\x1b[0m'    # mischief managed

# pip3 install adafruit_ws2801 RPi.GPIO
try: # because I'd still like this to run outside of a Pi
  import RPi.GPIO as GPIO
  import Adafruit_WS2801
  import Adafruit_GPIO.SPI as SPI
except Exception as ex: # mock-ups if there's no Pi
  print(f"{OE}Exception caught: {OR}{ex}{OM}")
  GPIO = None
  class Adafruit_WS2801:
    def __init__(self, pixelCount=200, spi=None, gpio=None):
      pass
    def RGB_to_color(r, g, b):
      pass
    class WS2801Pixels:
      def __init__(self, things, **kwargs):
        pass
      def clear(whatever):
        pass
      def show(whatever):
        pass
      def set_pixel(pixnum, color, whatever):
        pass
  class SPI:
    def __init__(self, **kwargs):
      pass
    def SpiDev(SPI_PORT, SPI_DEVICE):
      pass


# import specific fancy functions from ws2801_funcs.py
try: # because this won't work on dev computer
  from ws2801_funcs import *
except Exception as ex: # more mock-ups
  print(f"{OE}Exception caught: {OR}{ex}{OM}")
  def rainbow_cycle():
    pass

app = Quart(__name__)
connected = set()

parser = argparse.ArgumentParser()
parser.add_argument("-b", "--back2front", help="whether to do the back-to-front pixel stacking (default=False)", action="store_true")
parser.add_argument("-c", "--count", type=int, default=1, help="number of cycles through the program (default=1)")
parser.add_argument("-f", "--flashes", type=int, default=0, help="number of flashes during cycles (default=0)")
parser.add_argument("-p", "--pixels", type=int, default=200, help="number of pixels in LED set (default=200)")
parser.add_argument("-l", "--length", type=int, default=10, help="length of rows/number of columns (default=10)")
parser.add_argument("-v", "--verbosity", action="count", default=0, help="be more verbose")
args = parser.parse_args()

# Configure the count of pixels:
PIXEL_COUNT = args.pixels

if args.verbosity > 0:
  print(f"{OV}Running program for {OR}{args.pixels}{OV} pixels".format(args.pixels))

# Alternatively specify a hardware SPI connection on /dev/spidev0.0:
SPI_PORT   = 0
SPI_DEVICE = 0
pixels = Adafruit_WS2801.WS2801Pixels(PIXEL_COUNT, spi=SPI.SpiDev(SPI_PORT, SPI_DEVICE), gpio=GPIO)


# Define an Y,X tgrid for pixels with 0,0 in the lower left
# Assumes back and forth layout of LEDs, starting in lower-right
ROW_LENGTH = args.length
COL_LENGTH = int(PIXEL_COUNT / ROW_LENGTH)
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

# maintain pixel state for clients who join after start
pixelState = []
for column in pgrid:
    row = []
    for pixel in column:
        row.append([0,0,0])
    pixelState.append(row)

SAVE_DIR = Path(__file__).resolve().parent / "saves"
SAVE_DIR.mkdir(parents=True, exist_ok=True)
SAVE_NAME_PATTERN = re.compile(r"[^a-zA-Z0-9_-]+")


def sanitize_save_name(raw_name):
    if not isinstance(raw_name, str):
        raise ValueError("Save name must be a string.")
    trimmed = raw_name.strip()
    if not trimmed:
        raise ValueError("Save name cannot be empty.")
    sanitized = SAVE_NAME_PATTERN.sub('-', trimmed.lower()).strip('-')
    if not sanitized:
        raise ValueError("Save name must include letters, numbers, underscores, or dashes.")
    return sanitized[:64]


def snapshot_pixel_state():
    return copy.deepcopy(pixelState)

def collect_websocket(func):
    # when someone connects to /ws, add to inventory of websockets
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # if args.verbosity > 1: print(f'{OV}entered wrapper(){OM}')
        global connected
        connected.add(websocket._get_current_object())
        try:
            return await func(*args, **kwargs)
        finally:
            connected.remove(websocket._get_current_object())
    return wrapper


async def broadcast(message):
    # broadcast a message to all connected websockets
    if args.verbosity > 0: print(f'{OV}broadcasting {OR}{message}{OM}')
    for websock in connected:
        await websock.send(message)


async def consumer():
    # what to do with incoming websocket messages
    global pixelState
    global pgrid
    while True:
        data = await websocket.receive()
        if args.verbosity > 0: print(f'{OV}received data {OR}{data}{OM}', end='')
        try:
            dataj = json.loads(data)
            if dataj["Type"] == "Chat": # client is chatting
                if args.verbosity > 0: print(f'{OV}, broadcasting as chat {OM}')
                if dataj["Data"].lower() == "rainbow":
                    rainbow_cycle(pixels)
                    brightness_decrease(pixels)
                if dataj["Data"].lower() == "clear":
                    pixels.clear()
                    for column, col in zip(pixelState, range(ROW_LENGTH)):
                        for pixel, pix in zip(column, range(COL_LENGTH)):
                            pixelState[col][pix] = [0,0,0]
                            await broadcast(f'{{"Type":"Pixel","Data":[{col}, {pix}, 0, 0, 0]}}')
                    pixels.show()
                await broadcast(f'{{"Type":"Chat","Data":"{dataj["Data"]}"}}')
            if dataj["Type"] == "Pixel": # client is setting one pixel; update the board
                # incoming message looks like {"Type":"Pixel","Data":[3, 19, 255,  165,  0]}
                x = dataj['Data'][0]
                y = dataj['Data'][1]
                r = dataj['Data'][2]
                g = dataj['Data'][3]
                b = dataj['Data'][4]
                # if args.verbosity > 0: print (f'{OV}Setting pixel with dataj {OR}{dataj}{OM}')
                pixelState[x][y] = [r,g,b]
                pixels.set_pixel(pgrid[x][y],Adafruit_WS2801.RGB_to_color( r, g, b ))
                pixels.show()
                if args.verbosity > 0: print(f'{OV}, broadcasting as pixel {OM}')
                await broadcast(f'{{"Type":"Pixel","Data":{dataj["Data"]}}}')
            if dataj["Type"] == "Update": # client wants to know the whole image
                if args.verbosity > 0: print(f'{OV}, updating board with ROW_LENGTH {OR}{ROW_LENGTH} {OM}')
                for column, col in zip(pixelState, range(ROW_LENGTH)):
                    for pixel, pix in zip(column, range(COL_LENGTH)):
                        await broadcast(f'{{"Type":"Pixel","Data":[{col}, {pix}, {pixelState[col][pix][0]}, {pixelState[col][pix][1]}, {pixelState[col][pix][2]}]}}')
        except Exception as ex: # catch exceptions
            print(f'{OE}*** Exception in websocket-quart.py, consumer(): {OR}{ex}{OM}') 
            # return {"Success":False, "Error":f"{inspect.currentframe().f_code.co_name}-Exception: {ex}"}



async def producer():
    # sends sample messages out on a schedule
    while True:
        if args.verbosity > 1: print(f'{OV}entered producer(){OM}')
        message = f'{{"Type":"System","Data":"I\'m watching"}}'
        await asyncio.sleep(60)
        await websocket.send(message)
        if args.verbosity > 0: print(f'{OV}sent message {OR}{message}{OM}')

@app.route('/api/saves', methods=['GET'])
async def list_saved_states():
    saves = []
    for path in sorted(SAVE_DIR.glob('*.json')):
        try:
            with path.open('r', encoding='utf-8') as fp:
                payload = json.load(fp)
        except (OSError, json.JSONDecodeError):
            continue
        saves.append({
            "name": payload.get("name", path.stem),
            "slug": payload.get("slug", path.stem),
            "saved_at": payload.get("saved_at"),
            "width": payload.get("width", ROW_LENGTH),
            "height": payload.get("height", COL_LENGTH),
        })
    return {"saves": saves}


@app.route('/api/saves', methods=['POST'])
async def save_current_board():
    try:
        payload = await request.get_json()
    except Exception:
        payload = None
    if not payload or 'name' not in payload:
        return {"error": "A save name is required."}, 400
    display_name = payload['name'].strip()
    try:
        slug = sanitize_save_name(display_name)
    except ValueError as exc:
        return {"error": str(exc)}, 400
    record = {
        "name": display_name,
        "slug": slug,
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "width": ROW_LENGTH,
        "height": COL_LENGTH,
        "pixels": snapshot_pixel_state(),
    }
    save_path = SAVE_DIR / f"{slug}.json"
    try:
        with save_path.open('w', encoding='utf-8') as fp:
            json.dump(record, fp)
    except OSError as exc:
        return {"error": f"Unable to write save '{display_name}': {exc}"}, 500
    return {"save": {k: record[k] for k in ("name", "slug", "saved_at", "width", "height")}}


@app.route('/api/saves/<string:save_slug>', methods=['GET'])
async def load_saved_board(save_slug):
    try:
        slug = sanitize_save_name(save_slug)
    except ValueError:
        return {"error": "Save not found."}, 404
    save_path = SAVE_DIR / f"{slug}.json"
    if not save_path.exists():
        return {"error": "Save not found."}, 404
    try:
        with save_path.open('r', encoding='utf-8') as fp:
            payload = json.load(fp)
    except (OSError, json.JSONDecodeError) as exc:
        return {"error": f"Unable to read save '{slug}': {exc}"}, 500
    return payload


@app.websocket('/ws')
# defines what to do when websockets are requested from a client
@collect_websocket
async def ws():
    if args.verbosity > 1: print(f'{OV}entered ws(){OM}')
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
        if args.verbosity > 1: print(f'{OV}result is {OR}{result}{OM}')
    finally:
        consumer_task.cancel()
        producer_task.cancel()

@app.route('/')
# defines behavior for clients requesting /
async def index():
    if args.verbosity > 0: print(f'{OV}/ requested via {OR}{request.method}{OV}, args.verbosity={OR}{args.verbosity}{OM}')
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
