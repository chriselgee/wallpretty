#!/usr/bin/env python3
import argparse
import copy
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from threading import Event, Lock, Thread

from flask import Flask, render_template, request
from flask_sock import Sock

# grab PORT from environment if set
if "PORT" in os.environ:
    port = int(os.environ["PORT"])
else:
    port = 5000

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

app = Flask(__name__)
sock = Sock(app)
connected = set()
connected_lock = Lock()
pixel_lock = Lock()
HEARTBEAT_INTERVAL = 60

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
    with pixel_lock:
        return copy.deepcopy(pixelState)


def register_connection(ws):
    with connected_lock:
        connected.add(ws)


def unregister_connection(ws):
    with connected_lock:
        connected.discard(ws)


def broadcast(message):
    if args.verbosity > 0:
        print(f'{OV}broadcasting {OR}{message}{OM}')
    with connected_lock:
        targets = list(connected)
    stale = []
    for websock in targets:
        try:
            websock.send(message)
        except Exception as ex:
            stale.append(websock)
            print(f'{OE}broadcast failed: {OR}{ex}{OM}')
    if stale:
        with connected_lock:
            for dead_sock in stale:
                connected.discard(dead_sock)


def clear_board():
    """Reset both the physical pixels and cached board state."""
    updates = []
    with pixel_lock:
        pixels.clear()
        for col in range(ROW_LENGTH):
            for row in range(COL_LENGTH):
                pixelState[col][row] = [0, 0, 0]
                updates.append((col, row, 0, 0, 0))
        pixels.show()
    return updates


def process_websocket_message(raw_message):
    global pixelState
    if isinstance(raw_message, bytes):
        raw_message = raw_message.decode('utf-8', errors='ignore')
    if args.verbosity > 0:
        print(f'{OV}received data {OR}{raw_message}{OM}', end='')
    try:
        dataj = json.loads(raw_message)
    except json.JSONDecodeError as ex:
        print(f'{OE}invalid JSON payload: {OR}{ex}{OM}')
        return

    msg_type = dataj.get("Type")
    if msg_type == "Chat":
        payload = dataj.get("Data", "")
        if args.verbosity > 0:
            print(f'{OV}, broadcasting as chat {OM}')
        if isinstance(payload, str):
            lowered = payload.lower()
            if lowered == "rainbow":
                with pixel_lock:
                    rainbow_cycle(pixels)
                    brightness_decrease(pixels)
            if lowered == "clear":
                for col, row, r, g, b in clear_board():
                    broadcast(json.dumps({"Type": "Pixel", "Data": [col, row, r, g, b]}))
        broadcast(json.dumps({"Type": "Chat", "Data": payload}))
    elif msg_type == "Pixel":
        data = dataj.get("Data", [])
        if not (isinstance(data, list) and len(data) == 5):
            print(f"{OE}Pixel payload malformed: {OR}{data}{OM}")
            return
        x, y, r, g, b = data
        if not (0 <= x < ROW_LENGTH and 0 <= y < COL_LENGTH):
            print(f"{OE}Pixel coords out of bounds: {OR}{data}{OM}")
            return
        with pixel_lock:
            pixelState[x][y] = [r, g, b]
            pixels.set_pixel(pgrid[x][y], Adafruit_WS2801.RGB_to_color(r, g, b))
            pixels.show()
        if args.verbosity > 0:
            print(f'{OV}, broadcasting as pixel {OM}')
        broadcast(json.dumps({"Type": "Pixel", "Data": data}))
    elif msg_type == "Update":
        if args.verbosity > 0:
            print(f'{OV}, updating board with ROW_LENGTH {OR}{ROW_LENGTH} {OM}')
        snapshot = snapshot_pixel_state()
        for col, column in enumerate(snapshot):
            for row, pixel in enumerate(column):
                broadcast(json.dumps({
                    "Type": "Pixel",
                    "Data": [col, row, pixel[0], pixel[1], pixel[2]]
                }))
    else:
        print(f'{OE}Unknown message type: {OR}{msg_type}{OM}')


def heartbeat_sender(ws, stop_event):
    message = json.dumps({"Type": "System", "Data": "I'm watching"})
    while not stop_event.wait(HEARTBEAT_INTERVAL):
        try:
            ws.send(message)
            if args.verbosity > 0:
                print(f'{OV}sent heartbeat {OR}{message}{OM}')
        except Exception as ex:
            print(f'{OE}heartbeat failed: {OR}{ex}{OM}')
            break

@app.route('/api/saves', methods=['GET'])
def list_saved_states():
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
def save_current_board():
    payload = request.get_json(silent=True)
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
def load_saved_board(save_slug):
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


@sock.route('/ws')
def ws_handler(ws):
    if args.verbosity > 1:
        print(f'{OV}entered ws(){OM}')
    register_connection(ws)
    broadcast(json.dumps({"Type": "System", "Data": "Someone connected"}))
    stop_event = Event()
    producer_thread = Thread(target=heartbeat_sender, args=(ws, stop_event), daemon=True)
    producer_thread.start()
    try:
        while True:
            data = ws.receive()
            if data is None:
                break
            process_websocket_message(data)
    except Exception as ex:
        print(f'{OE}*** Exception in websocket handler: {OR}{ex}{OM}')
    finally:
        stop_event.set()
        producer_thread.join(timeout=1)
        unregister_connection(ws)


@app.route('/')
def index():
    if args.verbosity > 0:
        print(f'{OV}/ requested via {OR}{request.method}{OV}, args.verbosity={OR}{args.verbosity}{OM}')
    width = 10 # manually setting size of grid
    height = 20
    # build a list of x, y values for render to iterate through, e.g. 0,0 through 9,19
    xs, ys = [], []
    for i in range(width):
            xs += [i,]
    for i in range(height):
            ys += [(height - i - 1),]
    return render_template('index.html', xs=xs, ys=ys, height=height)

if __name__ == '__main__':
    pixels.clear()
    pixels.show()
    app.run(host="0.0.0.0", port=port)
